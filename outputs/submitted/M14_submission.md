# C4 Submission Form

## Severity rating

Medium

## Title

Stale ERC20 approval to old auction persists after `_setAuction` migration, enabling token theft if old auction is compromised

## Links to root cause

```
https://github.com/code-423n4/2026-03-chainlink/blob/main/src/AuctionBidder.sol#L150
https://github.com/code-423n4/2026-03-chainlink/blob/main/src/AuctionBidder.sol#L163
https://github.com/code-423n4/2026-03-chainlink/blob/main/src/AuctionBidder.sol#L78
https://github.com/code-423n4/2026-03-chainlink/blob/main/src/AuctionBidder.sol#L111
```

## Vulnerability details

---COPY FROM HERE---

## Finding description and impact

`AuctionBidder._setAuction()` ([L150-166](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/AuctionBidder.sol#L150)) overwrites `s_auction` at L163 **without** revoking residual ERC20 approvals to the old auction address.

ERC20 approvals to the auction accumulate via two paths:

1. **`bid()`** ([L78](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/AuctionBidder.sol#L78)): `forceApprove(address(auction), getAssetOutAmount(...))`
2. **`auctionCallback()`** ([L111](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/AuctionBidder.sol#L111)): `forceApprove(msg.sender, amountOut)`

If either call leaves a residual (e.g., dynamic pricing causes under-consumption of the approved amount), that allowance persists after migration.

```solidity
// _setAuction (L150-166)
function _setAuction(IBaseAuction newAuction) internal {
    // ❌ Missing: forceApprove(address(oldAuction), 0) for all tokens
    s_auction = newAuction;  // L163 — old approval survives
    emit AuctionSet(address(newAuction));
}
```

### Attack Scenario

1. `bid()` approves `oldAuction` for amount X, but auction only consumes Y < X
2. Admin calls `setAuction(newAuction)` — residual approval (X-Y) to `oldAuction` remains
3. Old auction contract (compromised or adversarial post-migration) calls `ERC20.transferFrom(auctionBidder, attacker, residual)` to drain tokens up to residual amount

### Impact

Token theft from AuctionBidder up to the residual allowance amount. Conditional on:
- A residual approval existing (dynamic pricing under-consumption)
- Old auction being adversarial (compromise, malicious upgrade, or abandoned contract with known vulnerability)

## Proof of Concept

```solidity
function test_staleApprovalAfterMigration() public {
    // 1. bid() approves oldAuction for 1000 LINK
    auctionBidder.bid(asset, 1000e18, solution);

    // 2. Auction only consumes 800 LINK — residual 200 LINK approval remains
    assertGt(LINK.allowance(address(auctionBidder), address(oldAuction)), 0);

    // 3. Admin migrates to new auction
    auctionBidder.setAuction(newAuction);

    // 4. Old auction still has approval — can drain residual
    assertGt(LINK.allowance(address(auctionBidder), address(oldAuction)), 0);
    // oldAuction.transferFrom(auctionBidder, attacker, residual) succeeds
}
```

## Recommended mitigation

Revoke all token approvals to the old auction before overwriting `s_auction`:

```solidity
function _setAuction(IBaseAuction newAuction) internal {
    IBaseAuction oldAuction = s_auction;

    // Revoke approvals to old auction for all managed tokens
    address[] memory tokens = getAssetList();
    for (uint256 i; i < tokens.length; ++i) {
        IERC20(tokens[i]).forceApprove(address(oldAuction), 0);
    }

    s_auction = newAuction;
    emit AuctionSet(address(newAuction));
}
```

---END COPY HERE---
