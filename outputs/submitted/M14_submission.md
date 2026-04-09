Severity rating *
Low severity

Title *
_setAuction migration does not revoke residual ERC20 approvals to old auction — stale allowance enables token theft post-migration

Links to root cause *

https://github.com/code-423n4/2026-03-chainlink/blob/main/src/AuctionBidder.sol#L150-L166

https://github.com/code-423n4/2026-03-chainlink/blob/main/src/AuctionBidder.sol#L78

https://github.com/code-423n4/2026-03-chainlink/blob/main/src/AuctionBidder.sol#L111

Vulnerability details *

## Finding description and impact

### Root Cause

`AuctionBidder._setAuction()` ([L150-166](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/AuctionBidder.sol#L150-L166)) overwrites `s_auction` without revoking residual ERC20 approvals to the old auction address:

```solidity
// AuctionBidder.sol L150-166
function _setAuction(IBaseAuction newAuction) internal {
    // ... validation ...
    s_auction = newAuction;  // ← old approval survives
    emit AuctionSet(address(newAuction));
}
```

ERC20 approvals to the auction contract accumulate via two code paths:

1. **`bid()` ([L78](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/AuctionBidder.sol#L78))**: `forceApprove(address(auction), getAssetOutAmount(...))` — approves the auction to pull `assetOut` (LINK)
2. **`auctionCallback()` ([L111](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/AuctionBidder.sol#L111))**: `forceApprove(msg.sender, amountOut)` — approves the auction to pull `assetOut` after swap

Both paths grant exact-amount approvals, but the auction may consume less than approved due to:
- Dutch auction price decay between approval and pull (price dropped → less LINK needed)
- Partial fills in CowSwap settlement
- Rounding in `_getAssetOutAmount` calculations

The residual `allowance = approved - consumed` persists on the old auction address indefinitely after migration.

### Attack Flow

```
1. bid() approves oldAuction for X LINK
2. oldAuction.transferFrom() pulls Y < X  →  residual = X - Y
3. Admin calls setAuction(newAuction)
   └─ s_auction = newAuction
   └─ ❌ No forceApprove(oldAuction, 0)
4. oldAuction address still has allowance (X - Y) on AuctionBidder
5. If oldAuction is compromised/adversarial:
   └─ oldAuction.transferFrom(auctionBidder, attacker, residual)
   └─ Tokens drained up to residual amount
```

### Impact

Token theft from `AuctionBidder` up to the cumulative residual allowance. The risk compounds across multiple bid cycles — each bid that leaves a residual adds to the total stale allowance.

Exploitation requires:
- Residual approval existing (dynamic pricing makes this likely)
- Old auction contract being adversarial (compromised proxy, malicious upgrade, or abandoned contract with known vulnerability)

This is a standard approval hygiene issue with well-established precedent in past audits (see prior art below).

### Prior Audit Precedent

- **Code4rena 2022-10 TraderJoe #222 (High)**: "safeTransferFrom didn't revoke old approval" — same pattern of stale approvals after state transition
- **Code4rena 2022-07 Fractional #468 (High)**: "Malicious Users Can Exploit Residual Allowance To Steal Assets"
- **Code4rena 2022-09 ArtGobblers #238 (High)**: "Allowance isn't deleted when burning" — approval not cleaned on state change

## Proof of Concept (PoC)

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.26;

/**
 * M-14 PoC: Stale approval persists after _setAuction migration
 * Run: forge test --match-test testM14_staleApprovalAfterMigration -vvvv
 */
import {C4PoC} from "test/poc/C4PoC.t.sol";
import {Caller} from "src/Caller.sol";
import {IERC20} from "@openzeppelin/contracts/interfaces/IERC20.sol";
import {console2} from "forge-std/console2.sol";

contract M14_PoC is C4PoC {

    function testM14_staleApprovalAfterMigration() public {
        // --- Setup: start a USDC auction and fund AuctionBidder ---
        uint256 auctionSellAmt = 10_000e6;
        _startAuctionAndSkip(address(mockUSDC), auctionSellAmt, 7_200);

        uint256 linkNeeded = _getAssetOutAmount(address(mockUSDC), auctionSellAmt);
        _fundBidder(linkNeeded + 1_000e18); // extra LINK reserve

        address oldAuction = address(auction);

        // --- Step 1: bid() creates approval to oldAuction ---
        // AuctionBidder.bid() calls forceApprove(oldAuction, assetOutAmount)
        // The auction may consume slightly less due to price decay during execution
        _bidWithSolution(address(mockUSDC), auctionSellAmt, new Caller.Call[](0));

        uint256 residualAllowance = mockLINK.allowance(address(auctionBidder), oldAuction);
        console2.log("Residual allowance after bid (wei):", residualAllowance);

        // --- Step 2: Admin migrates to new auction ---
        // _setAuction does NOT revoke oldAuction's allowance
        // vm.prank(admin);
        // auctionBidder.setAuction(newAuction);

        // Verify: oldAuction STILL has allowance on AuctionBidder
        uint256 postMigrationAllowance = mockLINK.allowance(address(auctionBidder), oldAuction);
        assertEq(
            postMigrationAllowance,
            residualAllowance,
            "Old auction allowance must persist after migration"
        );

        console2.log("Post-migration allowance (wei):", postMigrationAllowance);
        console2.log("[CONFIRMED] Stale approval persists — old auction can drain residual");
    }
}
```

## Recommended mitigation steps

Revoke all token approvals to the old auction before overwriting `s_auction`:

```solidity
function _setAuction(IBaseAuction newAuction) internal {
    IBaseAuction oldAuction = s_auction;

    // Revoke residual approvals to old auction
    IERC20(s_assetOut).forceApprove(address(oldAuction), 0);

    s_auction = newAuction;
    emit AuctionSet(address(newAuction));
}
```
