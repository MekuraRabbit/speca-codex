# C4 Submission Form

## Severity rating

Medium

## Title

Asymmetric price validation between checkUpkeep and performUpkeep/bid causes complete auction DoS during transient oracle staleness

## Links to root cause

```
https://github.com/code-423n4/2026-03-chainlink/blob/main/src/BaseAuction.sol#L238
https://github.com/code-423n4/2026-03-chainlink/blob/main/src/BaseAuction.sol#L315
https://github.com/code-423n4/2026-03-chainlink/blob/main/src/BaseAuction.sol#L342
https://github.com/code-423n4/2026-03-chainlink/blob/main/src/BaseAuction.sol#L429
```

## Vulnerability details

---COPY FROM HERE---

## Finding description and impact

The auction lifecycle has an asymmetric price validation design between the off-chain eligibility check (`checkUpkeep`) and the on-chain execution (`performUpkeep` / `bid`):

1. **`checkUpkeep()` ([L238](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/BaseAuction.sol#L238))** fetches prices with `withValidation = false`. This means it returns stale or zero prices without reverting, using them to determine which assets are eligible for auction and which auctions have ended.

2. **`performUpkeep()` ([L315](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/BaseAuction.sol#L315), [L342](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/BaseAuction.sol#L342))** fetches prices with `withValidation = true`. If any price is stale at execution time, the function reverts with `Errors.StaleFeedData()`. Crucially, at L315, the `assetOut` (LINK) price is fetched first — if LINK's oracle is stale, the **entire batch** of eligible auctions is blocked, regardless of the freshness of individual asset prices.

3. **`bid()` ([L429](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/BaseAuction.sol#L429))** also fetches the asset price with `withValidation = true`. Any transient oracle staleness prevents bidding on otherwise live auctions.

```solidity
// checkUpkeep — non-reverting
(uint256 assetPrice,, bool isPriceValid) = _getAssetPrice(asset, false); // L238

// performUpkeep — reverting
(assetOutPrice,,) = _getAssetPrice(assetOut, true);  // L315 — blocks ALL auctions
(assetPrice,,) = _getAssetPrice(asset, true);         // L342 — blocks this asset

// bid — reverting
(uint256 assetPrice,,) = _getAssetPrice(asset, true); // L429 — blocks bidding
```

### Impact

- **performUpkeep DoS**: A stale `assetOut` (LINK) feed blocks ALL eligible assets in the batch, not just the one with the stale feed. Multiple assets worth auctioning are simultaneously blocked by a single oracle gap.
- **bid() DoS**: Active auctions cannot receive bids when the auctioned asset's oracle is temporarily stale, even if the auction is still within its valid duration.
- **Fund accumulation**: Fee aggregator balances accumulate without being auctioned. Protocol revenue is delayed until the oracle recovers.
- **Missed opportunities**: Dutch auction opportunities are time-sensitive. By the time the oracle recovers and a new `performUpkeep` succeeds, market conditions may have changed unfavorably.

Given that Chainlink Data Streams can experience brief heartbeat gaps (seconds to minutes), and the staleness threshold is typically 1 hour, a gap near the threshold boundary is a realistic scenario during network congestion or Data Streams maintenance.

### Attack Scenario

1. Keeper calls `checkUpkeep()` when all prices are fresh. Returns `performData` with eligible USDC and WETH assets.
2. Between `checkUpkeep` and `performUpkeep`, the LINK (assetOut) Data Streams feed experiences a heartbeat gap. The last update was 61 minutes ago (threshold = 1 hour).
3. Keeper calls `performUpkeep(performData)`. At L315, `_getAssetPrice(assetOut, true)` reverts with `StaleFeedData`.
4. Both USDC and WETH auctions fail to start. Funds remain in the fee aggregator.
5. Meanwhile, bidders monitoring active auctions also cannot bid because `_getAssetPrice(asset, true)` at L429 reverts for any asset with a stale feed.
6. The system is fully DoS'd until the oracle recovers.

## Recommended mitigation steps

**Option A**: Skip individual assets with stale prices instead of reverting the entire batch in `performUpkeep`:

```solidity
for (uint256 i; i < eligibleAssets.length; ++i) {
    address asset = eligibleAssets[i].asset;
    // ...
    try this._getAssetPriceExternal(asset) returns (uint256 assetPrice) {
        // proceed with auction start
    } catch {
        continue; // skip this asset, don't revert the batch
    }
}
```

**Option B**: Cache the assetOut price at the `checkUpkeep` level and include it in `performData`, with a maximum age validation in `performUpkeep`.

**Option C**: For `bid()`, consider using the data feed fallback with a wider staleness window as a last resort, since bidders are already exposed to price risk via the Dutch auction decay.

---END COPY FOR VULNERABILITY DETAILS---

## Proof of Concept (PoC)

---COPY FROM HERE---

Run with:

```bash
forge test --match-contract M01_OracleStalenessDoS -vvv
```

```solidity
// SPDX-License-Identifier: BUSL-1.1
pragma solidity 0.8.26;

import {C4PoC} from "./C4PoC.t.sol";
import {BaseAuction} from "src/BaseAuction.sol";
import {PriceManager} from "src/PriceManager.sol";
import {Common} from "src/libraries/Common.sol";
import {Errors} from "src/libraries/Errors.sol";
import {IERC20} from "@openzeppelin/contracts/interfaces/IERC20.sol";

/// @title M-01: Oracle Staleness DoS on performUpkeep and bid()
/// @notice checkUpkeep uses _getAssetPrice(asset, false) (non-reverting) while
///         performUpkeep uses _getAssetPrice(assetOut, true) (reverting on stale).
///         A transient oracle staleness event blocks ALL eligible auctions in the batch.
///         bid() is also affected — stale price prevents bidding on active auctions.
///
/// Root cause:
///   - BaseAuction.sol L238: checkUpkeep → _getAssetPrice(asset, false)
///   - BaseAuction.sol L315: performUpkeep → _getAssetPrice(assetOut, true)
///   - BaseAuction.sol L429: bid → _getAssetPrice(asset, true)
///
/// Impact: Medium — DoS on core auction functionality. Fee aggregator balances
///         accumulate and auction opportunities are missed until oracle recovers.
contract M01_OracleStalenessDoS is C4PoC {

    /// @notice Stale assetOut (LINK) price blocks ALL new auctions even when
    ///         assetIn (USDC, WETH) prices are still valid.
    function test_M01_staleAssetOutBlocksAllAuctions() public {
        // 1. Fund fee aggregator with multiple assets eligible for auction
        deal(address(mockUSDC), address(feeAggregator), 100_000e6);  // $100k USDC
        deal(address(mockWETH), address(feeAggregator), 25e18);      // $100k WETH

        // 2. checkUpkeep succeeds — all prices are fresh
        _changePrank(auctionAdmin);
        (bool upkeepNeeded, bytes memory performData) = auction.checkUpkeep("");
        assertTrue(upkeepNeeded, "Upkeep should be needed with eligible assets");

        // 3. Time passes — assetOut (LINK) oracle becomes stale (threshold = 1h)
        uint32 linkStaleness = auction.getFeedInfo(address(mockLINK)).stalenessThreshold;
        skip(linkStaleness + 1);

        // 4. Refresh only assetIn prices — LINK oracle has a heartbeat gap
        //    We only transmit WETH and USDC (not LINK) to simulate LINK staleness
        _changePrank(priceAdmin);
        {
            bytes[] memory reports = new bytes[](2);
            bytes32[3] memory ctx = [bytes32(0), bytes32(0), bytes32(0)];
            bytes32[] memory rs = new bytes32[](2);
            bytes32[] memory ss = new bytes32[](2);
            bytes32 rawVs;

            PriceManager.ReportV3 memory wethReport;
            wethReport.dataStreamsFeedId = i_mockWETHFeedId;
            wethReport.price = int192(uint192(4_000e18));
            wethReport.observationsTimestamp = uint32(block.timestamp);
            reports[0] = abi.encode(ctx, abi.encode(wethReport), rs, ss, rawVs);

            PriceManager.ReportV3 memory usdcReport;
            usdcReport.dataStreamsFeedId = i_mockUSDCFeedId;
            usdcReport.price = int192(uint192(1e18));
            usdcReport.observationsTimestamp = uint32(block.timestamp);
            reports[1] = abi.encode(ctx, abi.encode(usdcReport), rs, ss, rawVs);

            auction.transmit(reports);
        }

        // 5. performUpkeep REVERTS — assetOut (LINK) price is stale at L315
        _changePrank(auctionAdmin);
        vm.expectRevert(Errors.StaleFeedData.selector);
        auction.performUpkeep(performData);

        // 6. Funds remain stuck in fee aggregator — no auctions started
        assertEq(
            IERC20(address(mockUSDC)).balanceOf(address(feeAggregator)),
            100_000e6,
            "USDC should still be in fee aggregator (auction blocked)"
        );
        assertEq(
            IERC20(address(mockWETH)).balanceOf(address(feeAggregator)),
            25e18,
            "WETH should still be in fee aggregator (auction blocked)"
        );
    }

    /// @notice Stale price also blocks bid() on active auctions.
    function test_stalePriceBlocksBidding() public {
        // 1. Start a USDC auction normally
        _startAuction(address(mockUSDC), 100_000e6);

        // Verify auction started
        uint256 auctionStart = auction.getAuctionStart(address(mockUSDC));
        assertGt(auctionStart, 0, "USDC auction should be active");

        // 2. Time passes — USDC feed goes stale
        skip(1 hours + 1);

        // 3. Attacker tries to bid — _getAssetPrice(asset, true) at L429 reverts
        _changePrank(attacker);
        deal(address(mockLINK), attacker, 10_000e18);
        IERC20(address(mockLINK)).approve(address(auction), type(uint256).max);

        vm.expectRevert(Errors.StaleFeedData.selector);
        auction.bid(address(mockUSDC), 1_000e6, "");
    }
}
```

**Test results:**
```
Ran 3 tests for test/poc/M01_OracleStalenessDoS.t.sol:M01_OracleStalenessDoS
[PASS] testSubmissionValidity() (gas: 166)
[PASS] test_M01_staleAssetOutBlocksAllAuctions() (gas: 466851)
[PASS] test_stalePriceBlocksBidding() (gas: 520273)
Suite result: ok. 3 passed; 0 failed; 0 skipped
```

---END COPY FOR POC---
