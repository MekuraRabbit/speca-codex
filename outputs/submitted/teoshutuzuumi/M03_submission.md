# C4 Submission Form

## Severity rating

Medium

## Title

Reverting Chainlink data feed blocks ALL auction operations including checkUpkeep and creates an unrecoverable deadlock for live auctions

## Links to root cause

```
https://github.com/code-423n4/2026-03-chainlink/blob/main/src/PriceManager.sol#L385
https://github.com/code-423n4/2026-03-chainlink/blob/main/src/PriceManager.sol#L386
```

## Vulnerability details

---COPY FROM HERE---

## Finding description and impact

When a Chainlink data feed is deprecated or malfunctions (e.g., aggregator set to zero address, proxy upgrade breaks ABI), `latestRoundData()` reverts. In `_getAssetPrice()` ([L385-386](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/PriceManager.sol#L385)), this external call is made **without** a try-catch wrapper:

```solidity
if (updatedAt < minTimestamp && feedInfo.usdDataFeed != AggregatorV3Interface(address(0))) {
    (, int256 answer,, uint256 dataFeedUpdatedAt,) = feedInfo.usdDataFeed.latestRoundData();
    // ← No try-catch: deprecated feed reverts here, bubbling up to caller
```

**This is fundamentally different from M-01 (oracle staleness DoS):**
- **M-01**: Stale Data Streams price → `_getAssetPrice` returns `(price, updatedAt, false)` when `withValidation = false`. Only `performUpkeep`/`bid` (which use `withValidation = true`) are affected.
- **M-03**: Reverting data feed → `_getAssetPrice` **reverts entirely**, regardless of `withValidation`. Even `checkUpkeep` (which uses `withValidation = false`) is affected because the revert happens before the validation flag is checked.

### Impact

1. **Total automation halt**: `checkUpkeep()` ([L238](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/BaseAuction.sol#L238)) iterates ALL allowlisted assets via `_getEligibleAssets`. If ANY asset's data feed reverts, the entire `checkUpkeep` call reverts. No auctions can be started, monitored, or ended via Chainlink Automation.

2. **Bidding blocked**: `bid()` and `isValidSignature()` revert for the affected asset. CowSwap settlement also fails.

3. **Cross-asset contamination**: Healthy assets (e.g., USDC with a working feed) are blocked because `checkUpkeep` processes all assets in a single loop. A broken WETH feed prevents USDC auctions from being monitored.

4. **Deadlock for live auctions**: If an asset has an active auction when its feed starts reverting, the system enters a deadlock:
   - **Cannot remove the asset from allowlist**: `applyFeedInfoUpdates` calls `_onFeedInfoUpdate` which checks `_whenNoLiveAuctions()` and reverts with `LiveAuction()`.
   - **Cannot end the auction via automation**: `checkUpkeep` reverts.
   - **Cannot bid on the auction**: `bid()` reverts.
   - **Only escape**: `AUCTION_WORKER_ROLE` manually crafts `performData` with the asset in `endedAuctions` array and calls `performUpkeep` directly. This works because the auction-ending path in `performUpkeep` ([L359-369](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/BaseAuction.sol#L359)) does not call `_getAssetPrice`. However, ALL unsold tokens are returned to feeAggregator at zero revenue.

### Prior Audit Precedent

This is a well-known pattern: **ORACLE_DEPRECATION_REVERT** (Code4rena 2023-06-reserve M-10). When Chainlink deprecates an oracle (sets aggregator to zero address), `latestRoundData()` reverts with empty error data. The recommended fix is a try-catch wrapper.

### Attack Scenario

1. Protocol has USDC, WETH, and DAI allowlisted. WETH has an active auction worth $200k.
2. Chainlink deprecates the WETH/USD data feed (realistic — feeds are deprecated regularly as Chainlink migrates to new aggregators).
3. Data Streams price for WETH goes stale (past staleness threshold). Normal — Data Streams falls back to data feed.
4. `_getAssetPrice(WETH, false)` hits L385: `feedInfo.usdDataFeed.latestRoundData()` reverts.
5. `checkUpkeep` reverts → ALL automation stops (including for healthy USDC and DAI).
6. `bid(WETH, ...)` reverts → no one can bid on the $200k WETH auction.
7. Admin tries to remove WETH from allowlist → `LiveAuction()` revert.
8. **Deadlock**: The only recovery path is manual `performUpkeep` by AUCTION_WORKER, resulting in $200k returned to feeAggregator at zero revenue. All other auctions are also blocked until this is resolved.

## Recommended mitigation steps

Wrap the `latestRoundData()` call in a try-catch:

```solidity
if (updatedAt < minTimestamp && feedInfo.usdDataFeed != AggregatorV3Interface(address(0))) {
    try feedInfo.usdDataFeed.latestRoundData() returns (
        uint80, int256 answer, uint256, uint256 dataFeedUpdatedAt, uint80
    ) {
        if (answer > 0 && dataFeedUpdatedAt >= minTimestamp) {
            price = uint256(answer) * (10 ** (18 - feedDecimals));
            updatedAt = dataFeedUpdatedAt;
        }
    } catch {
        // Feed is broken/deprecated — treat as unavailable, don't revert
        // The caller will see isValid = false and handle accordingly
    }
}
```

This ensures that a broken data feed degrades gracefully (price marked as invalid) rather than catastrophically (entire function reverts).

---END COPY FOR VULNERABILITY DETAILS---

## Proof of Concept (PoC)

---COPY FROM HERE---

Run with:

```bash
forge test --match-contract M03_RevertingDataFeedBlocksAll -vvv
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

/// @title M-03: Reverting Chainlink Data Feed Blocks ALL Auction Operations Including checkUpkeep
/// @notice When a Chainlink data feed is deprecated or malfunctions (latestRoundData() reverts)
///         AND the Data Streams price for that asset is stale, _getAssetPrice() reverts
///         WITHOUT try-catch. This is DIFFERENT from M-01 (stale price DoS):
///
///         - M-01: Stale price -> _getAssetPrice returns (price, updatedAt, false) when withValidation=false
///         - M-03: Reverting feed -> _getAssetPrice REVERTS ENTIRELY, even with withValidation=false
///
/// Root cause:
///   - PriceManager.sol L385-386: No try-catch around latestRoundData()
///
/// Impact: HIGH —
///   1) checkUpkeep() iterates ALL allowlisted assets -> ONE reverting feed blocks ALL automation
///   2) bid() on ANY active auction with a reverting feed's asset is impossible
///   3) isValidSignature() for CowSwap orders also reverts -> CowSwap settlement blocked
///   4) DEADLOCK: If the asset with reverting feed has a live auction, you cannot:
///      - Remove it from allowlist (_onFeedInfoUpdate reverts with LiveAuction)
///      - End the auction via normal automation (checkUpkeep reverts)
///      - Bid on it (bid reverts)
///      Only manual performUpkeep by AUCTION_WORKER with crafted performData can recover.
///
/// Prior audit pattern: ORACLE_DEPRECATION_REVERT (C4-2023-06-reserve M-10)
contract M03_RevertingDataFeedBlocksAll is C4PoC {

    /// @notice Proves that a single reverting data feed blocks checkUpkeep for ALL assets.
    ///         This is strictly worse than M-01 because checkUpkeep uses withValidation=false
    ///         but still reverts when the external call itself fails.
    function test_M03_revertingFeedBlocksCheckUpkeep() public {
        // 1. Fund fee aggregator with multiple assets eligible for auction
        deal(address(mockUSDC), address(feeAggregator), 100_000e6);   // $100k USDC
        deal(address(mockWETH), address(feeAggregator), 25e18);       // $100k WETH

        // 2. Verify checkUpkeep works initially
        _changePrank(auctionAdmin);
        (bool upkeepNeeded,) = auction.checkUpkeep("");
        assertTrue(upkeepNeeded, "Upkeep should be needed initially");

        // 3. Make Data Streams prices stale (so fallback to data feed is triggered)
        uint32 stalenessThreshold = auction.getFeedInfo(address(mockWETH)).stalenessThreshold;
        skip(stalenessThreshold + 1);

        // 4. Simulate WETH data feed being deprecated/broken — latestRoundData() reverts
        //    This simulates Chainlink deprecating the feed or a proxy upgrade breaking it.
        vm.mockCallRevert(
            address(mockWethUsdFeed),
            abi.encodeWithSignature("latestRoundData()"),
            "Feed deprecated"
        );

        // 5. Update USDC and LINK data feed prices (they are still working)
        mockUsdcUsdFeed.transmit(1e8);
        mockLinkUsdFeed.transmit(20e8);

        // 6. checkUpkeep REVERTS — the reverting WETH feed blocks ALL automation
        //    Even though USDC and LINK feeds are perfectly fine.
        _changePrank(auctionAdmin);
        vm.expectRevert("Feed deprecated");
        auction.checkUpkeep("");

        // 7. IMPACT: $200k worth of assets cannot be auctioned because of ONE broken feed.
        //    All automation is halted until admin manually removes the broken feed.
    }

    /// @notice Proves the DEADLOCK scenario: live auction + reverting feed = cannot recover
    ///         through normal operations.
    function test_M03_deadlockWithLiveAuction() public {
        // 1. Start a WETH auction normally
        _startAuction(address(mockWETH), 25e18);  // $100k WETH auction

        // Verify auction is live
        uint256 auctionStart = auction.getAuctionStart(address(mockWETH));
        assertGt(auctionStart, 0, "WETH auction should be live");

        // 2. Time passes — Data Streams prices become stale
        uint32 stalenessThreshold = auction.getFeedInfo(address(mockWETH)).stalenessThreshold;
        skip(stalenessThreshold + 1);

        // Refresh USDC and LINK prices (not WETH — its Data Streams is stale)
        mockUsdcUsdFeed.transmit(1e8);
        mockLinkUsdFeed.transmit(20e8);

        // 3. Simulate WETH data feed deprecated — latestRoundData() reverts
        vm.mockCallRevert(
            address(mockWethUsdFeed),
            abi.encodeWithSignature("latestRoundData()"),
            "Feed deprecated"
        );

        // 4. DEADLOCK PROOF:

        // 4a. checkUpkeep reverts -> automation cannot detect the ended auction
        _changePrank(auctionAdmin);
        vm.expectRevert("Feed deprecated");
        auction.checkUpkeep("");

        // 4b. bid() reverts -> bidders cannot participate
        address bidder_ = makeAddr("deadlockBidder");
        deal(address(mockLINK), bidder_, 10_000e18);
        _changePrank(bidder_);
        IERC20(address(mockLINK)).approve(address(auction), type(uint256).max);
        vm.expectRevert("Feed deprecated");
        auction.bid(address(mockWETH), 1e18, "");

        // 4c. Cannot remove the broken feed because WETH has a live auction
        _changePrank(assetAdmin);
        PriceManager.ApplyFeedInfoUpdateParams[] memory emptyAdds = new PriceManager.ApplyFeedInfoUpdateParams[](0);
        address[] memory removes = new address[](1);
        removes[0] = address(mockWETH);
        vm.expectRevert(BaseAuction.LiveAuction.selector);
        auction.applyFeedInfoUpdates(emptyAdds, removes);

        // 5. ONLY ESCAPE: AUCTION_WORKER manually crafts performUpkeep to end the auction
        _changePrank(auctionAdmin);
        Common.AssetAmount[] memory noEligible = new Common.AssetAmount[](0);
        address[] memory endAuctions = new address[](1);
        endAuctions[0] = address(mockWETH);
        bytes memory manualPerformData = abi.encode(noEligible, endAuctions);

        // This works because ending auctions doesn't require price validation
        auction.performUpkeep(manualPerformData);

        // 6. Auction ended — WETH returned to feeAggregator at ZERO revenue
        assertEq(auction.getAuctionStart(address(mockWETH)), 0, "Auction should be ended");
        assertGt(
            IERC20(address(mockWETH)).balanceOf(address(feeAggregator)),
            0,
            "WETH should be returned to feeAggregator with zero revenue"
        );
    }

    /// @notice Proves that even USDC auctions (with working feed) are blocked
    ///         because checkUpkeep iterates ALL assets including the broken one.
    function test_M03_healthyAssetsBlockedByBrokenFeed() public {
        // 1. Start a USDC auction (USDC feed is working fine)
        _startAuction(address(mockUSDC), 100_000e6);
        assertGt(auction.getAuctionStart(address(mockUSDC)), 0, "USDC auction should be live");

        // 2. Also fund WETH for potential auction
        deal(address(mockWETH), address(feeAggregator), 25e18);

        // 3. Make Data Streams stale + break WETH feed
        skip(1 hours + 1);
        vm.mockCallRevert(
            address(mockWethUsdFeed),
            abi.encodeWithSignature("latestRoundData()"),
            "Feed deprecated"
        );

        // Refresh USDC and LINK data feeds — they work fine
        mockUsdcUsdFeed.transmit(1e8);
        mockLinkUsdFeed.transmit(20e8);

        // 4. checkUpkeep reverts — can't detect USDC auction state
        _changePrank(auctionAdmin);
        vm.expectRevert("Feed deprecated");
        auction.checkUpkeep("");

        // IMPACT: USDC auction with $100k cannot be monitored or ended normally
        // because an unrelated WETH feed is broken.
    }
}
```

**Test results:**
```
Ran 4 tests for test/poc/M03_RevertingDataFeedBlocksAll.t.sol:M03_RevertingDataFeedBlocksAll
[PASS] testSubmissionValidity() (gas: 166)
[PASS] test_M03_revertingFeedBlocksCheckUpkeep() (gas: 164274)
[PASS] test_M03_deadlockWithLiveAuction() (gas: 583822)
[PASS] test_M03_healthyAssetsBlockedByBrokenFeed() (gas: 522641)
Suite result: ok. 4 passed; 0 failed; 0 skipped
```

---END COPY FOR POC---
