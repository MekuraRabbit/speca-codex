# C4 Submission Form

## Severity rating

Medium

## Title

Unrestricted `approve()` via `_multiCall` in `auctionCallback` grants attacker unlimited token allowance — same root cause as arbitrary call execution

## Links to root cause

```
https://github.com/code-423n4/2026-03-chainlink/blob/main/src/AuctionBidder.sol#L97
https://github.com/code-423n4/2026-03-chainlink/blob/main/src/AuctionBidder.sol#L111
https://github.com/code-423n4/2026-03-chainlink/blob/main/src/Caller.sol#L58
```

## Vulnerability details

---COPY FROM HERE---

## Finding description and impact

This is the `approve()` variant of the unrestricted `_multiCall` vulnerability in `auctionCallback`. Same root cause as the direct `transfer` drain — `_multiCall` ([Caller.sol L58-60](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/Caller.sol#L58)) executes arbitrary calls without target/selector validation.

Instead of a direct `transfer`, an attacker injects:

```solidity
Call({
    target: LINK_token,
    data: abi.encodeWithSignature("approve(address,uint256)", attackerEOA, type(uint256).max)
})
```

The post-`_multiCall` approval at [L111](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/AuctionBidder.sol#L111) only covers `assetOut → auction` for `amountOut` and does **not** revoke rogue allowances on other tokens.

### Attack Scenario

1. `AUCTION_BIDDER_ROLE` holder calls `bid()` with `solution` containing `approve(attacker, type(uint256).max)` for LINK
2. `auctionCallback._multiCall` executes the approval
3. Attacker calls `LINK.transferFrom(auctionBidder, attacker, entireBalance)` in a separate transaction

### Impact

Full drain of the AuctionBidder's LINK balance (and any other token). This is a two-step variant — the approval persists indefinitely, so the attacker can drain at any time after the malicious bid.

Downgraded from High because:
- Requires `AUCTION_BIDDER_ROLE` (admin-granted, not permissionless)
- Same root cause as the direct transfer variant — fixing one fixes both

## Proof of Concept

```solidity
function test_approveViaMultiCall() public {
    // 1. Craft malicious approval
    ICaller.Call[] memory maliciousCalls = new ICaller.Call[](1);
    maliciousCalls[0] = ICaller.Call({
        target: address(LINK),
        data: abi.encodeWithSignature(
            "approve(address,uint256)",
            attacker,
            type(uint256).max
        )
    });

    bytes memory solution = abi.encode(maliciousCalls);

    // 2. bid() triggers auctionCallback → _multiCall executes approve
    // auctionBidder.bid(asset, amount, solution);

    // 3. Attacker drains via transferFrom in separate tx
    // LINK.transferFrom(auctionBidder, attacker, LINK.balanceOf(auctionBidder));
}
```

## Recommended mitigation

Same fix as the direct transfer variant: restrict `_multiCall` targets and selectors in `auctionCallback`.

---END COPY HERE---
