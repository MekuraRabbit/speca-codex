# C4 Submission Form

## Severity rating

Low

## Title

PriceManager fallback path does not validate Chainlink aggregator min/max circuit breaker bounds, enabling mispriced auctions during extreme market events

## Links to root cause

```
https://github.com/code-423n4/2026-03-chainlink/blob/main/src/PriceManager.sol#L386
https://github.com/code-423n4/2026-03-chainlink/blob/main/src/PriceManager.sol#L392
```

## Vulnerability details

---COPY FROM HERE---

## Finding description and impact

### Root Cause

`PriceManager._getAssetPrice()` ([L386-392](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/PriceManager.sol#L386)) fetches the fallback Chainlink data feed price via `latestRoundData()` but does not validate whether the returned `answer` has hit the aggregator's built-in `minAnswer`/`maxAnswer` circuit breaker bounds:

```solidity
// PriceManager.sol L385-402
if (updatedAt < minTimestamp && feedInfo.usdDataFeed != AggregatorV3Interface(address(0))) {
    (, int256 answer,, uint256 dataFeedUpdatedAt,) = feedInfo.usdDataFeed.latestRoundData();

    if (updatedAt < dataFeedUpdatedAt) {
        updatedAt = dataFeedUpdatedAt;
        price = answer.toUint256();  // ← No min/max bound check

        // ... decimal scaling ...
    }
}
```

Chainlink aggregators have hardcoded `minAnswer` and `maxAnswer` values. When the actual market price moves beyond these bounds, the aggregator returns the boundary value instead of the real price. The code performs staleness and zero checks ([L404-416](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/PriceManager.sol#L404)) but **does not detect circuit-breaker-clamped prices**.

### Impact

When the fallback data feed is active (Data Streams is stale) and the real market price exceeds circuit breaker bounds:

**Scenario: LINK price crashes below minAnswer**

The `assetOutAmount` calculation in `_getAssetOutAmount()` ([L802](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/BaseAuction.sol#L802)) uses `assetOutUsdPrice` as denominator:

```solidity
return auctionUsdValue.mulDivUp(10 ** s_assetParams[s_assetOut].decimals, assetOutUsdPrice);
```

If the real LINK price drops below the aggregator's `minAnswer`, the feed returns `minAnswer` instead of the real price. Since `assetOutUsdPrice` (LINK) is inflated relative to reality, `assetOutAmount` is lower than it should be — the bidder pays fewer LINK tokens than the auctioned assets are worth at market price. The degree of loss depends on how far the real price has diverged from `minAnswer`.

### Conditions

1. **Data Streams must be stale** — fallback path activates only when primary oracle is unavailable
2. **Market price must exceed circuit breaker bounds** — requires extreme market event (crash/spike)
3. **bid() is permissionless** — any address with LINK can call `BaseAuction.bid()` (no role required)

Both conditions must coincide, making exploitation opportunistic rather than on-demand.

### Additional issue: negative price

The same code path also lacks a `answer > 0` check. If `latestRoundData()` returns a negative `int256`, `answer.toUint256()` via SafeCast will revert, causing a DoS on `bid()` and `performUpkeep()` for all assets using that feed as fallback. This is a defense-in-depth gap — Chainlink price feeds for standard assets (USDC, WETH, LINK) should not return negative values, but the [Chainlink documentation recommends](https://docs.chain.link/data-feeds#check-the-timestamp-of-the-latest-answer) validating `answer > 0`.

### Prior Audit Precedent

This exact pattern has been consistently rated **Medium** across multiple Code4rena contests:

- **Loopfi (2024-07) #522 (Medium)**: "ChainlinkOracle will use incorrect price when price hits minAnswer/maxAnswer"
- **Noya (2024-04) #1130 (Medium)**: "Chainlink oracle will return the wrong price if the aggregator hits minAnswer/maxAnswer"
- **Size (2024-06) #3 (Medium)**: "PriceFeed doesn't check min/max price boundaries"
- **Ondo (2023-01) #185 (Medium)**: "Chainlink's multisigs can immediately block access to price feeds"

**Note on trust model alignment**: These precedents and our finding share the same trust model — permissionless users interact with auction/lending functions that consume potentially clamped oracle prices. The attack surface (external oracle returning misleading-but-valid data) is identical.

### Severity Rationale

Rated **Low** (not Medium) because:
1. Requires two simultaneous external conditions (Data Streams outage + extreme market event)
2. The primary oracle (Data Streams) does not have this issue — only the fallback path
3. This is Chainlink's own protocol — they have operational awareness of their aggregator configurations
4. Recovery is possible by updating Data Streams prices via `transmit()`

## Recommended mitigation steps

Add circuit breaker validation in the fallback path:

```solidity
if (updatedAt < minTimestamp && feedInfo.usdDataFeed != AggregatorV3Interface(address(0))) {
    (, int256 answer,, uint256 dataFeedUpdatedAt,) = feedInfo.usdDataFeed.latestRoundData();

    // NEW: Reject negative prices
    if (answer <= 0) {
        revert Errors.ZeroFeedData();
    }

    if (updatedAt < dataFeedUpdatedAt) {
        updatedAt = dataFeedUpdatedAt;
        price = uint256(answer);

        // ... existing decimal scaling ...
    }
}
```

For full circuit breaker protection, compare against the aggregator's min/max bounds:

```solidity
IAccessControlledOffchainAggregator aggregator = IAccessControlledOffchainAggregator(
    feedInfo.usdDataFeed.aggregator()
);
int192 minAnswer = aggregator.minAnswer();
int192 maxAnswer = aggregator.maxAnswer();
if (answer <= minAnswer || answer >= maxAnswer) {
    revert Errors.CircuitBreakerTriggered();
}
```

---END COPY FOR VULNERABILITY DETAILS---

## Proof of Concept (PoC)

---COPY FROM HERE---

The vulnerability is in the code path itself — no runtime PoC is needed to demonstrate the missing validation. The following walkthrough traces the exact execution path:

### Code Walkthrough

1. **Data Streams becomes stale** — `updatedAt < minTimestamp` at [L385](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/PriceManager.sol#L385)

2. **Fallback activates** — `latestRoundData()` is called on the Chainlink data feed at [L386](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/PriceManager.sol#L386):
```solidity
(, int256 answer,, uint256 dataFeedUpdatedAt,) = feedInfo.usdDataFeed.latestRoundData();
```

3. **No bounds check** — `answer` is assigned directly to `price` at [L392](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/PriceManager.sol#L392):
```solidity
price = answer.toUint256();
```
There is no comparison against `aggregator.minAnswer()` or `aggregator.maxAnswer()`. If the aggregator has clamped the answer to a boundary value, this code cannot detect it.

4. **Staleness/zero checks pass** — [L404-416](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/PriceManager.sol#L404) only check `updatedAt >= minTimestamp` and `price == 0`. A clamped-but-fresh price passes both checks.

5. **Mispriced auction** — `_getAssetOutAmount()` at [L802](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/BaseAuction.sol#L802) uses the clamped price as denominator:
```solidity
return auctionUsdValue.mulDivUp(10 ** s_assetParams[s_assetOut].decimals, assetOutUsdPrice);
```
An inflated `assetOutUsdPrice` produces a lower `assetOutAmount` — the bidder pays fewer LINK tokens than the auctioned assets are worth at market price.

### Key observation

The existing code validates staleness and zero but has **no path** to detect circuit-breaker-clamped values. This is visible by inspection of [L385-416](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/PriceManager.sol#L385) — the word "min" or "max" does not appear in the fallback validation logic.

---END COPY FOR POC---
