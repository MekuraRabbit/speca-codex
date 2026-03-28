# C4 Submission Form

## Severity rating

Low

## Title

transmit() accepts future-dated price reports, extending effective validity window and defeating staleness protection

## Links to root cause

```
https://github.com/code-423n4/2026-03-chainlink/blob/main/src/PriceManager.sol#L162
https://github.com/code-423n4/2026-03-chainlink/blob/main/src/PriceManager.sol#L178-L179
```

## Vulnerability details

---COPY FROM HERE---

## Finding description and impact

`PriceManager.transmit()` validates that `report.observationsTimestamp` is not too old ([L162](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/PriceManager.sol#L162)), but does **not** check if it is in the future:

```solidity
if (report.observationsTimestamp < block.timestamp - feedInfo.stalenessThreshold) {
    revert Errors.StaleFeedData();   // ← Only rejects TOO OLD
}
// ← NO check: report.observationsTimestamp > block.timestamp
```

The `observationsTimestamp` is stored directly into `s_dataStreamsPrice[asset]` ([L178-179](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/PriceManager.sol#L178)):

```solidity
s_dataStreamsPrice[asset] = DataStreamsPriceInfo({
    usdPrice: usdPrice.toUint224(),
    timestamp: report.observationsTimestamp   // ← Future timestamp stored as-is
});
```

Later, `_getAssetPrice()` checks staleness as `updatedAt < block.timestamp - stalenessThreshold` ([L405](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/PriceManager.sol#L405)). A future-dated `updatedAt` will always be greater than `minTimestamp`, so the price is **never considered stale** until `block.timestamp` catches up to `futureTimestamp + stalenessThreshold`.

### Impact

A report with `observationsTimestamp = block.timestamp + N` extends the effective validity window from `stalenessThreshold` to `stalenessThreshold + N`:

| Scenario | Normal | Future-dated (N=1 day) |
|---|---|---|
| stalenessThreshold | 1 hour | 1 hour |
| Price becomes stale at | T + 1h | T + 25h |
| **Effective validity** | **1 hour** | **25 hours (25x)** |

During this extended window:

1. **Oracle price drift**: Real market prices can diverge significantly from the stored price. The staleness mechanism — the protocol's primary defense against stale prices — is defeated.

2. **Bidder exploitation**: Bidders can bid using prices that are hours old. If the real LINK price moved 50% in that time, either the bidder or the protocol absorbs the loss.

3. **Fallback bypass**: The future-dated Data Streams price always appears "fresher" than the Chainlink data feed fallback (`updatedAt` comparison at [L390](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/PriceManager.sol#L390)), preventing the fallback from ever activating — even when the Data Streams price is objectively outdated.

### Defense-in-depth argument

While `transmit()` requires `PRICE_ADMIN_ROLE` and reports pass through `VerifierProxy.verifyBulk()`, on-chain timestamp validation is a standard defense-in-depth measure:

- **DON clock skew**: Decentralized Oracle Network nodes may have clock differences. A node slightly ahead produces future-dated reports that pass cryptographic verification but have incorrect timestamps.
- **VerifierProxy scope**: The VerifierProxy validates cryptographic signatures, not timestamp sanity. Timestamp validation is the consuming contract's responsibility.
- **Precedent**: Chainlink's own `latestRoundData()` returns timestamps that consumers are [recommended to validate](https://docs.chain.link/data-feeds#check-the-timestamp-of-the-latest-answer) — the same principle applies to Data Streams reports.

## Recommended mitigation steps

Add an upper-bound timestamp check in `transmit()`:

```solidity
if (report.observationsTimestamp < block.timestamp - feedInfo.stalenessThreshold) {
    revert Errors.StaleFeedData();
}
// NEW: Reject future-dated reports
if (report.observationsTimestamp > block.timestamp) {
    revert Errors.InvalidTimestamp();
}
```

---END COPY FOR VULNERABILITY DETAILS---

## Proof of Concept (PoC)

---COPY FROM HERE---

Run with:

```bash
forge test --match-contract M07_FutureTimestampExtendsValidity -vvv
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

contract M07_FutureTimestampExtendsValidity is C4PoC {

    function test_M07_futureTimestampExtendsValidity() public {
        // 1. Start a USDC auction
        _startAuction(address(mockUSDC), 100_000e6);

        // 2. Submit a price report with USDC timestamp 1 DAY in the future
        _changePrank(priceAdmin);

        bytes[] memory unverifiedReports = new bytes[](3);
        bytes32[3] memory context = [bytes32(0), bytes32(0), bytes32(0)];
        bytes32[] memory rs = new bytes32[](2);
        bytes32[] memory ss = new bytes32[](2);
        bytes32 rawVs;

        PriceManager.ReportV3 memory wethReport;
        wethReport.dataStreamsFeedId = auction.getFeedInfo(address(mockWETH)).dataStreamsFeedId;
        wethReport.price = int192(uint192(4_000e18));
        wethReport.observationsTimestamp = uint32(block.timestamp);
        unverifiedReports[0] = abi.encode(context, abi.encode(wethReport), rs, ss, rawVs);

        // USDC: FUTURE timestamp — 1 day ahead
        PriceManager.ReportV3 memory usdcReport;
        usdcReport.dataStreamsFeedId = auction.getFeedInfo(address(mockUSDC)).dataStreamsFeedId;
        usdcReport.price = int192(uint192(1e18));
        usdcReport.observationsTimestamp = uint32(block.timestamp + 1 days);
        unverifiedReports[1] = abi.encode(context, abi.encode(usdcReport), rs, ss, rawVs);

        PriceManager.ReportV3 memory linkReport;
        linkReport.dataStreamsFeedId = auction.getFeedInfo(address(mockLINK)).dataStreamsFeedId;
        linkReport.price = int192(uint192(20e18));
        linkReport.observationsTimestamp = uint32(block.timestamp);
        unverifiedReports[2] = abi.encode(context, abi.encode(linkReport), rs, ss, rawVs);

        // 3. transmit() accepts future timestamp — no revert
        auction.transmit(unverifiedReports);

        // 4. Verify future timestamp is stored
        (uint256 usdcPrice, uint256 usdcUpdatedAt, bool usdcValid) =
            auction.getAssetPrice(address(mockUSDC));
        assertEq(usdcPrice, 1e18);
        assertGt(usdcUpdatedAt, block.timestamp, "Timestamp is in the future");
        assertTrue(usdcValid, "Future-dated price is valid");

        // 5. Skip past normal staleness threshold (1 hour)
        skip(1 hours + 1);

        // 6. Normal-timestamped prices are now stale
        (,, bool wethValid) = auction.getAssetPrice(address(mockWETH));
        (,, bool linkValid) = auction.getAssetPrice(address(mockLINK));
        assertFalse(wethValid, "WETH stale after 1h");
        assertFalse(linkValid, "LINK stale after 1h");

        // 7. Future-dated USDC price is STILL VALID
        (,, bool usdcStillValid) = auction.getAssetPrice(address(mockUSDC));
        assertTrue(usdcStillValid, "USDC still valid after 1h — staleness bypassed!");

        // Effective validity = 25 hours instead of 1 hour (25x extension)
    }
}
```

---END COPY FOR POC---
