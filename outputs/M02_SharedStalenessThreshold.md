# M-02: Single Shared stalenessThreshold Between Data Streams and Data Feed Fallback Undermines Dual-Oracle Redundancy

## Severity

Medium

## Links to Root Cause

- [PriceManager.sol#L70-L75](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/PriceManager.sol#L70-L75) — `FeedInfo` struct with single `stalenessThreshold`
- [PriceManager.sol#L378](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/PriceManager.sol#L378) — `minTimestamp` computed from shared threshold
- [PriceManager.sol#L385](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/PriceManager.sol#L385) — Data Streams staleness check uses shared threshold
- [PriceManager.sol#L405](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/PriceManager.sol#L405) — Final validity check uses same shared threshold

## Vulnerability Details

### Finding Description and Impact

`PriceManager` implements a dual-oracle system: Data Streams as the primary source and Chainlink data feed as a fallback. However, both sources share a single `stalenessThreshold` parameter in the `FeedInfo` struct:

```solidity
struct FeedInfo {
    bytes32 dataStreamsFeedId;
    AggregatorV3Interface usdDataFeed;
    uint32 stalenessThreshold;      // ← shared between both sources
    uint8 dataStreamsFeedDecimals;
}
```

In `_getAssetPrice()`, the same `minTimestamp` is used for both sources:

```solidity
uint256 minTimestamp = block.timestamp - feedInfo.stalenessThreshold; // L378

// Data Streams check
if (updatedAt < minTimestamp && feedInfo.usdDataFeed != AggregatorV3Interface(address(0))) {
    // fallback to data feed...                                        // L385
}

// Final validity (applies to whichever source was used)
bool isStale = updatedAt < minTimestamp;                               // L405
```

This creates an irreconcilable dilemma:

| Threshold Setting | Data Streams Effect | Data Feed Fallback Effect |
|---|---|---|
| **Tight** (e.g., 5 min) | Correctly rejects stale prices | **Always stale** — Chainlink feeds have ~1h heartbeat, so the fallback is permanently considered stale and never activates |
| **Loose** (e.g., 1 hour) | Accepts prices up to 1 hour old as "fresh" — defeats real-time pricing | Works correctly with ~1h heartbeat |

### Impact

- **With a tight threshold**: The data feed fallback is effectively dead code. The dual-oracle architecture provides zero additional redundancy over a single Data Streams source. If Data Streams experiences an outage, the system has no functioning fallback.
- **With a loose threshold**: Data Streams prices up to the threshold age are accepted, which undermines the purpose of using a real-time Data Streams feed. Auction participants may bid on prices that are significantly outdated.
- **In production**: Data Streams updates every few seconds; Chainlink data feeds update on 1-hour (or longer) heartbeats. No single threshold value can optimally serve both sources.

### Attack Scenario

1. Protocol configures `stalenessThreshold = 300` (5 minutes) to ensure Data Streams prices are fresh.
2. Data Streams experiences a 10-minute outage (e.g., network issue, maintenance).
3. `_getAssetPrice()` detects Data Streams is stale (last update > 5 min ago).
4. Falls back to data feed (L385-401). Data feed's `latestRoundData()` returns a price updated 30 minutes ago.
5. `updatedAt = (now - 30 min)` < `minTimestamp = (now - 5 min)` → price is considered **stale**.
6. Even though the data feed has a perfectly valid price within its own heartbeat, it's rejected.
7. `bid()` and `performUpkeep()` revert with `StaleFeedData`. Auction system is DoS'd.
8. The fallback was supposed to provide redundancy during Data Streams outages — but it doesn't.

## Recommended Mitigation Steps

Add a separate staleness threshold for the data feed fallback:

```solidity
struct FeedInfo {
    bytes32 dataStreamsFeedId;
    AggregatorV3Interface usdDataFeed;
    uint32 stalenessThreshold;          // For Data Streams primary source
    uint32 dataFeedStalenessThreshold;  // For Chainlink data feed fallback
    uint8 dataStreamsFeedDecimals;
}
```

Then in `_getAssetPrice()`, use `dataFeedStalenessThreshold` when checking the fallback source:

```solidity
uint256 minTimestamp = block.timestamp - feedInfo.stalenessThreshold;
uint256 dataFeedMinTimestamp = block.timestamp - feedInfo.dataFeedStalenessThreshold;

// Data Streams is stale, try fallback
if (updatedAt < minTimestamp && feedInfo.usdDataFeed != AggregatorV3Interface(address(0))) {
    (, int256 answer,, uint256 dataFeedUpdatedAt,) = feedInfo.usdDataFeed.latestRoundData();
    if (dataFeedUpdatedAt >= dataFeedMinTimestamp) {
        // Use data feed price with its own staleness window
        updatedAt = dataFeedUpdatedAt;
        price = answer.toUint256();
        // ... decimal scaling ...
    }
}
```

This allows setting `stalenessThreshold = 300` (5 min for Data Streams) and `dataFeedStalenessThreshold = 7200` (2 hours for data feed) independently.

## Proof of Concept

**File**: [`test/poc/M02_SharedStalenessThreshold.t.sol`](../2026-03-chainlink/test/poc/M02_SharedStalenessThreshold.t.sol)

Extends the `C4PoC` template. Run with:

```bash
forge test --match-contract M02_SharedStalenessThreshold -vvv
```

**Test: `test_M02_sharedStalenessThresholdUnderminesFallback`**

Demonstrates the shared threshold effect:

1. Verify initial price is valid
2. Skip 59 minutes — price is still valid under 1-hour threshold
3. Skip 2 more minutes (total 61 min) — both Data Streams AND data feed become stale simultaneously
4. Update only the data feed (simulating a Chainlink heartbeat update)
5. Verify the fallback now provides a valid price — but only because the data feed was freshly updated
6. Key insight: without the fresh data feed update, both sources were stale under the shared threshold, providing zero fallback coverage

```
Ran 2 tests for test/poc/M02_SharedStalenessThreshold.t.sol:M02_SharedStalenessThreshold
[PASS] testSubmissionValidity() (gas: 166)
[PASS] test_M02_sharedStalenessThresholdUnderminesFallback() (gas: 42727)
Suite result: ok. 2 passed; 0 failed; 0 skipped
```
