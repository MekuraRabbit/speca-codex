# Chainlink Payment Abstraction V2 — 総合監査レポート

> Code4rena 2026-03 | 監査期間: 2026-03-20 〜 2026-03-27
> 監査チーム: SPECA Pipeline + Human Review (grandchildrice)

---

## 1. Executive Summary

Chainlink Payment Abstraction V2 は、プロトコルが保有するトークン（USDC, WETH）を Dutch Auction 方式で LINK に変換するシステム。CowSwap/GPv2 との統合、Chainlink Data Streams + Data Feed のデュアルオラクル、Chainlink Automation による自動オークション管理を備える。

### 監査結果

| Severity | 件数 | 提出 | 却下 |
|----------|------|------|------|
| **High** | 1 | 1 | 0 |
| **Medium** | 2 | 2 | 0 |
| **Low** | 4 | 4 | 0 |
| **QA** | 4 | 0 | 4 |
| **Info** | 2 | 0 | 2 |
| **Duplicate** | 1 | 0 | 1 |
| **合計** | **14** | **7** | **7** |

### 追加分析

| 分析 | 件数 | 結果 |
|------|------|------|
| 過去コンテスト CSV 検索 | 20,000+ 件 | 14パターンで検索 |
| LLM Bulk Audit | 2,000 件 | 104 applicable, 17 high confidence new |
| Round 2 攻撃面分析 | 12 パターン | 1 新候補（M-15） |
| CowSwap slippage 検証 | 全コード | isValidSignature で settlement 時に検証済み。問題なし |

---

## 2. 提出済み Finding 一覧

### 2.1 [H-01] High — Persistent ERC20 Approvals via Unrestricted _multiCall

**ファイル**: `AuctionBidder.sol` L97-112
**Root Cause**: `auctionCallback()` が `_multiCall(calls)` で任意の外部呼び出しを実行。AUCTION_BIDDER_ROLE（solver bot = operational role）が `approve(attacker, type(uint256).max)` を solution に含めることで、DEFAULT_ADMIN_ROLE の `withdraw()` による資金管理境界を bypass。

**Attack Flow**:
```
1. AUCTION_BIDDER_ROLE が bid() を呼び出し
2. solution に approve(attacker, MAX) を含める
3. auctionCallback() → _multiCall() で approve 実行
4. 後続 tx で attacker が transferFrom で全残高を奪取
```

**Impact**: AuctionBidder 内の全トークン窃取。Trust boundary violation（operational role → admin 権限 bypass）。

**Severity 根拠**: AUCTION_BIDDER_ROLE は trusted role だが、solver bot という operational role であり、信頼度は DEFAULT_ADMIN_ROLE より低い。trust boundary bypass が明確なため High。

**Status**: 提出済み (teoshutuzuumi)

---

### 2.2 [M-03] Medium-High — Single Feed Revert Causes Cross-Asset DoS

**ファイル**: `BaseAuction.sol` `performUpkeep()` L324-357
**Root Cause**: `performUpkeep()` のオークション開始ループ内で `_getAssetPrice(asset, true)` を呼び出すが、try-catch がない。1つのアセットの price feed が revert すると、**全アセット**のオークション開始/終了が停止。

**Attack Flow**:
```
1. USDC の Data Streams feed が一時的にrevert（外部要因）
2. performUpkeep([USDC, WETH]) を呼び出し
3. USDC の _getAssetPrice() が revert → トランザクション全体が revert
4. WETH のオークションも開始/終了不能（cross-asset DoS）
5. 既に開始済みのオークションの endedAuctions 処理も巻き添え
```

**Impact**: Permissionless（`bid()` 経由でも trigger 可能）、system-wide DoS、recovery 困難。

**修正**: `_getAssetPrice()` を try-catch で囲み、失敗したアセットを skip。1行の修正。

**Status**: 提出済み (teoshutuzuumi) — **最有力 Finding**

---

### 2.3 [M-01] Medium — Oracle Staleness Causes Permissionless DoS

**ファイル**: `PriceManager.sol` `_getAssetPrice()` L409-415
**Root Cause**: Data Streams と Data Feed の両方が stale の場合、`_getAssetPrice(asset, true)` が `StaleFeedData` で revert。`bid()` と `performUpkeep()` の両方が停止。

**Impact**: Permissionless DoS（外部要因だが、攻撃者の操作不要で発生可能）。特定アセットの機能停止。

**Status**: 提出済み (teoshutuzuumi)

---

### 2.4 [M-02] Low — Shared Staleness Threshold Undermines Dual-Oracle Fallback

**ファイル**: `PriceManager.sol` L73, L378, L385, L405
**Root Cause**: `FeedInfo.stalenessThreshold` が Data Streams（秒単位更新）と Data Feed（1時間 heartbeat）で共有。tight threshold（5分）→ fallback が常に stale。loose threshold（1時間）→ Data Streams の鮮度保証が失われる。

**Impact**: Dual-oracle の冗長性が設計上無効化。admin config 依存。

**Severity**: Low（設計制限、admin config 依存、直接 fund loss なし）

**過去判決例**: Tapioca #1505 (Medium) が完全一致パターン。ただし trust model の違いから Low に据え置き。

**Status**: 提出済み

---

### 2.5 [M-07] Low — Future-Dated Timestamps Extend Staleness Window

**ファイル**: `PriceManager.sol` L162, L178-179
**Root Cause**: `transmit()` が `report.observationsTimestamp > block.timestamp` を拒否しない。future timestamp が stored → staleness check を bypass → 有効期間が `stalenessThreshold + N` に延長。

**Impact**: Staleness protection の無効化。ただし PRICE_ADMIN_ROLE + VerifierProxy 経由の trusted path。

**Severity**: Low（defense-in-depth 不足。permissionless exploitation path なし）

**Status**: 提出済み

---

### 2.6 [M-14] Low — Stale Approval After _setAuction Migration

**ファイル**: `AuctionBidder.sol` L150-166
**Root Cause**: `_setAuction()` が `s_auction` を上書きする際、旧 auction への ERC20 approval を revoke しない。residual allowance が旧 auction に残存。

**Impact**: 理論上は旧 auction からの token drain。ただし:
- `forceApprove` が毎回上書き → residual ≈ 0
- DEFAULT_ADMIN_ROLE による migration が前提
- 旧 auction が adversarial になる必要あり

**Severity**: Low（residual ≈ 0、admin trust 依存）

**Status**: 提出済み

---

### 2.7 [M-15] Low — Chainlink Circuit Breaker Bounds Not Validated in Fallback

**ファイル**: `PriceManager.sol` L386-392
**Root Cause**: Fallback path で `latestRoundData()` の `answer` に対して minAnswer/maxAnswer の circuit breaker 検証がない。価格が bounds を超えると、clamped 値が返り、オークション価格が実勢と乖離。

**Impact**:
- LINK が minAnswer まで暴落 → bidder が少ない LINK で高額アセットを取得 → protocol loss
- 同パスで `answer <= 0` チェックもなし → negative price で SafeCast revert → DoS

**条件**: Data Streams stale + 極端な市場変動の同時発生が必要。

**過去判決例**: Loopfi #522, Noya #1130, Size #3 等で Medium（15件一致）。ただし本件は fallback path のみ + Chainlink 自社プロトコルのため Low。

**Severity**: Low（二重の外部条件依存、fallback のみ）

**Status**: 新規作成

---

## 3. 却下 Finding 一覧

### 3.1 [C-01] Duplicate — Unrestricted Arbitrary Call in auctionCallback

H-01 と同一 root cause（_multiCall の無制限実行）。H-01 に統合。

### 3.2 [M-04] QA — AUCTION_WORKER_ROLE による performData 操作

AUCTION_WORKER_ROLE は trusted role。fund loss なし。OOS。

### 3.3 [M-05] QA — 非経済的攻撃

攻撃コスト（ガス代）> 攻撃利益。非経済的。

### 3.4 [M-06] QA — bid() の Slippage Protection 不在

AuctionBidder が `getAssetOutAmount()` で exact approve = self-protection 済み。EOA 直接利用は非標準パス。UX issue。

### 3.5 [M-08] Low-Medium（未提出） — Auction Freeze

Impact 盛りすぎ。handcrafted performData で workaround 可能。narrow scope なら提出可能だったが未提出。

### 3.6 [M-09] Info（未提出） — M-07 の弱い亜種

実害立証なし。

### 3.7 [M-10] Low（未提出） — Token Donation による Config Mismatch

Config mismatch / onboarding 運用問題。sustained DoS は言い過ぎ。

### 3.8 [M-11] Info（未提出） — performUpkeep Atomic Batching

M-01/M-03 の言い換え。独立 finding として弱い。

---

## 4. コードベース防御パターン分析

Chainlink V2 が standard attack vector を潰していた防御:

| # | 防御 | 効果 |
|---|------|------|
| 1 | `s_entered` reentrancy guard（グローバル） | bid() + isValidSignature() の全reentrancy を防止 |
| 2 | `assetOutAmount` を callback 前に確定 | callback 中の価格操作不可 |
| 3 | `safeTransferFrom` で atomic 支払い | 中途半端な状態なし |
| 4 | SafeERC20 一貫使用 | return value 問題なし |
| 5 | `AccessControlDefaultAdminRules` | admin 権限の安全な移譲 |
| 6 | `whenNotPaused` 全 critical path | Emergency stop あり |
| 7 | Constructor-based（non-upgradeable） | init frontrun / proxy 脆弱性なし |
| 8 | GPv2 `domainSeparator` + `filledAmount` | EIP-1271 replay 防止 |
| 9 | `_whenNoLiveAuctions()` modifier | ライブ中の設定変更防止 |
| 10 | Oracle decimals 正規化 | 両パス実装済み |
| 11 | `isValidSignature()` settlement 時検証 | CowSwap slippage protection 機能 |
| 12 | `mulDivUp` 一貫使用 | 丸めがプロトコル有利 |

**結論**: 堅牢なコードベースで permissionless な High/Critical が構造的に出にくい。主な attack surface は trusted role boundary bypass（H-01）と外部依存の liveness failure（M-03）。

---

## 5. 過去コンテスト事例分析

### 5.1 CSV 検索（Phase 1 + Phase 2）

| 検索 | 対象 | ヒット数 | 結果 |
|------|------|---------|------|
| M-02 類似（shared staleness） | 3プラットフォーム | 2,422 | Tapioca #1505 が完全一致（Medium） |
| M-07 類似（future timestamp） | 3プラットフォーム | 8,162 | oracle validation 系は High が多いが trusted path |
| M-14 類似（stale approval） | 3プラットフォーム | 13,709 | Centrifuge #309 が完全一致（High）だが trust model が異なる |

### 5.2 拡張パターン検索（14パターン）

| パターン | ヒット数 | Chainlink V2 該当 |
|---------|---------|-----------------|
| dutch_auction_rounding | 24 | なし（mulDivUp がプロトコル有利） |
| auction_timing_griefing | 841 | なし（±15秒は無視可能） |
| auction_settlement_reentrancy | 445 | なし（s_entered がグローバル） |
| fee_on_transfer | 894 | なし（USDC/WETH/LINK は標準 ERC20） |
| token_donation_inflation | 997 | なし（残余は FeeAggregator に戻る） |
| oracle_decimal_mismatch | 2,417 | なし（decimal 正規化済み） |
| eip1271_reentrancy | 96 | なし（s_entered + view 関数） |
| order_replay | 690 | なし（GPv2 filledAmount 防止） |
| pause_bypass | 346 | なし（全 critical path に whenNotPaused） |
| performupkeep_manipulation | 235 | なし（AUCTION_WORKER trusted） |
| oracle_staleness_fallback | 2,422 | **M-15 発見**（circuit breaker 未チェック） |
| cowswap_gpv2 | 2 | なし（settlement 時検証済み） |

### 5.3 Bulk LLM Audit（2,000件 × 16並列）

| 項目 | 値 |
|------|---|
| 処理件数 | 2,000 |
| 処理時間 | 392秒（6.5分） |
| Applicable | 104 |
| High confidence NEW | 17 |
| **実コード検証で確認** | **M-15（circuit breaker）のみ有効** |

High confidence 17件の内訳:
- oracle_staleness_fallback: 15件 → **M-15 として提出**
- auction_timing_griefing: 1件 → ±15秒は無視可能、QA
- performupkeep_manipulation: 1件 → trusted role、QA

### 5.4 Round 2 攻撃面分析（12パターン）

| パターン | 結果 |
|---------|------|
| fee-on-transfer balance | 該当なし（標準 ERC20） |
| negative oracle price DoS | M-15 に統合（defense-in-depth） |
| Dutch auction frontrun | 該当なし（±15秒無視可能） |
| checkUpkeep/performUpkeep mismatch | 該当なし（re-validate 済み） |
| rounding/precision mulDiv | 該当なし（mulDivUp プロトコル有利） |
| full balance approval to relayer | 該当なし（OOS、vaultRelayer trusted） |
| feeAggregator pull failure | タイムアウト（未完了） |
| delete mapping state leak | M-14 に包含済み |
| auction dust griefing | 該当なし（minBidUsdValue 防止） |
| safeTransfer before state update | 該当なし（s_entered 防止） |
| ERC20 decimal mismatch | 該当なし（正規化済み） |
| EnumerableSet gas DoS | 該当なし（アセット数は admin 管理） |

---

## 6. 提出 Finding の最終ステータス

| ID | Severity | Title | Status |
|----|----------|-------|--------|
| **H-01** | High | Unrestricted _multiCall trust boundary bypass | 提出済み ✅ |
| **M-03** | Medium-High | Cross-asset DoS via single feed revert | 提出済み ✅ |
| **M-01** | Medium | Oracle staleness permissionless DoS | 提出済み ✅ |
| **M-02** | Low | Shared staleness threshold | 提出済み ✅ |
| **M-07** | Low | Future timestamp extends staleness | 提出済み ✅ |
| **M-14** | Low | Stale approval after migration | 提出済み ✅ |
| **M-15** | Low | Circuit breaker bounds not validated | 新規 📝 |

---

## 7. 推定報奨金

| Severity | 件数 | C4 標準レンジ | 推定 |
|----------|------|--------------|------|
| High | 1 | $3,000-15,000 | ~$5,000-10,000 |
| Medium | 2 | $500-3,000 each | ~$1,000-6,000 |
| Low | 4 | $100-500 each | ~$400-2,000 |
| **合計** | **7** | — | **~$6,400-18,000** |

※ pot size、参加者数、duplicate 数により大幅に変動。

---

*Generated by SPECA Pipeline + Claude Code*
*2026-03-27*
