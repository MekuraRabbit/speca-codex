# C4 Submission Form

## Severity rating

High

## Title

Persistent ERC20 approvals via unrestricted `_multiCall` in `auctionCallback` allow `AUCTION_BIDDER_ROLE` to bypass `DEFAULT_ADMIN_ROLE` withdrawal boundary

## Links to root cause

```
https://github.com/code-423n4/2026-03-chainlink/blob/main/src/AuctionBidder.sol#L97
https://github.com/code-423n4/2026-03-chainlink/blob/main/src/AuctionBidder.sol#L111
https://github.com/code-423n4/2026-03-chainlink/blob/main/src/Caller.sol#L58
```

## Vulnerability details

---COPY FROM HERE---

## Finding description and impact

Same underlying root cause as arbitrary call execution in `auctionCallback`, but a **distinct exploit manifestation through persistent ERC20 approvals**.

`auctionCallback()` ([L97-112](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/AuctionBidder.sol#L97)) decodes caller-supplied `Call[]` and passes them to `_multiCall()` ([Caller.sol L58-60](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/Caller.sol#L58)), which executes each call as the `AuctionBidder` contract itself — no target or selector restriction.

An attacker injects an `approve` call into the solution:

```solidity
Call({
    target: LINK_token,
    data: abi.encodeWithSignature("approve(address,uint256)", attackerEOA, type(uint256).max)
})
```

Because `_multiCall` executes in the context of `AuctionBidder`, the `approve()` is issued **from the bidder contract itself**, granting the attacker a persistent spending allowance. The post-`_multiCall` approval at [L111](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/AuctionBidder.sol#L111) only covers `assetOut → auction` for `amountOut` and does not revoke rogue allowances on other tokens.

### Trust Boundary Violation

`AUCTION_BIDDER_ROLE` is intended to participate in auctions only, while `withdraw()` is restricted to `DEFAULT_ADMIN_ROLE`. Persistent arbitrary approvals allow the bidder role to sidestep that boundary via `transferFrom` — effectively escalating `AUCTION_BIDDER_ROLE` to unrestricted fund extraction without `DEFAULT_ADMIN_ROLE`.

### Attack Scenario (two-step)

1. Attacker with `AUCTION_BIDDER_ROLE` (malicious operator or compromised bidder account) calls `bid()` with `solution` containing `approve(attacker, type(uint256).max)` for LINK
2. `BaseAuction.bid()` calls back into `auctionCallback()` → `_multiCall` executes `approve` as `AuctionBidder`
3. Attacker calls `LINK.transferFrom(auctionBidder, attacker, entireBalance)` in a **separate transaction**, at any time

### Impact

The attacker can drain any token held by `AuctionBidder` for which they grant an allowance during `_multiCall`. The approval persists indefinitely — the attacker can drain at any time after the malicious bid, making detection harder than a direct transfer.

This is distinct from the direct `transfer` variant because:
- The exploit is two-step (approve now, drain later) — harder to detect in real-time
- The approval survives across transactions and blocks
- A single malicious `bid()` can approve multiple tokens simultaneously

## Proof of Concept

```solidity
function test_approveViaMultiCall() public {
    // 1. Craft malicious approval — _multiCall executes as AuctionBidder,
    //    so approve() is issued FROM the bidder contract itself
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

    // 2. bid() → BaseAuction.bid() calls back auctionCallback()
    //    → _multiCall executes approve as AuctionBidder
    auctionBidder.bid(asset, amount, solution);

    // 3. Verify: persistent allowance now exists
    assertEq(LINK.allowance(address(auctionBidder), attacker), type(uint256).max);

    // 4. Attacker drains via transferFrom in separate tx — bypasses
    //    DEFAULT_ADMIN_ROLE withdrawal restriction entirely
    vm.prank(attacker);
    LINK.transferFrom(address(auctionBidder), attacker, LINK.balanceOf(address(auctionBidder)));
}
```

## Recommended mitigation

1. **Primary**: Allowlist trusted targets/selectors in `_multiCall` — only permit known DEX routers and swap-related selectors
2. **Secondary**: Clear all temporary approvals after callback execution completes (revoke any approvals not explicitly intended)
3. **Alternative**: Avoid arbitrary external calls from callback context entirely — use a dedicated swap executor with constrained calldata

---END COPY HERE---
