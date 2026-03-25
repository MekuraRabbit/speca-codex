# M-01: Asymmetric Price Validation Between checkUpkeep and performUpkeep/bid Causes Complete Auction DoS During Transient Oracle Staleness

## Severity

Medium

## Links to Root Cause

- [BaseAuction.sol#L238](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/BaseAuction.sol#L238) — `checkUpkeep` uses `_getAssetPrice(asset, false)` (non-reverting)
- [BaseAuction.sol#L315](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/BaseAuction.sol#L315) — `performUpkeep` uses `_getAssetPrice(assetOut, true)` (reverting)
- [BaseAuction.sol#L342](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/BaseAuction.sol#L342) — `performUpkeep` uses `_getAssetPrice(asset, true)` (reverting)
- [BaseAuction.sol#L429](https://github.com/code-423n4/2026-03-chainlink/blob/main/src/BaseAuction.sol#L429) — `bid()` uses `_getAssetPrice(asset, true)` (reverting)

## Vulnerability Details

### Finding Description and Impact

The auction lifecycle has an asymmetric price validation design between the off-chain eligibility check (`checkUpkeep`) and the on-chain execution (`performUpkeep` / `bid`):

1. **`checkUpkeep()` (L238)** fetches prices with `withValidation = false`. This means it returns stale or zero prices without reverting, using them to determine which assets are eligible for auction and which auctions have ended.

2. **`performUpkeep()` (L315, L342)** fetches prices with `withValidation = true`. If any price is stale at execution time, the function reverts with `Errors.StaleFeedData()`. Crucially, at L315, the `assetOut` (LINK) price is fetched first — if LINK's oracle is stale, the **entire batch** of eligible auctions is blocked, regardless of the freshness of individual asset prices.

3. **`bid()` (L429)** also fetches the asset price with `withValidation = true`. Any transient oracle staleness prevents bidding on otherwise live auctions.

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

## Recommended Mitigation Steps

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

## Proof of Concept

**File**: [`test/poc/M01_OracleStalenessDoS.t.sol`](../2026-03-chainlink/test/poc/M01_OracleStalenessDoS.t.sol)

Extends the `C4PoC` template. Run with:

```bash
forge test --match-contract M01_OracleStalenessDoS -vvv
```

**Test 1: `test_M01_staleAssetOutBlocksAllAuctions`**

Demonstrates that a stale LINK (assetOut) feed blocks all new auctions even when USDC and WETH feeds are fresh:

1. Fund fee aggregator with $100k USDC and $100k WETH
2. `checkUpkeep()` succeeds — returns both assets as eligible
3. Skip past LINK staleness threshold (1 hour + 1 second)
4. Refresh only WETH and USDC prices (LINK remains stale)
5. `performUpkeep()` reverts with `StaleFeedData`
6. Assert: both USDC and WETH remain in fee aggregator (auctions blocked)

**Test 2: `test_stalePriceBlocksBidding`**

Demonstrates that stale price blocks `bid()` on active auctions:

1. Start a USDC auction normally
2. Skip past staleness threshold
3. Attacker (permissionless) tries to bid — reverts with `StaleFeedData`

Both tests pass:
```
Ran 3 tests for test/poc/M01_OracleStalenessDoS.t.sol:M01_OracleStalenessDoS
[PASS] testSubmissionValidity() (gas: 166)
[PASS] test_M01_staleAssetOutBlocksAllAuctions() (gas: 466851)
[PASS] test_stalePriceBlocksBidding() (gas: 520273)
Suite result: ok. 3 passed; 0 failed; 0 skipped
```
