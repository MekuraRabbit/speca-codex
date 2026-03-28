# Reverse Match Analysis: Past Audit Patterns vs. Chainlink Payment Abstraction V2

> Generated: 2026-03-26
> Source: `outputs/similar_audit_matches.json` (51 high-relevance matches from 125 total)
> Target: `2026-03-chainlink/src/` (6 in-scope contracts, 1,060 nSLOC)
> Objective: Find NEW vulnerabilities beyond existing M-01 through M-14, C-01, H-01

---

## 1. Match Categorization

The 51 high-relevance matches were categorized into the following pattern types:

| Category | Count | Key Sources |
|---|---|---|
| **Residual/stale approval after state change** | 14 | Fractional #468, artgobblers #238, traderjoe #222, astaria #484, caviar #976 |
| **Arbitrary call/execute abuse** | 18 | caviar #801/#709/#707/#673/#218/#186/#63/#230, rubicon #292/#138, axelar #429/#390, tapioca #1391/#927 |
| **Privilege escalation via role boundary bypass** | 8 | blur #629/#618/#487/#374/#217, dopex #680, escher #426/#441 |
| **Oracle manipulation/staleness** | 2 | reserve #76, reserve #259 |
| **Reentrancy via callback** | 3 | reserve #154, ens #14, astaria #166 |
| **Dutch auction price manipulation** | 4 | escher #94/#457/#225/#198 |
| **Fee/accounting errors** | 2 | backed #110, prepo #125 |

---

## 2. Pattern-by-Pattern Analysis

### 2a. Residual/Stale Approval Pattern

**Locations searched:**
- `GPV2CompatibleAuction._onAuctionStart()` (L86-93): `forceApprove(i_gpV2VaultRelayer, balance)`
- `GPV2CompatibleAuction._onAuctionEnd()` (L96-104): `forceApprove(i_gpV2VaultRelayer, 0)`
- `AuctionBidder.bid()` (L78): `forceApprove(address(auction), getAssetOutAmount(...))`
- `AuctionBidder.auctionCallback()` (L111): `forceApprove(msg.sender, amountOut)`
- `AuctionBidder._setAuction()` (L150-166): overwrites `s_auction`
- `FeeAggregator.bridgeAssets()` (L247): `safeIncreaseAllowance(i_ccipRouter, fees)`
- `FeeAggregator._buildBridgeAssetsMessage()` (L272): `safeIncreaseAllowance(i_ccipRouter, amount)`

**Findings:**

1. **GPV2CompatibleAuction approval lifecycle -- PROPERLY HANDLED.**
   - `_onAuctionStart` sets approval to current balance.
   - `_onAuctionEnd` revokes to 0.
   - The vault relayer is immutable (`i_gpV2VaultRelayer`), so no migration risk.
   - If auction ends with partial fill, the revocation at `_onAuctionEnd` properly cleans up.
   - **No new vulnerability.**

2. **AuctionBidder stale approval on auction migration -- ALREADY COVERED by M-14.**
   - `_setAuction()` does not revoke approvals to the old auction.
   - M-14 already identifies this exact pattern.
   - **Overlaps with existing M-14.**

3. **FeeAggregator `safeIncreaseAllowance` residual -- OUT OF SCOPE.**
   - `FeeAggregator.sol` is explicitly out of scope per `BUG_BOUNTY_SCOPE.json`.
   - Even so: `safeIncreaseAllowance` is used for CCIP router (immutable), so no migration risk.
   - **Not applicable (OOS).**

4. **GPV2CompatibleAuction: approval amount set to `balanceOf(this)` at auction start, but additional tokens deposited during auction increase balance without increasing approval.**
   - At `_onAuctionStart`, approval = `balanceOf(address(this))` at that moment.
   - If tokens are donated/sent to the contract during the auction, CowSwap vault relayer cannot pull the excess (approval is insufficient).
   - However, this is a known limitation documented in `publicly_known_issues`: "Arbitrary deposits during live auctions."
   - The direct `bid()` path works fine since it uses `safeTransfer` directly.
   - **Already a known issue. No new vulnerability.**

### 2b. Arbitrary Call/Execute Abuse Pattern

**Locations searched:**
- `Caller._call()` (L21-44): raw `.call(target, data)` with no restriction
- `Caller._multiCall()` (L49-63): loops `_call` for each entry
- `AuctionBidder.auctionCallback()` (L107-109): decodes `data` -> `_multiCall(calls)`
- `WorkflowRouter.onReport()` (L86-118): decodes report -> `_call(target, data)`

**Findings:**

1. **AuctionBidder._multiCall -- ALREADY COVERED by C-01 and H-01.**
   - Both existing submissions cover the unrestricted `_multiCall` in `auctionCallback`.
   - C-01 focuses on single-tx drain via `transfer`, H-01 on persistent approval escalation.
   - **Overlaps with existing C-01/H-01.**

2. **WorkflowRouter.onReport() uses `_call(target, data)` -- ANALYZED.**
   - `onReport` is gated by `FORWARDER_ROLE` (trusted per scope).
   - Has a triple-layered allowlist: workflow ID -> target -> selector.
   - The target must be in `s_workflowInfos[workflowId].allowlistedTargets`.
   - The selector must be in `s_workflowInfos[workflowId].allowlistedSelectors[target]`.
   - Admin (`DEFAULT_ADMIN_ROLE`) configures the allowlists.
   - **Key question**: Can the `_call` be exploited even with allowlists?
     - The `_call` executes as the `WorkflowRouter` contract (msg.sender = WorkflowRouter).
     - If the admin allowlists a target+selector combination that is dangerous (e.g., `token.approve()`), then `FORWARDER_ROLE` could abuse it.
     - However, `FORWARDER_ROLE` is TRUSTED per scope, and admin configuration is TRUSTED.
     - The allowlist design does prevent arbitrary calls from the forwarder.
   - **Potential issue**: The selector check uses `bytes4` extracted via assembly. If the `data` is shorter than 4 bytes, the assembly at L106-108 reads uninitialized memory. However, if `data.length < 4`, the `mload(add(data, 32))` will still read 32 bytes starting at the data pointer, and the `bytes4` mask would pick up whatever is there. But the selector check against the EnumerableSet would fail for garbage selectors, so this is not exploitable.
   - **No new vulnerability (FORWARDER_ROLE is trusted; allowlist is enforced).**

3. **WorkflowRouter: Can onReport re-enter BaseAuction?**
   - If admin allowlists `BaseAuction.performUpkeep` selector on BaseAuction target, the forwarder could trigger it.
   - But the forwarder is trusted per scope, and `performUpkeep` has its own `AUCTION_WORKER_ROLE` gate -- wait, let me re-check.
   - `performUpkeep` is gated by `onlyRole(Roles.AUCTION_WORKER_ROLE)`. When called via `WorkflowRouter._call()`, `msg.sender` would be `WorkflowRouter`, not the original forwarder. So `WorkflowRouter` would need `AUCTION_WORKER_ROLE` on the BaseAuction.
   - This is an admin configuration concern, not a code vulnerability.
   - **No new vulnerability.**

### 2c. Privilege Escalation via Role Boundary Bypass

**All role-gated functions mapped:**

| Contract | Function | Role | Trust Level |
|---|---|---|---|
| WorkflowRouter | onReport | FORWARDER_ROLE | TRUSTED |
| WorkflowRouter | applyAllowlisted*Updates | DEFAULT_ADMIN_ROLE | TRUSTED |
| BaseAuction | performUpkeep | AUCTION_WORKER_ROLE | TRUSTED |
| BaseAuction | setMinBidUsdValue | ASSET_ADMIN_ROLE | TRUSTED |
| BaseAuction | setAssetOut | ASSET_ADMIN_ROLE | TRUSTED |
| BaseAuction | setAssetOutReceiver | DEFAULT_ADMIN_ROLE | TRUSTED |
| BaseAuction | setFeeAggregator | DEFAULT_ADMIN_ROLE | TRUSTED |
| BaseAuction | applyAssetParamsUpdates | ASSET_ADMIN_ROLE | TRUSTED |
| BaseAuction | bid | (permissionless) | UNTRUSTED |
| PriceManager | transmit | PRICE_ADMIN_ROLE | SEMI_TRUSTED |
| PriceManager | applyFeedInfoUpdates | ASSET_ADMIN_ROLE | TRUSTED |
| AuctionBidder | bid | AUCTION_BIDDER_ROLE | (see below) |
| AuctionBidder | auctionCallback | auction contract only | N/A |
| AuctionBidder | withdraw | DEFAULT_ADMIN_ROLE | TRUSTED |
| AuctionBidder | setAuction | DEFAULT_ADMIN_ROLE | TRUSTED |
| AuctionBidder | setReceiver | DEFAULT_ADMIN_ROLE | TRUSTED |
| GPV2CompatibleAuction | isValidSignature | (permissionless view) | UNTRUSTED |
| GPV2CompatibleAuction | invalidateOrders | ORDER_MANAGER_ROLE | TRUSTED |

**Findings:**

1. **AUCTION_BIDDER_ROLE -> DEFAULT_ADMIN_ROLE escalation -- ALREADY COVERED by C-01/H-01.**
   - The `_multiCall` in `auctionCallback` allows AUCTION_BIDDER_ROLE to bypass `withdraw()` which requires DEFAULT_ADMIN_ROLE.
   - **Overlaps with existing findings.**

2. **ASSET_ADMIN_ROLE can manipulate auction parameters during non-live auctions.**
   - Can set `endingPriceMultiplier` close to 0 (bounded by `i_minPriceMultiplier`), making auctions very cheap.
   - But ASSET_ADMIN is TRUSTED per scope.
   - **Not in scope (trusted role).**

3. **PRICE_ADMIN_ROLE can submit manipulated prices.**
   - Reports are verified by `i_streamsVerifierProxy.verifyBulk()` -- external verifier.
   - Oracle verification is out of scope per `BUG_BOUNTY_SCOPE.json`.
   - Staleness issues are already covered by M-01/M-02/M-07.
   - **No new vulnerability.**

4. **Permissionless `bid()` on BaseAuction -- any address can call.**
   - The callback mechanism (`IAuctionCallback`) is called on `msg.sender`.
   - `s_entered` flag prevents reentrancy back into `bid()` and `isValidSignature()`.
   - After callback, `safeTransferFrom` pulls assetOut from caller.
   - The bidder gets assetIn first (flash loan style), then pays assetOut.
   - **Could a malicious bidder exploit the callback?**
     - During callback, `s_entered = true`, so no re-entry to bid/isValidSignature.
     - The bidder could interact with other protocols but cannot re-enter the auction.
     - State changes in BaseAuction are: `safeTransfer(asset -> bidder)` happens BEFORE callback, and `safeTransferFrom(assetOut <- bidder)` happens AFTER.
     - If the bidder reverts in the callback, the entire bid reverts (no harm).
     - If the bidder succeeds but doesn't approve enough assetOut, the `safeTransferFrom` reverts.
   - **No new vulnerability. Reentrancy protection is effective.**

### 2d. Oracle Staleness / Manipulation

**Locations searched:**
- `PriceManager._getAssetPrice()` (L372-419)
- `PriceManager.transmit()` (L133-183)
- `BaseAuction.bid()` L429: `_getAssetPrice(asset, true)`
- `BaseAuction.checkUpkeep()` L238: `_getAssetPrice(asset, false)`
- `BaseAuction.performUpkeep()` L315: `_getAssetPrice(assetOut, true)`
- `GPV2CompatibleAuction.isValidSignature()` L153: `_getAssetPrice(sellToken, true)`

**Findings:**

1. **`latestRoundData()` without try-catch -- ALREADY COVERED by M-03.**
   - `_getAssetPrice()` L386 calls `feedInfo.usdDataFeed.latestRoundData()` without try-catch.
   - A reverting data feed blocks all price queries for that asset.
   - **Overlaps with M-03.**

2. **Shared staleness threshold -- ALREADY COVERED by M-02.**
   - Single `stalenessThreshold` used for both Data Streams and Data Feed.
   - **Overlaps with M-02.**

3. **Future timestamp in transmit -- ALREADY COVERED by M-07.**
   - `transmit()` checks `observationsTimestamp < block.timestamp - stalenessThreshold` but doesn't reject future timestamps.
   - **Overlaps with M-07.**

4. **Data Feed `answer` can be negative -> `toUint256()` reverts.**
   - `_getAssetPrice()` L392: `price = answer.toUint256()` -- if `answer < 0`, SafeCast reverts.
   - This is actually a safety feature (price=0 check would miss negative values).
   - But a negative answer from a data feed would cause `_getAssetPrice` with `withValidation=true` to revert, which could block bids.
   - This is similar to M-03 (external revert blocks operations). Could be considered a sub-finding of M-03.
   - **Partially overlaps with M-03 (negative answer = revert). Not a distinct finding.**

5. **Price checked at `bid()` time but not at `performUpkeep` end time -- ALREADY COVERED by M-04.**
   - **Overlaps with M-04.**

6. **`_getAssetPrice` fallback: Data Feed `decimals()` external call without try-catch.**
   - At L394: `uint8 decimals = feedInfo.usdDataFeed.decimals()` -- if this reverts, entire price query fails.
   - This is a sub-case of M-03 (reverting external call blocks all operations).
   - **Partially overlaps with M-03.**

7. **NEW POTENTIAL FINDING: `_getAssetPrice` Data Feed fallback uses `answer.toUint256()` BEFORE checking if Data Feed price is more recent.**
   - At L386-401: `latestRoundData()` is called, `answer.toUint256()` is computed.
   - The `toUint256()` conversion happens unconditionally at L392.
   - If `answer` is negative (compromised feed), it reverts even if the Data Streams price is more recent and would be used instead.
   - Wait, actually L392 only executes inside the `if (updatedAt < dataFeedUpdatedAt)` block at L390. So it only converts if the data feed is actually more recent. Let me re-read...
   - Re-reading L385-401:
     ```
     if (updatedAt < minTimestamp && feedInfo.usdDataFeed != address(0)) {
       (, int256 answer,, uint256 dataFeedUpdatedAt,) = feedInfo.usdDataFeed.latestRoundData();
       if (updatedAt < dataFeedUpdatedAt) {
         updatedAt = dataFeedUpdatedAt;
         price = answer.toUint256();
         ...
       }
     }
     ```
   - The `latestRoundData()` call at L386 happens whenever Data Streams price is stale AND a Data Feed is configured. Even if the Data Feed's `updatedAt` is older than the stale Data Streams price, the `latestRoundData()` call itself could revert.
   - This IS the M-03 finding (reverting data feed blocks all operations when data streams is stale).
   - **Overlaps with M-03.**

### 2e. Reentrancy via Callback

**Locations searched:**
- `BaseAuction.bid()` (L410-458): external calls at L444 (`safeTransfer`), L449 (`auctionCallback`), L453 (`safeTransferFrom`)
- `GPV2CompatibleAuction.isValidSignature()` (L119-176): view function, no state changes
- `BaseAuction.performUpkeep()` (L305-370): external calls to `s_feeAggregator.transferForSwap()`, `_onAuctionStart()`
- `AuctionBidder.auctionCallback()` (L97-112): `_multiCall` with external calls

**Findings:**

1. **`bid()` reentrancy protection via `s_entered` -- EFFECTIVE.**
   - L415-418: `s_entered = true` before any external calls.
   - L457: `s_entered = false` after all operations.
   - `isValidSignature()` also checks `s_entered` at L125.
   - **No new vulnerability.**

2. **`performUpkeep` reentrancy path:**
   - L321: `s_feeAggregator.transferForSwap(address(this), eligibleAssets)` -- external call to FeeAggregator.
   - If FeeAggregator is malicious or compromised, it could re-enter `performUpkeep`.
   - But `performUpkeep` is gated by `AUCTION_WORKER_ROLE`, so re-entry from FeeAggregator would fail unless FeeAggregator has that role.
   - `s_feeAggregator` is set by DEFAULT_ADMIN (trusted).
   - **No new vulnerability (trusted admin sets feeAggregator).**

3. **`bid()` callback -> state change ordering:**
   - L444: `safeTransfer(asset -> bidder)` -- sends assetIn to bidder
   - L449: `auctionCallback(...)` -- bidder executes arbitrary logic
   - L453: `safeTransferFrom(assetOut <- bidder)` -- pulls assetOut from bidder
   - L457: `s_entered = false`
   - State that could be exploited during callback:
     - `s_auctionStarts` is NOT modified during `bid()` (only in `performUpkeep`)
     - No balance state is tracked in storage; balances are checked via `balanceOf`
     - The `s_entered` flag prevents re-entry to `bid()` and `isValidSignature()`
   - **Could callback interact with `performUpkeep`?**
     - `performUpkeep` requires `AUCTION_WORKER_ROLE` -- the bidder doesn't have this.
     - Even if they could call it via another path, `performUpkeep` would see the reduced balance (asset was transferred to bidder at L444) and might end the auction early (if balance < minAuctionSize).
     - But again, role-gated, so not reachable from callback.
   - **No new vulnerability.**

4. **`_onAuctionEnd` revert -> auction freeze -- ALREADY COVERED by M-08.**
   - **Overlaps with M-08.**

### 2f. Dutch Auction Price Curve Manipulation

**Locations searched:**
- `BaseAuction._getAssetOutAmount()` (L777-803): linear price decay calculation
- `BaseAuction.AssetParams` struct: `startingPriceMultiplier`, `endingPriceMultiplier`, `auctionDuration`

**Findings:**

1. **Price calculation analysis:**
   ```solidity
   uint256 priceMultiplier = startingPriceMultiplier
     - (startingPriceMultiplier - endingPriceMultiplier).mulDiv(elapsedTime, auctionDuration);

   uint256 auctionUsdValue = amountIn.mulDivUp(assetInUsdPrice, 10**decimals).mulWadUp(priceMultiplier);
   uint256 assetOutAmount = auctionUsdValue.mulDivUp(10**assetOutDecimals, assetOutUsdPrice);
   ```
   - Uses Solady `mulDiv` (512-bit intermediate) for the multiplier decay.
   - Uses `mulDivUp` for USD value and asset out amount (rounds UP = protocol-favorable).
   - `elapsedTime` is bounded to `auctionDuration` at L785.
   - Solidity 0.8 checked arithmetic prevents underflow.
   - **No overflow/underflow risk.**

2. **L2 sequencer downtime -> price skip -- ALREADY COVERED by M-13.**
   - **Overlaps with M-13.**

3. **NEW POTENTIAL FINDING: `startingPriceMultiplier == endingPriceMultiplier` edge case.**
   - If both are equal, the `mulDiv` term is 0, so `priceMultiplier = startingPriceMultiplier` throughout.
   - This is a flat-price auction, which is valid behavior, not a vulnerability.
   - **Not a vulnerability.**

4. **Rounding in price calculation:**
   - `mulDivUp` rounds in favor of the protocol (bidder pays more assetOut).
   - This is correct and intentional per the audit state file.
   - **No new vulnerability.**

5. **`block.timestamp` manipulation by miners (1-2 seconds).**
   - Could shift `elapsedTime` slightly, affecting `priceMultiplier`.
   - Impact is negligible (linear decay, 1-2 seconds out of potentially hours).
   - **Not a practical vulnerability.**

### 2g. Fee/Accounting Errors

**Locations searched:**
- `BaseAuction._onAuctionEnd()` (L383-397): balance transfers
- `BaseAuction.performUpkeep()` (L318-370): fee aggregator interactions
- `BaseAuction.bid()` (L437-453): balance check and transfer
- `GPV2CompatibleAuction.isValidSignature()` (L144): `sellAmount > balanceOf`

**Findings:**

1. **`_onAuctionEnd` transfers ALL assetOut balance to receiver, not just from this auction.**
   - L393-396: `uint256 assetOutBalance = IERC20(s_assetOut).balanceOf(address(this)); safeTransfer(s_assetOutReceiver, assetOutBalance);`
   - If multiple auctions end simultaneously, the first `_onAuctionEnd` call transfers ALL accumulated assetOut (from all auctions).
   - Subsequent `_onAuctionEnd` calls would have 0 assetOut to transfer.
   - This is not a loss of funds (the receiver gets everything), just a batching behavior.
   - **Not a vulnerability (funds reach correct destination).**

2. **`performUpkeep` checks `eligibleAssets[i].amount` (from `checkUpkeep`) but the actual FeeAggregator balance might have changed.**
   - Between `checkUpkeep` and `performUpkeep`, the FeeAggregator balance could change.
   - `transferForSwap` transfers the requested amount; if balance is insufficient, the transfer reverts.
   - This is a known issue (stale performData) covered by M-04's family.
   - **Not a new distinct vulnerability.**

3. **NEW POTENTIAL FINDING: `bid()` balance check at L437 uses `balanceOf(address(this))` which includes any tokens beyond the auctioned amount.**
   - If someone sends additional tokens of the auctioned asset to the auction contract during a live auction, those tokens become available for bidding.
   - This is documented in `publicly_known_issues`: "Arbitrary deposits during live auctions: balance-based amount detection means extra deposits are only available to bid() callers, not CowSwap solvers."
   - **Already a known issue.**

4. **`GPV2CompatibleAuction._onAuctionStart` approves exactly `balanceOf(this)` to vault relayer.**
   - If extra tokens arrive after auction start, CowSwap solver can't sell them (insufficient approval).
   - Direct `bid()` callers can bid on the extra balance (they use `safeTransfer`, not vault relayer approval).
   - This creates asymmetry between CowSwap and direct bidders.
   - **Already documented in known issues (arbitrary deposits).**

5. **No cross-auction accounting isolation.**
   - The contract uses `balanceOf(address(this))` for each asset, meaning all tokens of the same type are pooled.
   - If two auctions were possible for the same asset (prevented by `s_auctionStarts[asset] != 0` check), double-counting would occur.
   - Since the contract prevents concurrent auctions for the same asset, this is safe.
   - **Not a vulnerability (design prevents the issue).**

---

## 3. Summary of New Potential Vulnerabilities

After thorough analysis of all 51 high-relevance match patterns against the 6 in-scope contracts:

| # | Pattern Category | Code Location | Finding | New? | Severity | Status |
|---|---|---|---|---|---|---|
| 1 | Residual approval | AuctionBidder._setAuction L150 | Stale approval on migration | No | Medium | Overlaps M-14 |
| 2 | Arbitrary call | AuctionBidder.auctionCallback L107 | Unrestricted _multiCall | No | Critical/High | Overlaps C-01/H-01 |
| 3 | Arbitrary call | WorkflowRouter.onReport L117 | _call with allowlist | No | N/A | FORWARDER trusted; triple allowlist |
| 4 | Oracle staleness | PriceManager._getAssetPrice L386 | latestRoundData no try-catch | No | Medium | Overlaps M-03 |
| 5 | Oracle staleness | PriceManager._getAssetPrice L378 | Shared staleness threshold | No | Medium | Overlaps M-02 |
| 6 | Oracle staleness | PriceManager.transmit L162 | Future timestamp accepted | No | Medium | Overlaps M-07 |
| 7 | Reentrancy | BaseAuction.bid L449 | Callback before payment | No | N/A | s_entered guard effective |
| 8 | Dutch auction | BaseAuction._getAssetOutAmount | Price curve manipulation | No | N/A | mulDiv/mulDivUp safe |
| 9 | Dutch auction | BaseAuction.bid | L2 sequencer skip | No | Medium | Overlaps M-13 |
| 10 | Fee/accounting | BaseAuction._onAuctionEnd L393 | All assetOut swept on end | No | N/A | Funds reach correct destination |

### Conclusion

**No new HIGH or MEDIUM vulnerabilities were found** beyond the existing M-01 through M-14, C-01, and H-01 findings.

The 51 high-relevance audit matches from past contests all converge on patterns that are either:
1. **Already covered** by existing findings (primarily the `_multiCall` arbitrary call pattern in C-01/H-01/M-14, and oracle patterns in M-01/M-02/M-03/M-07)
2. **Mitigated by design** (`s_entered` reentrancy guard, `forceApprove` + revocation lifecycle, role-gated functions, Solady 512-bit math)
3. **Out of scope** per trust model (admin/forwarder roles are trusted, FeeAggregator is OOS, oracle verification delegated to external verifier)
4. **Documented as known issues** (arbitrary deposits, non-canonical ERC20s)

### Why the Protocol is Resilient to These Patterns

1. **`s_entered` boolean** protects both `bid()` and `isValidSignature()` against reentrancy through callbacks
2. **All state-changing admin functions** are role-gated with OpenZeppelin `AccessControlDefaultAdminRules`
3. **GPV2CompatibleAuction** properly manages the approval lifecycle: grant on start, revoke on end
4. **WorkflowRouter** enforces a triple allowlist (workflowId -> target -> selector) for `_call`
5. **Solady `mulDivUp`** with 512-bit intermediate prevents overflow in price calculations
6. **Dutch auction instant atomic settlement** prevents commit-reveal or batch manipulation patterns
7. **Solidity 0.8 checked arithmetic** prevents underflow/overflow in price multiplier decay

### Patterns That Could Still Be Relevant (Low/Informational)

- **`_getAssetPrice` Data Feed `decimals()` call without try-catch**: If an external data feed's `decimals()` function reverts, it blocks the fallback price path. This is a sub-case of M-03.
- **Assembly selector extraction in WorkflowRouter L106-108**: If `data.length < 4`, reads uninitialized memory for selector. However, the subsequent allowlist check would reject any garbage selector, making this unexploitable.

---

## 4. Methodology Notes

- All 6 in-scope Solidity files were read in full
- All approval/call/role/oracle/balance patterns were searched via grep
- Each of the 51 high-relevance matches was mapped to its pattern category
- The trust model from `BUG_BOUNTY_SCOPE.json` was applied to filter trusted-role findings
- Cross-referenced against all existing findings (M-01 through M-14, C-01, H-01) from `CHAINLINK_V2_AUDIT_STATE.md`
- Publicly known issues list was consulted to avoid rediscovery
