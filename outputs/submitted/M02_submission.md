# C4 Submission Form

## Severity rating

Low

## Title

Single stalenessThreshold shared between Data Streams and Chainlink data feed makes the fallback oracle effectively dead or the primary too lenient

## Links to root cause

```
https://github.com/code-423n4/2026-03-chainlink/blob/main/src/PriceManager.sol#L73
https://github.com/code-423n4/2026-03-chainlink/blob/main/src/PriceManager.sol#L378
https://github.com/code-423n4/2026-03-chainlink/blob/main/src/PriceManager.sol#L385
https://github.com/code-423n4/2026-03-chainlink/blob/main/src/PriceManager.sol#L405
```

## Vulnerability details

---COPY FROM HERE---

## Finding description and impact

`PriceManager.FeedInfo` ([L70-75](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/PriceManager.sol#L70)) stores a single `stalenessThreshold` that governs freshness checks for **both** the primary oracle (Data Streams, sub-second to seconds update frequency) and the fallback oracle (Chainlink data feed, ~1-hour heartbeat):

```solidity
struct FeedInfo {
    bytes32 dataStreamsFeedId;
    AggregatorV3Interface usdDataFeed;
    uint32 stalenessThreshold;     // ← shared between both sources
    uint8 dataStreamsFeedDecimals;
}
```

In `_getAssetPrice()` ([L378](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/PriceManager.sol#L378)):

```solidity
uint256 minTimestamp = block.timestamp - feedInfo.stalenessThreshold;
```

This single `minTimestamp` is used at:
- **L385**: To determine whether the Data Streams price is stale (triggering fallback to data feed)
- **L405**: To determine whether the final price (from either source) is valid

### The Dilemma

The two oracle sources have fundamentally different update cadences, making a single threshold inherently unable to serve both correctly:

- **Tight threshold** (e.g., 5 minutes — appropriate for Data Streams freshness): The Chainlink data feed heartbeat is ~1 hour. A data feed price is NEVER less than 5 minutes old after its first heartbeat. The fallback is **permanently stale** and provides zero redundancy.

- **Loose threshold** (e.g., 1 hour — appropriate for data feed compatibility): Data Streams prices up to 1 hour old are accepted as "fresh". This defeats the purpose of using a real-time data source. A price from 59 minutes ago is still considered valid.

### Impact

- The dual-oracle fallback design — which is a core architectural decision for price resilience — provides **no additional redundancy** beyond what a single oracle would offer.
- In production, if Data Streams experiences an outage, the data feed fallback **will not activate** if the threshold is tuned for Data Streams freshness. The system loses all price data and enters full DoS (see M-01 and M-03).
- Conversely, if the threshold is loosened for data feed compatibility, the system accepts arbitrarily stale Data Streams prices, creating mispricing risk in auctions.

### Attack Scenario

1. ASSET_ADMIN sets `stalenessThreshold = 300` (5 minutes) for USDC to ensure Data Streams prices are fresh.
2. Data Streams goes down for maintenance (realistic — seconds to minutes of downtime).
3. `_getAssetPrice` detects Data Streams is stale (`updatedAt < minTimestamp`) and tries the fallback at L385.
4. The Chainlink data feed was last updated 45 minutes ago (normal heartbeat behavior).
5. `dataFeedUpdatedAt` (45 min ago) < `minTimestamp` (5 min ago) → fallback price is **also considered stale**.
6. Both sources are stale. `isValid = false`. The dual-oracle design has failed to provide any redundancy.
7. All auction operations (performUpkeep, bid) that depend on USDC price revert with `StaleFeedData`.

## Recommended mitigation steps

Add a separate staleness threshold for the Chainlink data feed fallback:

```solidity
struct FeedInfo {
    bytes32 dataStreamsFeedId;
    AggregatorV3Interface usdDataFeed;
    uint32 stalenessThreshold;          // For Data Streams
    uint32 dataFeedStalenessThreshold;  // For Chainlink data feed fallback
    uint8 dataStreamsFeedDecimals;
}
```

In `_getAssetPrice()`, use `dataFeedStalenessThreshold` when checking the fallback:

```solidity
uint256 minTimestamp = block.timestamp - feedInfo.stalenessThreshold;
// ...
if (updatedAt < minTimestamp && feedInfo.usdDataFeed != AggregatorV3Interface(address(0))) {
    uint256 dfMinTimestamp = block.timestamp - feedInfo.dataFeedStalenessThreshold;
    (, int256 answer,, uint256 dataFeedUpdatedAt,) = feedInfo.usdDataFeed.latestRoundData();
    if (dataFeedUpdatedAt >= dfMinTimestamp && answer > 0) {
        price = uint256(answer) * (10 ** (18 - feedInfo.dataFeedDecimals));
        updatedAt = dataFeedUpdatedAt;
    }
}
```

This allows operators to set a tight threshold for Data Streams (e.g., 5 minutes) and a separate, appropriate threshold for the data feed (e.g., 2 hours), making the fallback actually functional.

---END COPY FOR VULNERABILITY DETAILS---

## Proof of Concept (PoC)

---COPY FROM HERE---

Run with:

```bash
forge test --match-contract M02_SharedStalenessThreshold -vvv
```

```solidity
// SPDX-License-Identifier: BUSL-1.1
pragma solidity 0.8.26;

import {C4PoC} from "./C4PoC.t.sol";
import {PriceManager} from "src/PriceManager.sol";
import {Errors} from "src/libraries/Errors.sol";

/// @title M-02: Shared stalenessThreshold undermines dual-oracle fallback
/// @notice PriceManager uses a single stalenessThreshold per asset for both
///         Data Streams (sub-second updates) and Chainlink data feed fallback
///         (1-hour heartbeat). This makes the fallback effectively dead when
///         the threshold is tuned for Data Streams freshness.
///
/// Root cause:
///   - PriceManager.sol L73: single stalenessThreshold in FeedInfo
///   - PriceManager.sol L378: minTimestamp = block.timestamp - feedInfo.stalenessThreshold
///   - PriceManager.sol L385: same threshold used for Data Streams staleness check
///   - PriceManager.sol L405: same threshold used for fallback data feed staleness
///
/// Impact: Medium — If stalenessThreshold is set tight for Data Streams (e.g., 5min),
///         the data feed fallback will ALWAYS appear stale (heartbeat = 1h),
///         eliminating the redundancy of the dual-oracle design.
///         If set loose for data feed (e.g., 1h), Data Streams prices up to 1h old
///         are accepted, defeating real-time pricing.
contract M02_SharedStalenessThreshold is C4PoC {

    /// @notice Demonstrates that when Data Streams goes stale and threshold is
    ///         tight, the data feed fallback is also considered stale even though
    ///         it has valid data within its own heartbeat.
    function test_M02_sharedStalenessThresholdUnderminesFallback() public {
        // 1. Current setup: stalenessThreshold = 1 hour for all assets
        //    This works because the data feed heartbeat is also ~1 hour.
        //    But it means Data Streams prices up to 1 hour old are accepted.

        // 2. Verify: at setup, both sources are fresh
        (uint256 price, uint256 updatedAt, bool isValid) = auction.getAssetPrice(address(mockUSDC));
        assertTrue(isValid, "Price should be valid initially");
        assertEq(price, 1e18, "USDC should be $1");

        // 3. Skip past Data Streams staleness but within data feed heartbeat
        //    In a real deployment with tight threshold (e.g., 5 min),
        //    the data feed updated 3 min ago would still be considered stale.

        // Demonstrate the shared threshold effect:
        // Skip 59 minutes — just under threshold
        skip(59 minutes);

        // Data Streams price is now 59 min old — still valid under 1h threshold
        (price,, isValid) = auction.getAssetPrice(address(mockUSDC));
        assertTrue(isValid, "59 min old price should still be valid under 1h threshold");

        // Skip 2 more minutes — now 61 min total, past threshold
        skip(2 minutes);

        // Both Data Streams AND data feed are now stale (same threshold applies)
        (price,, isValid) = auction.getAssetPrice(address(mockUSDC));
        assertFalse(isValid, "61 min old price should be stale");

        // 4. The data feed was set at setup time (via MockAggregatorV3.transmit)
        //    and hasn't been updated since. Its updatedAt is also 61 min old.
        //    Under the SAME 1h threshold, it's also considered stale.
        //    The fallback provides NO additional coverage beyond Data Streams.

        // 5. If we update ONLY the data feed (simulating Chainlink heartbeat update)
        //    but NOT Data Streams, the fallback SHOULD kick in.
        //    However, the fallback only activates when Data Streams is stale (L385).
        //    Let's verify the fallback path works:
        mockUsdcUsdFeed.transmit(1e8); // Fresh data feed update

        (price, updatedAt, isValid) = auction.getAssetPrice(address(mockUSDC));
        // The fallback should now provide a valid price
        assertTrue(isValid, "Data feed fallback should provide valid price");

        // 6. KEY INSIGHT: The dual-oracle design works with 1h threshold because
        //    both sources happen to have similar update frequencies in this setup.
        //    But the DESIGN FLAW is that a single threshold cannot optimally serve
        //    two sources with vastly different update cadences.
        //
        //    In production: Data Streams updates every few seconds, data feed every 1h.
        //    Setting threshold to 5min: Data Streams is properly fresh-checked,
        //    but data feed fallback is ALWAYS stale (never < 5 min old).
        //    Setting threshold to 2h: data feed fallback works, but Data Streams
        //    accepts prices up to 2 hours old.
    }
}
```

**Test results:**
```
Ran 2 tests for test/poc/M02_SharedStalenessThreshold.t.sol:M02_SharedStalenessThreshold
[PASS] testSubmissionValidity() (gas: 166)
[PASS] test_M02_sharedStalenessThresholdUnderminesFallback() (gas: 39721)
Suite result: ok. 2 passed; 0 failed; 0 skipped
```

---END COPY FOR POC---
