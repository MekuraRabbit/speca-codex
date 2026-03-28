# C4 Submission Form

## Severity rating

Medium

## Title

bid() lacks slippage protection, allowing oracle price updates to inflate bidder payment with no way to cap maximum assetOut cost

## Links to root cause

```
https://github.com/code-423n4/2026-03-chainlink/blob/main/src/BaseAuction.sol#L410
https://github.com/code-423n4/2026-03-chainlink/blob/main/src/BaseAuction.sol#L442
https://github.com/code-423n4/2026-03-chainlink/blob/main/src/BaseAuction.sol#L453
```

## Vulnerability details

---COPY FROM HERE---

## Finding description and impact

The `bid()` function ([L410-414](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/BaseAuction.sol#L410)) accepts three parameters: `asset`, `amount`, and `data`. It does **not** accept a `maxAssetOutAmount` parameter to cap the maximum payment:

```solidity
function bid(
    address asset,
    uint256 amount,
    bytes calldata data
) external whenNotPaused {
```

The `assetOutAmount` (how much LINK the bidder must pay) is calculated at execution time based on the **current** oracle price ([L429](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/BaseAuction.sol#L429), [L442](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/BaseAuction.sol#L442)):

```solidity
(uint256 assetPrice,,) = _getAssetPrice(asset, true);        // L429 - fetched at execution time
// ...
uint256 assetOutAmount = _getAssetOutAmount(assetParams, assetPrice, amount, elapsedTime, true); // L442
// ...
IERC20(assetOut).safeTransferFrom(msg.sender, address(this), assetOutAmount); // L453 - pulls LINK
```

If the oracle price changes between the bidder's transaction submission and execution (e.g., a `transmit()` call is included earlier in the same block by the block builder), the bidder pays a different -- potentially much higher -- amount of LINK with **no way to revert or cap the payment**.

### Critical Asymmetry with CowSwap Path

The CowSwap path (`isValidSignature`) **does** have slippage protection via the `order.buyAmount` field ([L155-156](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/GPV2CompatibleAuction.sol#L155)):

```solidity
// CowSwap path -- PROTECTED:
if (order.buyAmount < minBuyAmount) {
    revert InsufficientBuyAmount(order.buyAmount, minBuyAmount);
}
// order.buyAmount acts as the solver's maximum payment cap
```

This creates a two-tier system where CowSwap solvers have price protection but direct bidders do not.

### Impact

1. **Direct fund loss for bidders**: A LINK price drop (e.g., $20 to $10) between tx submission and execution doubles the LINK payment. Since bidders commonly approve `type(uint256).max` for gas efficiency, there is no secondary protection.

2. **MEV extraction**: Block builders can order `transmit()` (legitimate oracle update) before `bid()` transactions to maximize LINK extraction from bidders. This is a **zero-cost** MEV opportunity -- the block builder doesn't need to manipulate the oracle, just reorder legitimate transactions.

3. **Asymmetric risk**: Direct bidders bear slippage risk that CowSwap solvers don't. This discourages direct bidding and concentrates settlement through CowSwap, reducing competition and potentially worsening auction outcomes for the protocol.

### Attack Scenario

1. Bidder calls `getAssetOutAmount()` off-chain -- expects to pay ~2,550 LINK for 50,000 USDC (LINK=$20).
2. Bidder submits `bid(USDC, 50000e6, "")` with `approve(type(uint256).max)`.
3. In the same block, a legitimate `transmit()` updates LINK price from $20 to $10.
4. Block builder orders: `transmit()` first, then `bid()`.
5. `bid()` executes with LINK=$10. Bidder pays ~5,100 LINK instead of ~2,550.
6. **Bidder lost ~2,550 LINK ($25,500) with no way to prevent it.**
7. A CowSwap solver in the same situation would have set `order.buyAmount = 2550e18`, and `isValidSignature` would revert with `InsufficientBuyAmount`.

### Prior Audit Precedent

- Code4rena 2023-12 Revolution Protocol #91 (Medium): "Missing slippage protection in buyToken"
- Code4rena 2023-11 Canto #12 (Medium): "No slippage control in bonding curve buy"

## Recommended mitigation steps

Add a `maxAssetOutAmount` parameter to `bid()`:

```solidity
function bid(
    address asset,
    uint256 amount,
    uint256 maxAssetOutAmount, // NEW: slippage protection
    bytes calldata data
) external whenNotPaused {
    // ... existing validations ...

    uint256 assetOutAmount = _getAssetOutAmount(assetParams, assetPrice, amount, elapsedTime, true);

    // Add slippage check
    if (assetOutAmount > maxAssetOutAmount) {
        revert SlippageExceeded(assetOutAmount, maxAssetOutAmount);
    }

    // ... rest of function ...
}
```

This brings `bid()` in line with the CowSwap path's slippage protection and is a standard DeFi pattern (similar to Uniswap's `amountOutMin`, Curve's `min_dy`, etc.).

---END COPY FOR VULNERABILITY DETAILS---

## Proof of Concept (PoC)

---COPY FROM HERE---

Run with:

```bash
forge test --match-contract M06_BidNoSlippageProtection -vvv
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

/// @title M-06: bid() Lacks Slippage Protection -- No maxAssetOutAmount Parameter
/// @notice BaseAuction.bid() allows permissionless bidders to specify the auctioned asset
///         and amount they want, but provides NO parameter to cap the maximum assetOut (LINK)
///         payment. The only protection is the bidder's ERC20 approval, which is typically
///         set broadly and does not provide per-bid granularity.
///
///         In contrast, the CowSwap path (isValidSignature) DOES have slippage protection
///         via the order.buyAmount field, creating an asymmetry where direct bidders are
///         less protected than CowSwap solvers.
///
/// Root cause: BaseAuction.sol L410-414:
///   ```
///   function bid(
///       address asset,
///       uint256 amount,
///       bytes calldata data
///   ) external whenNotPaused {
///   ```
///   No `uint256 maxAssetOutAmount` parameter exists.
///
/// Impact: Medium --
///   1) Oracle price updates (via transmit()) in the same block can change the assetOutAmount
///      between tx submission and execution
///   2) A bidder who approved a large LINK amount (e.g., type(uint256).max for gas efficiency)
///      has no protection against unfavorable price changes
///   3) Block builders can order transmit() before bid() to extract value from bidders
///   4) Prior art: Code4rena Revolution Protocol 2023-12 #91, Canto 2023-11 #12 (Medium)
///
/// The CowSwap path (isValidSignature) IS protected:
///   GPV2CompatibleAuction.sol L155-156:
///   ```
///   if (order.buyAmount < minBuyAmount) {
///       revert InsufficientBuyAmount(order.buyAmount, minBuyAmount);
///   }
///   ```
///   order.buyAmount acts as the solver's maxPayment -- a slippage cap.
contract M06_BidNoSlippageProtection is C4PoC {

    /// @notice Demonstrates that a price update in the same block causes the bidder
    ///         to pay significantly more LINK than expected, with no way to cap payment.
    function test_M06_priceChangeInflatesBidCost() public {
        // 1. Start a $100k USDC auction
        _startAuction(address(mockUSDC), 100_000e6);

        // 2. Skip to mid-auction for realistic pricing
        skip(12 hours);
        _refreshPrices();

        // 3. Bidder checks the expected cost BEFORE bidding
        uint256 expectedCost = auction.getAssetOutAmount(address(mockUSDC), 50_000e6, block.timestamp);

        // 4. Bidder approves generously (common gas optimization pattern)
        address directBidder = makeAddr("directBidder");
        deal(address(mockLINK), directBidder, 100_000e18);
        _changePrank(directBidder);
        IERC20(address(mockLINK)).approve(address(auction), type(uint256).max);

        // 5. BEFORE the bid executes, a legitimate oracle update changes LINK price
        //    (transmit() is called by automation in the same block, ordered first by block builder)
        _changePrank(priceAdmin);
        _transmitPrices(4_000e18, 1e18, 10e18); // LINK drops from $20 to $10

        // 6. NOW the bid executes with the NEW price -- bidder pays ~2x more LINK
        _changePrank(directBidder);
        uint256 linkBefore = IERC20(address(mockLINK)).balanceOf(directBidder);
        auction.bid(address(mockUSDC), 50_000e6, "");
        uint256 linkAfter = IERC20(address(mockLINK)).balanceOf(directBidder);
        uint256 actualCost = linkBefore - linkAfter;

        // 7. PROOF: Bidder paid significantly more than expected
        assertGt(actualCost, expectedCost * 180 / 100, "Bidder should pay >1.8x the expected cost");
    }

    /// @notice Shows the asymmetry: CowSwap path has slippage protection but bid() does not.
    function test_M06_cowswapHasSlippageButBidDoesNot() public {
        // 1. Start a USDC auction
        _startAuction(address(mockUSDC), 100_000e6);
        skip(12 hours);
        _refreshPrices();

        // 2. Get the current expected cost
        uint256 expectedCost = auction.getAssetOutAmount(address(mockUSDC), 50_000e6, block.timestamp);

        // 3. Prove bid() has no revert mechanism for overpayment:
        address directBidder = makeAddr("directBidder2");
        deal(address(mockLINK), directBidder, 100_000e18);
        _changePrank(directBidder);
        IERC20(address(mockLINK)).approve(address(auction), type(uint256).max);

        // Price update makes LINK cheaper -> bidder pays more LINK
        _changePrank(priceAdmin);
        _transmitPrices(4_000e18, 1e18, 10e18);

        // Bid succeeds at the inflated cost -- no way for bidder to revert
        _changePrank(directBidder);
        auction.bid(address(mockUSDC), 50_000e6, "");

        uint256 linkSpent = 100_000e18 - IERC20(address(mockLINK)).balanceOf(directBidder);

        // Bidder paid ~2x the original expectedCost
        assertGt(linkSpent, expectedCost * 180 / 100, "Direct bidder overpaid without protection");

        // KEY INSIGHT: If this were a CowSwap order with buyAmount = expectedCost,
        // the settlement would have failed because minBuyAmount > order.buyAmount.
        // The CowSwap path is protected; the bid() path is not.
    }
}
```

**Test results:**
```
Ran 3 tests for test/poc/M06_BidNoSlippageProtection.t.sol:M06_BidNoSlippageProtection
[PASS] testSubmissionValidity() (gas: 166)
[PASS] test_M06_priceChangeInflatesBidCost() (gas: 587432)
[PASS] test_M06_cowswapHasSlippageButBidDoesNot() (gas: 574918)
Suite result: ok. 3 passed; 0 failed; 0 skipped
```

---END COPY FOR POC---
