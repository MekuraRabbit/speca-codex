# Chainlink Payment Abstraction V2 — 監査状態ファイル

> **目的**: AIがこのファイルを読んで、途中から監査を続行できるようにする。
> コンテキストが切れた場合はこのファイルを最初に読め。
> 最終更新: 2026-03-24

---

## 1. コンテスト情報

| 項目 | 値 |
|---|---|
| プラットフォーム | Code4rena |
| 名前 | Chainlink Payment Abstraction V2 |
| 賞金 | $65,000 USDC (HM: up to $57,600) |
| 期間 | 2026-03-18 20:00 UTC → 2026-03-27 20:00 UTC |
| ターゲットリポ | `code-423n4/2026-03-chainlink` (commit `5317782`) |
| ローカルパス | `2026-03-chainlink/` |
| nSLOC | 1,060 |
| V12 (Zellic AI) | OOS — https://v12.sh/runs/1378/public |
| Audit Catalyst | `2026-03-chainlink/catalyst.md` — 重要ヒント3点: asset custody, economic correctness, callback risks |

## 2. スコープ内コントラクト

| ファイル | nSLOC | 役割 |
|---|---|---|
| `BaseAuction.sol` | 420 | コアDutchオークション（線形価格減衰） |
| `PriceManager.sol` | 227 | Data Streams + Chainlink Data Feed 二重オラクル |
| `GPV2CompatibleAuction.sol` | 104 | CowSwap GPv2統合（EIP-1271） |
| `AuctionBidder.sol` | 103 | ソルバーヘルパー（任意callback実行） |
| `WorkflowRouter.sol` | 125 | 自動化イングレス（selector allowlist） |
| `Caller.sol` | 33 | low-level call utility |
| `interfaces/*` | 18 | IAuctionCallback, IBaseAuction, IGPV2*, IPriceManager |
| `libraries/*` | 30 | Errors.sol, Roles.sol |

## 3. 信頼モデル

| アクター | 信頼レベル | スコープ |
|---|---|---|
| DEFAULT_ADMIN / ASSET_ADMIN / PRICE_ADMIN | TRUSTED | OOS |
| AUCTION_WORKER (automation) | TRUSTED | OOS (ただしperformDataの検証不足はM-04) |
| FORWARDER (automation) | TRUSTED | OOS |
| **Bidders (permissionless)** | **UNTRUSTED** | **IN SCOPE** |
| **CowSwap solvers** | **UNTRUSTED** | **IN SCOPE** |
| Price feeds (Data Streams) | SEMI_TRUSTED | staleness/manipulation within PriceManager is in scope |

## 4. 発見事項一覧

### 提出済み

| ID | タイトル | 重要度 | PoC | Submission | C4提出 |
|---|---|---|---|---|---|
| **M-01** | checkUpkeep/performUpkeep 価格検証不整合 (Oracle Staleness DoS) | Medium | `test/poc/M01_*.t.sol` | `outputs/submitted/teoshutuzuumi/M01_submission.md` | **提出済み 2026-03-22** |

### 提出待ち（submission + PoC完成済み、提出予定）

| ID | タイトル | 重要度 | PoC | Submission | パターンカテゴリ |
|---|---|---|---|---|---|
| **M-03** | revertするChainlink Data Feedが全操作をブロック (try-catch無し) | Medium-High | `test/poc/M03_*.t.sol` | `outputs/submitted/M03_submission.md` | external_revert_blocks |

### 未提出（submission + PoC完成済み、提出検討中）

| ID | タイトル | 重要度 | PoC | Submission | パターンカテゴリ |
|---|---|---|---|---|---|
| **M-02** | 共有stalenessThresholdでデュアルオラクル無効化 | Medium | `test/poc/M02_*.t.sol` | `outputs/submitted/M02_submission.md` | shared_oracle_config |
| **M-04** | performUpkeepがオークション終了条件を再検証しない | Medium | `test/poc/M04_*.t.sol` | `outputs/submitted/M04_submission.md` | missing_validation |
| **M-06** | bid()にslippage保護なし (no maxAssetOutAmount) | Medium | `test/poc/M06_*.t.sol` | `outputs/submitted/M06_submission.md` | missing_slippage |
| **M-07** | transmit()が未来タイムスタンプを受け入れ有効期間を延長 | Medium | `test/poc/M07_*.t.sol` | `outputs/submitted/M07_submission.md` | timestamp_validation |

### 新発見（AI深層監査 2026-03-24）

| ID | タイトル | 重要度 | PoC | Issue | パターンカテゴリ |
|---|---|---|---|---|---|
| **M-08** | _onAuctionEnd revert → 永続auction freeze（回復関数なし） | Medium | `test/poc/M08_*.t.sol` (3 tests PASS) | [#163](https://github.com/NyxFoundation/security-agent/issues/163) | stuck_auction / no_recovery |
| **M-09** | transmit()がvalidFromTimestampを検証しない（premature price） | Low-Medium | `test/poc/M09_*.t.sol` (1 test PASS) | [#164](https://github.com/NyxFoundation/security-agent/issues/164) | timestamp_validation |
| **M-10** | FeeAggregator/BaseAuction allowlist不整合 → token donation DoS | Medium | `test/poc/M10_*.t.sol` (1 test PASS) | [#165](https://github.com/NyxFoundation/security-agent/issues/165) | allowlist_mismatch / batch_dos |
| **M-11** | performUpkeep atomic batching → stale price blocks all auction endings | Medium | `test/poc/M11_*.t.sol` (1 test PASS) | [#166](https://github.com/NyxFoundation/security-agent/issues/166) | atomic_batch / cross_contamination |
| **M-12** | checkUpkeep gas limit超過（~80 assets で 5M gas超え → Automation停止） | Medium | — | [#167](https://github.com/NyxFoundation/security-agent/issues/167) | gas_dos / unbounded_loop |
| **M-13** | L2 sequencer downtime → Dutch auction価格decay skip → 最大discount即売 | Medium | — | [#168](https://github.com/NyxFoundation/security-agent/issues/168) | l2_sequencer / price_manipulation |

### QA/Info降格

| ID | タイトル | 元重要度 | 降格理由 |
|---|---|---|---|
| **M-05** | isValidSignatureがminBidUsdValueをバイパス | Medium → QA | 攻撃者がオークション現在価格以上を支払う必要があり、micro-fillの経済的インセンティブなし。ガス代 > 利益 |

### 検討済み＆却下

| パターン | 理由 |
|---|---|
| donation_attack (balanceOf膨張) | 公式 publicly_known_issues に記載済み |
| erc777_reentrancy | non-canonical ERC20は明示的にOOS |
| callback_reentrancy (bid callback) | `s_entered` ガードが有効。performUpkeepはロール制限 |
| eip1271_bypass | GPv2Order.hash()でハッシュ検証済み。replay不可 |
| arithmetic_underflow | Solidity 0.8 checked arithmetic + solady mulDiv |
| force_send (selfdestruct) | ERC20オークション。ETH受信関数なし |
| approval_race | forceApproveで緩和済み |
| balance_manipulation | 公式known issueの範囲内 |
| cascading_failure | 各オークションは独立（asset別） |
| multicall_abuse | AuctionBidder.auctionCallbackはロール+s_entered保護 |
| price_curve precision | mulDiv/mulDivUpで512bit中間演算。誤差<1wei |
| missing_deadline (bid) | Dutch auctionでは時間経過=価格減衰=bidder有利。deadline不要の設計判断 |

## 5. パイプライン実行状態

SPECAパイプライン（全6フェーズ）は完了済み:
- 01a → 01b → 01e → 02c → 03 → 04
- Phase 04結果: 49件中 CONFIRMED_POTENTIAL=1 (M-01), PASS_THROUGH=48
- パイプラインでは M-02〜M-07 は発見できなかった（spec-to-propertyアプローチの限界）

## 6. パターンマッチングDB

### CSV ソース
- `outputs/past_defi_patterns.csv` (95件) — sherlock/code4rena/codehawks 全 HIGH findings
- キーワードカテゴリ: dutch+auction, cowswap/gpv2, EIP-1271, keeper/upkeep, settlement, approval, price+oracle, reentrancy+callback, balance+stale

### 網羅的パターン検証結果 (2026-03-24)

5並列 AI エージェントが 95 パターンを 26 検証項目に分類し、全てのソースコードを直接読んで検証。

| 検証グループ | パターン数 | 結果 | 新規 finding |
|---|---|---|---|
| Dutch Auction (#1-6): 価格曲線、overpayment、終了チェック、refund、partial fill | 16件 | **全て非該当** | なし |
| Oracle/Price (#7-11): flash manipulation、stale/zero price、negative answer、sandwich | 12件 | #9 は M-03 重複、他は非該当 | なし |
| EIP-1271/Approval (#12-16): signature bypass、replay、approval race、callback drain | 17件 | **全て非該当**（`s_entered` が防御の鍵） | なし |
| Reentrancy/Callback (#17-20): bid callback、cross-contract、read-only | 20件 | #18 は config依存 (Low)、#19 は read-only (Low) | なし |
| Keeper/Balance (#21-26): fund theft、overflow、donation、stale balance、precision | 30件 | #25 stale performData は M-01 と同クラス | なし |

**結論: 95パターン × 26検証で M-01〜M-13 を超える新規 HIGH/MEDIUM は発見されなかった。**

### プロトコル防御が堅固な理由

1. `s_entered` が `bid()` + `isValidSignature()` 両方を保護 → callback reentrancy 無効化
2. 全 state-changing function がロールゲート → callback からの権限昇格不可
3. Dutch auction の instant atomic settlement → batch/commit-reveal 系パターン非該当
4. `forceApprove` + immutable vault relayer → approval attack 防止
5. Solady `mulDivUp` の 512bit 中間演算 → precision/overflow attack 防止
6. off-chain Data Streams (DON consensus) → on-chain spot price manipulation 非該当

## 7. コードベース重要ポイント（AIが知るべきこと）

### bid() フロー (BaseAuction.sol L410-458)
1. `s_entered = true` (reentrancy guard)
2. オークション有効性チェック (`auctionStart != 0`, `elapsedTime <= duration`)
3. oracle価格取得 (`_getAssetPrice(asset, true)`)
4. minBidUsdValue チェック
5. `_getAssetOutAmount()` で支払LINK額計算（mulDivUp rounding = protocol有利）
6. `safeTransfer(asset → bidder)` — flash loanパターン
7. callback (任意コード実行、ただしs_entered保護)
8. `safeTransferFrom(LINK ← bidder)` — 支払
9. `s_entered = false`

### isValidSignature() フロー (GPV2CompatibleAuction.sol L119-176)
- CowSwap EIP-1271 order validation (view function)
- `order.buyAmount >= minBuyAmount` = **slippage保護あり** (bid()との非対称性)
- `order.sellAmount <= balanceOf(this)` = balance check
- `s_entered` check = reentrancy protection
- **minBidUsdValueチェックなし** (M-05)

### _getAssetPrice() フォールバック (PriceManager.sol L372-419)
1. Data Streams price (優先)
2. staleならChainlink Data Feed fallback
3. `updatedAt < minTimestamp` で staleness判定（**未来タイムスタンプは通過** = M-07）
4. `latestRoundData()` に **try-catch無し** (M-03)
5. **単一stalenessThreshold** を両ソースに共有 (M-02)

### performUpkeep() (BaseAuction.sol L305-370)
- `performData` は `checkUpkeep()` から来るが **信頼してはいけない** (IBaseAuction doc)
- eligibleAssets: `transferForSwap` → `_onAuctionStart` → `s_auctionStarts[asset] = block.timestamp`
- endedAuctions: **終了条件の再検証なし** (M-04) → `_onAuctionEnd` → `delete s_auctionStarts`
- `_onAuctionEnd`: 残余asset → feeAggregator, **全LINK** → receiver (複数オークション横断)

## 8. テスト実行コマンド

```bash
# 全PoC実行
cd 2026-03-chainlink && forge test --match-path test/poc/M0*.t.sol -vvv

# 個別実行
forge test --match-contract M06_BidNoSlippageProtection -vvv
forge test --match-contract M07_FutureTimestampExtendsValidity -vvv

# テストベース
# M01-M05: C4PoC.t.sol ベース (独自setUp)
# M07: C4PoC.t.sol ベース
# 旧FutureTimestamp.t.sol: BaseIntegrationTest ベース (別)
```

## 9. 提出優先順位（外部レビュー済み）

Issue #158 で独立レビューを受けた結果:

| 順位 | ID | 認められやすさ | 理由 | リスク |
|------|-----|---|---|---|
| 1 | **M-03** | ★★★★★ | 完全同一パターンが C4 で Medium 判定済み (reserve M-10)。反論不可能 | ほぼゼロ |
| 2 | **M-08** | ★★★★☆ | `_onAuctionEnd` revert → auction freeze は明確な DoS。回復関数なし | Low 判定リスク小 |
| 3 | **M-11** | ★★★★☆ | atomic batching → cross-contamination は M-01/M-03 と同クラスだが独立 root cause | 重複判定リスク中 |
| 4 | **M-02** | ★★★☆☆ | M-01 との重複判定リスク。独立 root cause の説明が肝 | 重複判定リスク中 |
| 5 | **M-04** | ★★☆☆☆ | trusted role 前提 → Low/QA 判定リスク最大 | Low 判定リスク大 |
| 6 | **M-06** | ★★☆☆☆ | 外部レビューで「設計/UX制限、Low/Info相当」と判定 | Low/Info 判定リスク大 |
| 7 | **M-07** | ★★☆☆☆ | PRICE_ADMIN_ROLE (trusted) 前提 | Low/Info 判定リスク大 |

## 10. 次にやるべきこと

1. **M-03 を最優先で C4 に提出** (締切: 2026-03-27 20:00 UTC)
2. **M-08〜M-11 の submission MD が未作成なら作成**: `outputs/submitted/` にC4テンプレートで
3. **PoC動作確認**: `forge test --match-path test/poc/M0*.t.sol -vvv` で全PoC PASS を確認
4. **M-02, M-04 は提出判断が必要**: signal score への悪影響 vs 当たった場合の報酬を天秤
5. **M-06, M-07 は Low/Info リスクが高い**: 提出するなら QA report としてまとめる方が安全
6. **結果追跡**: 判定後、各 finding の accept/reject を記録して精度向上に活用

## 11. 監査工数サマリー

| 項目 | 値 |
|---|---|
| 総ラウンド数 | 10+ (SPECA自動5 + 手動5+) |
| 総エージェント数 | 50+ |
| 総パターン検証数 | 360+ (CSV) + 95 (past_defi_patterns) |
| Fuzz テスト | 10 invariants × 1024 runs each |
| 総コスト | ~$50 |
| 自動パイプライン時間 | ~40min |
| Permissionless HIGH | **0** |
| Medium 候補 | **13 (M-01〜M-13)** |
| 提出済み | M-01 (2026-03-22) |

## 12. ファイルマップ

```
security-agent/
├── 2026-03-chainlink/              # ターゲットリポ (submodule)
│   ├── src/                        # スコープ内コントラクト
│   ├── test/poc/                   # PoC ファイル (M01-M07 + 旧PoC)
│   │   ├── C4PoC.t.sol            # 共通テストベース
│   │   ├── M01_OracleStalenessDoS.t.sol
│   │   ├── M02_SharedStalenessThreshold.t.sol
│   │   ├── M03_RevertingDataFeedBlocksAll.t.sol
│   │   ├── M04_PerformUpkeepNoEndValidation.t.sol
│   │   ├── M05_IsValidSignatureNoMinBid.t.sol
│   │   ├── M06_BidNoSlippageProtection.t.sol
│   │   ├── M07_FutureTimestampExtendsValidity.t.sol
│   │   ├── M08_OnAuctionEndRevertFreeze.t.sol
│   │   ├── M09_ValidFromTimestampNotChecked.t.sol
│   │   ├── M10_AllowlistMismatchDoS.t.sol
│   │   ├── M11_AtomicBatchBlocksEnding.t.sol
│   │   ├── FuzzAuctionInvariants.t.sol  # Invariant fuzz tests
│   │   ├── FutureTimestamp.t.sol   # 旧PoC (BaseIntegrationTest)
│   │   └── RoundingFavorsBidder.t.sol # QA
│   └── catalyst.md                 # Zellic Audit Catalyst
├── outputs/
│   ├── submitted/                  # C4提出用MD
│   │   ├── teoshutuzuumi/M01_submission.md  # 提出済み
│   │   ├── M02_submission.md       # 未提出
│   │   ├── M03_submission.md
│   │   ├── M04_submission.md
│   │   ├── M05_submission.md
│   │   ├── M06_submission.md
│   │   └── M07_submission.md
│   ├── c4_dutch_auction_patterns.csv  # パターンDB (45件)
│   └── CHAINLINK_V2_AUDIT_STATE.md   # ← このファイル
└── CLAUDE.md                       # プロジェクト全体の説明
```
