# Chainlink Payment Abstraction V2 — Security Audit Report

**Target**: [Chainlink Payment Abstraction V2 — Code4rena Audit](https://code4rena.com/audits/2026-03-chainlink-payment-abstraction-v2)
**Repository**: `code-423n4/2026-03-chainlink` @ `5317782`
**Scope**: 1,060 nSLOC — Dutch auction mechanism converting fee tokens to LINK, with CowSwap (GPv2) solver integration
**Date**: 2026-03-25

---

## Executive Summary

4 confirmed vulnerabilities identified (1 Critical, 3 Medium), plus 1 downgraded High. The most severe finding allows an AUCTION_BIDDER_ROLE holder to drain all tokens from the AuctionBidder contract via unrestricted arbitrary call execution in `auctionCallback`.

| # | Severity | ID | Title |
|---|----------|------|-------|
| 1 | Critical | PROP-01b-partial2-inv-003 | Unrestricted arbitrary call execution in `auctionCallback` drains contract funds |
| 2 | High (Downgraded) | PROP-01b-partial2-inv-004 | Unrestricted `approve()` via `_multiCall` grants attacker unlimited token allowance |
| 3 | Medium | PROP-01b-partial2-post-001 | Stale ERC20 approval to old auction persists after `_setAuction` migration |
| 4 | Medium | PROP-01b-partial-pre-002 | CowSwap settlement path bypasses `minBidUsdValue` threshold |
| 5 | Medium | PROP-01b-partial3-inv-036 | Reverting fallback oracle feed DoS-es `checkUpkeep` automation |

---

## [Critical] #1 — Unrestricted arbitrary call execution in `auctionCallback`

**File**: `src/AuctionBidder.sol::auctionCallback` (L97-112)
**Spec Reference**: SG-003

### Description

`auctionCallback` decodes the caller-supplied `Call[]` from the `data` parameter and passes it verbatim to `_multiCall` (Caller.sol L58-60), which executes each `Call` via raw low-level `.call(data)` with **no restriction on target address or calldata**.

Any `AUCTION_BIDDER_ROLE` holder can construct a `solution` containing `Call({target: tokenAddress, data: transfer(attacker, balance)})`. The `withdraw()` function requiring `DEFAULT_ADMIN_ROLE` confirms this privilege was never intended for `AUCTION_BIDDER_ROLE`.

### Attack Scenario

1. Attacker with `AUCTION_BIDDER_ROLE` calls `bid()` with:
   ```
   solution = [Call({
     target: heldToken,
     data: abi.encodeWithSignature("transfer(address,uint256)", attacker, balance)
   })]
   ```
2. The auction transfers `assetIn` to `AuctionBidder`, then invokes `auctionCallback`
3. `_multiCall` executes the attacker's `transfer` call, draining `heldToken` to the attacker **before** the auction can pull `assetOut`

### Impact

Direct theft of all tokens held by the `AuctionBidder` contract. Meets Critical threshold per scope: "Direct theft or permanent freezing of funds."

### Recommendation

Restrict `_multiCall` targets and selectors in `auctionCallback`. Either:
- Whitelist allowed call targets (e.g., only the auction contract and known DEX routers)
- Validate that `Call.target` is not a token held by the contract
- Use a dedicated swap executor with constrained calldata instead of arbitrary `_multiCall`

---

## [High → Downgraded] #2 — Unrestricted `approve()` via `_multiCall`

**File**: `src/AuctionBidder.sol::auctionCallback` (L97-112)
**Spec Reference**: SG-003

### Description

Same root cause as #1. Instead of a direct `transfer`, an attacker can inject `Call{target: LINK_token, data: approve(attackerEOA, type(uint256).max)}` into the solution. `_multiCall` executes it unconditionally, granting the attacker an unlimited spending allowance. The post-`_multiCall` approval at L111 only covers `assetOut` → auction for `amountOut` and does not revoke rogue allowances on other tokens.

### Attack Scenario

1. Attacker calls `bid()` with `solution` containing `approve(attacker, type(uint256).max)` for LINK
2. `auctionCallback._multiCall` executes the approval
3. Attacker calls `LINK.transferFrom(auctionBidder, attacker, entireBalance)` in a separate transaction

### Impact

Full drain of the AuctionBidder's LINK balance (and any other token). Downgraded from Critical to High because exploitation requires `AUCTION_BIDDER_ROLE` (admin-granted, not permissionless).

### Recommendation

Same as #1.

---

## [Medium] #3 — Stale ERC20 approval persists after auction migration

**File**: `src/AuctionBidder.sol::_setAuction` (L150-166)
**Spec Reference**: SG-005

### Description

`_setAuction` overwrites `s_auction` (L163) without calling `forceApprove(oldAuction, 0)` to clear residual ERC20 approvals. Approvals to the old auction accumulate via:
- `bid()` (L78): `forceApprove(address(auction), getAssetOutAmount(...))`
- `auctionCallback()` (L111): `forceApprove(msg.sender, amountOut)`

If either call leaves a residual (e.g., dynamic pricing causes under-consumption), that allowance persists on the old auction address.

### Attack Scenario

1. `bid()` approves `oldAuction` for amount X, but auction only consumes Y < X
2. Admin calls `setAuction(newAuction)` — residual approval (X-Y) to `oldAuction` remains
3. Old auction contract (compromised or adversarial post-migration) calls `ERC20.transferFrom(auctionBidder, attacker, residual)` to drain tokens

### Impact

Token theft from AuctionBidder up to the residual allowance amount. Conditional on residual approval existing and old auction being adversarial.

### Recommendation

Add `forceApprove(address(oldAuction), 0)` for all relevant tokens before overwriting `s_auction` in `_setAuction`.

---

## [Medium] #4 — CowSwap settlement bypasses `minBidUsdValue`

**File**: `src/GPV2CompatibleAuction.sol::isValidSignature` (L119-176)
**Spec Reference**: SG-003

### Description

`BaseAuction.bid()` enforces `minBidUsdValue` at L431-435. However, the alternative CowSwap settlement path via `GPV2CompatibleAuction.isValidSignature` only checks:
- `order.sellAmount > 0`
- `buyAmount >= minBuyAmount(sellAmount)`

It **never** compares the sell amount's USD value against `s_minBidUsdValue`. CowSwap settlement calls `isValidSignature` then directly transfers tokens via the vault relayer without invoking `bid()`.

### Attack Scenario

1. CowSwap solver constructs a partial order with `order.sellAmount = 1 wei`
2. Sets `buyAmount` to the proportional `_getAssetOutAmount` result
3. Submits to CowSwap settlement — `isValidSignature` validates
4. Settlement executes, taking 1 wei of the auctioned asset while bypassing `s_minBidUsdValue`

### Impact

Minimum bid threshold bypass on CowSwap path. Enables dust bids that the system was designed to reject, potentially griefing auction economics.

### Recommendation

Add `minBidUsdValue` check in `isValidSignature`:
```solidity
uint256 bidUsdValue = _getBidUsdValue(order.sellAmount, ...);
require(bidUsdValue >= s_minBidUsdValue, "Bid below minimum");
```

---

## [Medium] #5 — Reverting fallback oracle DoS-es `checkUpkeep`

**File**: `src/PriceManager.sol::_getAssetPrice` (L385-386)
**Spec Reference**: SG-004

### Description

When an asset's data stream price becomes stale and a fallback `AggregatorV3` feed is configured, `_getAssetPrice` calls `feedInfo.usdDataFeed.latestRoundData()` at L385-386 **without try/catch**. If the fallback feed reverts (deprecated aggregator, access-controlled feed, circuit breaker), the revert propagates through the entire `checkUpkeep` call.

`checkUpkeep` is designed with a no-revert soft-skip invariant: ineligible assets should be skipped via `continue`, not cause a revert. This violation blocks Chainlink Automation from processing any auctions.

### Attack Scenario

1. Asset A's data stream price becomes stale
2. The configured fallback `AggregatorV3` feed is deprecated/paused and reverts on `latestRoundData()`
3. Revert bubbles through `_getAssetPrice` → `checkUpkeep`
4. Chainlink Automation receives a revert on every `checkUpkeep` call
5. **All auction starts and auction-end processing are blocked** until the feed is fixed

### Impact

DoS of core `checkUpkeep` functionality. Matches scope's Medium threshold: "Auction participation blocking (DoS)."

### Recommendation

Wrap fallback `latestRoundData()` in try/catch:
```solidity
try feedInfo.usdDataFeed.latestRoundData() returns (
    uint80, int256 answer, uint256, uint256 updatedAt, uint80
) {
    // use answer and updatedAt
} catch {
    continue; // soft-skip this asset
}
```

---

## Appendix: Methodology

- **Pipeline**: SPECA (Specification-to-Property Agentic Auditing) 6-phase pipeline
  - Phase 01a: Spec Discovery
  - Phase 01b: Subgraph Extraction
  - Phase 01e: Property Generation (STRIDE + CWE Top 25)
  - Phase 02c: Code Location Pre-resolution (Tree-sitter)
  - Phase 03: Proof-based Formal Audit (Map → Prove → Stress-Test)
  - Phase 04: 3-Gate FP Filter (Dead Code → Trust Boundary → Scope Check)
- **Pattern Database**: 131 historical DeFi vulnerability patterns from Code4rena, Sherlock, CodeHawks
- **Review**: Phase 04 applied 3-gate filtering; 2/7 findings disputed as FP (admin-path only), 4 confirmed, 1 downgraded
