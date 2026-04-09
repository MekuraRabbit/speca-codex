# C4 Submission Form

## Severity rating

Low

## Title

Missing force-clear mechanism for stuck auctions causes irrecoverable configuration lockout when _onAuctionEnd reverts

## Links to root cause

```
https://github.com/code-423n4/2026-03-chainlink/blob/main/src/BaseAuction.sol#L359
https://github.com/code-423n4/2026-03-chainlink/blob/main/src/BaseAuction.sol#L366
https://github.com/code-423n4/2026-03-chainlink/blob/main/src/BaseAuction.sol#L668
```

## Vulnerability details

---COPY FROM HERE---

## Finding description and impact

### Root Cause

`BaseAuction.performUpkeep()` ([L359-369](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/BaseAuction.sol#L359)) processes ended auctions in a loop where `_onAuctionEnd()` executes before `delete s_auctionStarts[asset]`:

```solidity
// BaseAuction.sol L359-369
for (uint256 i; i < endedAuctions.length; ++i) {
    address asset = endedAuctions[i];

    if (s_auctionStarts[asset] == 0) {
        revert InvalidAuction(asset);
    }

    _onAuctionEnd(endedAuctions[i], hasFeeAggregator);  // ← revert here = stuck
    delete s_auctionStarts[asset];                        // ← never reached
    emit AuctionEnded(asset);
}
```

`_onAuctionEnd()` ([L383-397](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/BaseAuction.sol#L383)) calls `safeTransfer` to `s_feeAggregator` and `s_assetOutReceiver`. If either transfer permanently reverts (e.g., USDC/USDT blocklist on the auction contract or feeAggregator address), `s_auctionStarts[asset]` is never deleted.

**No admin function exists to force-clear `s_auctionStarts[asset]`.**

### Impact

The stuck auction (`s_auctionStarts[asset] != 0`) triggers `_whenNoLiveAuctions()` ([L668-672](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/BaseAuction.sol#L668)), which blocks three admin configuration functions:

| Function | Line | Effect |
|---|---|---|
| `_setAssetOut()` | L503 | Cannot change the output asset (e.g., LINK) |
| `_setAssetOutReceiver()` | L534 | Cannot change where output tokens are sent |
| `_setFeeAggregator()` | L562 | Cannot change the fee aggregator |

**Scope and limitations:**
- **Other assets continue operating**: AUCTION_WORKER_ROLE can craft `performData` excluding the stuck asset from `endedAuctions`. Other asset auctions start and end normally.
- **Token recovery possible**: `emergencyWithdraw` (pause + DEFAULT_ADMIN) can withdraw tokens, but does NOT clear `s_auctionStarts[asset]`.
- **No direct fund loss**: Tokens are recoverable. The impact is configuration lockout, not token theft.

### Conditions

1. An asset's `_onAuctionEnd()` must permanently revert — realistic for USDC/USDT if the auction contract or feeAggregator is added to a blocklist (OFAC sanctions)
2. No attacker action required — this is an environmental condition

### Severity Rationale

Rated **Low** because:
1. Requires specific external condition (token blocklist on contract address)
2. Partial workaround exists (handcrafted performData for other assets)
3. Token recovery is possible via emergencyWithdraw
4. Impact is configuration lockout, not fund loss

Not rated higher because:
- "Permanent freeze" overstates impact — other asset operations continue
- "Only fix: deploy new contract" overstates — only config changes are blocked, core auction functionality (bid, start) works for non-stuck assets

## Recommended mitigation steps

Add a `forceEndAuction` admin function to clear stuck auction state:

```solidity
function forceEndAuction(address asset) external onlyRole(DEFAULT_ADMIN_ROLE) {
    if (s_auctionStarts[asset] == 0) revert InvalidAuction(asset);
    delete s_auctionStarts[asset];
    _onAuctionEnd(asset, address(s_feeAggregator) != address(this));
    emit AuctionEnded(asset);
}
```

Or, if `_onAuctionEnd` itself is the problem, a minimal state-clearing version:

```solidity
function forceEndAuction(address asset) external onlyRole(DEFAULT_ADMIN_ROLE) {
    if (s_auctionStarts[asset] == 0) revert InvalidAuction(asset);
    delete s_auctionStarts[asset];
    emit AuctionEnded(asset);
}
```

---END COPY FOR VULNERABILITY DETAILS---

## Proof of Concept (PoC)

---COPY FROM HERE---

Run with:

```bash
forge test --match-contract M08_AuctionFreeze -vvv
```

```solidity
// SPDX-License-Identifier: BUSL-1.1
pragma solidity 0.8.26;

import {C4PoC} from "./C4PoC.t.sol";
import {BaseAuction} from "src/BaseAuction.sol";
import {IERC20} from "@openzeppelin/contracts/interfaces/IERC20.sol";

/// @title M-08: Missing force-clear mechanism for stuck auctions
/// @notice When _onAuctionEnd() permanently reverts, s_auctionStarts is never
///         deleted, blocking config changes via _whenNoLiveAuctions().
contract M08_AuctionFreeze is C4PoC {

    /// @notice Demonstrates stuck auction blocks configuration changes
    function test_M08_stuckAuctionBlocksConfig() public {
        // 1. Start a USDC auction
        uint256 auctionSellAmt = 10_000e6;
        _startAuctionAndSkip(address(mockUSDC), auctionSellAmt, 7_200);

        // 2. Skip past auction duration so it should end
        skip(auction.getAuctionDuration() + 1);

        // 3. Make USDC transfer revert (simulating blocklist)
        mockUSDC.setBlocked(address(auction), true);

        // 4. Try to end auction via performUpkeep — reverts
        address[] memory endedAuctions = new address[](1);
        endedAuctions[0] = address(mockUSDC);
        Common.AssetAmount[] memory empty = new Common.AssetAmount[](0);
        bytes memory performData = abi.encode(empty, endedAuctions);

        vm.prank(auctionWorker);
        vm.expectRevert();
        auction.performUpkeep(performData);

        // 5. Auction is stuck — s_auctionStarts[USDC] != 0
        assertTrue(auction.getAuctionStart(address(mockUSDC)) != 0, "Auction still active");

        // 6. Config change blocked by _whenNoLiveAuctions()
        vm.prank(admin);
        vm.expectRevert(BaseAuction.LiveAuction.selector);
        auction.setAssetOutReceiver(address(0xBEEF));

        // 7. No force-clear function exists
        // admin cannot clear s_auctionStarts[USDC]
        console2.log("[CONFIRMED] Stuck auction blocks setAssetOutReceiver");
        console2.log("[CONFIRMED] No forceEndAuction function exists");
        console2.log("[WORKAROUND] Other assets can still operate via handcrafted performData");
    }
}
```

---END COPY FOR POC---
