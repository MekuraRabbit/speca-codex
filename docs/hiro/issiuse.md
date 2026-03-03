# ベンチマーク Gap Analysis + ベースライン比較

**分析日:** 2026-03-03
**対象:** SPECA ベンチマーク (RQ1 / RQ2)
**目的:** 論文評価として不足している定量化・考察の洗い出し

---

## 1. RQ1 現状データ: Sherlock Ethereum Audit Contest

| 項目 | 値 | 備考 |
|------|------|------|
| 監査対象ブランチ | 10 個 | alloy, c-kzg, grandine, lighthouse, lodestar, nethermind, nimbus, prysm, reth, rust-eth-kzg |
| 検出 findings 数 | 102 | Phase 03 出力 |
| Ground-truth issues (H/M/L) | 15 | Sherlock contest CSV |
| Issue Recall | **100% (15/15)** | High=5/5, Medium=2/2, Low=8/8 |
| Precision (auto) | **66.3%** | auto_tp=17, auto_tp_info=23, auto_tp_other=13 |
| Precision (conservative) | **52.0%** | 22 件 unknown を FP 扱い |
| F1 | **0.797** | |
| Phase 03 全 findings | 647 | phase_comparison.json |
| Phase 04 レビュー済 | 238/647 (36.8%) | |
| Phase 04 DISPUTED_FP | 10 件 | |
| Phase 04 CONFIRMED_VULNERABILITY | 16 件 | |
| Phase 04 CONFIRMED_POTENTIAL | 10 件 | |
| Phase 04 PASS_THROUGH | 197 件 | out-of-scope 自動パス |
| Human label 済 | **0 件** | 22 件 unknown が未ラベルのまま |

**Auto-label 品質:**
- 分析対象: 81 findings (fp_invalid: 54, tp_info: 27)
- 信頼できる (keep): 44 件 (54.3%)
- 要人手レビュー (unknown): 37 件 (45.7%)
- CROSS client matching: **37.8% keep 率** -- 要改善

---

## 2. RQ2 現状データ: PrimeVul ツール比較

**データセット:** PrimeVul C/C++ (868 サンプル, 435 vulnerable, 433 clean, 386 ペア)

| ツール | Precision | Recall | F1 | FPR | Pairwise Acc |
|--------|-----------|--------|------|------|-------------|
| Semgrep | 0.000 | 0.000 | 0.000 | 0.0% | 0/386 (0.0%) |
| Cppcheck | 0.499 | 0.867 | 0.633 | 87.5% | 1/386 (0.3%) |
| Flawfinder | 0.508 | 0.290 | 0.369 | 28.2% | 4/386 (1.0%) |
| Security Agent | -- | -- | -- | -- | **未実行** |

**CWE Coverage (Top 5, Cppcheck/Flawfinder):**

| CWE | 件数 | Cppcheck Recall | Flawfinder Recall |
|-----|------|-----------------|-------------------|
| CWE-787 (Buffer Overflow) | 72 | 0.972 | 0.292 |
| CWE-125 (OOB Read) | 47 | 0.872 | 0.234 |
| CWE-703 (Improper Check) | 47 | 0.745 | 0.213 |
| CWE-476 (Null Ptr Deref) | 39 | 0.846 | 0.256 |
| CWE-416 (Use After Free) | 29 | 0.931 | 0.207 |

**生成済み図表:** fig1 (ツール比較), fig2 (Confusion Matrix), fig3 (CWE Coverage), fig4 (Overview), fig5 (CWE 分布) -- 全図で Security Agent = TBD

---

## 3. 致命的欠落 (論文不成立レベル)

| ID | 問題 | 詳細 | 対応 |
|----|------|------|------|
| **C-1** | Security Agent 結果なし | RQ2 の主張するツールの比較データが完全に欠落 | `run_security_agent.py` 実装 + PrimeVul 全件実行 |
| **C-2** | Semgrep 検出ゼロ | C/C++ 向けルールがほぼ存在しない既知の制限。868 サンプル全件で TP=0, F1=0.000。Docker 権限問題ではなく、Semgrep 自体の C/C++ 対応が根本的に不十分 | 既知の制限として論文に記載。Python/JS との対比で議論 |
| **C-3** | LLM Baseline 全エラー | API 呼び出し失敗で有効な予測 0 件 | エラー原因調査 + 再実行 |
| **C-4** | Human label 未実施 | 22 件 unknown が未ラベル。Precision の信頼性が証明できない | 手動レビュー実施 |

---

## 4. 定量化・考察の不足

### 4.1 定量化が不十分

| ID | 問題 | 対応方法 |
|----|------|----------|
| Q-1 | 信頼区間 (CI) 未報告 | `stats.py` の `bootstrap_rate()` を RQ1/RQ2 に適用 |
| Q-2 | 統計的検定なし | C-1 解決後に McNemar / Cliff's delta を計算 |
| Q-3 | アブレーション未実施 | Phase 04 の 3-gate 各ゲートの個別寄与を分析 |
| Q-4 | Phase 03→04 差分未分析 | 647→637 (10 件フィルタ) の内訳と recall 影響 |
| Q-5 | コスト効率分析なし | Phase 03: ~119.6s/item, Phase 04: ~22.0s/item を集計 |
| Q-6 | RQ1 CWE 別分析なし | findings の CWE 分類を行い分析 |
| Q-7 | Severity 別詳細なし | 個別マッチの分析テーブル作成 |
| Q-8 | Pairwise 統計の意味 | Cppcheck 0.3%, Flawfinder 1.0% が示す限界を考察 |

### 4.2 考察が不足

| ID | 問題 | 対応方法 |
|----|------|----------|
| D-1 | FP 原因分析 | Cross-client matching 37.8% の原因を論文に統合 |
| D-2 | PASS_THROUGH 197 件の妥当性 | out-of-scope 判定の検証 |
| D-3 | サンプルサイズの限界 | Ground-truth 15 件での statistical power 議論 |
| D-4 | LLM matcher の再現性 | confidence 0.85-0.99 の判定基準の定量的説明 |
| D-5 | 他ツールとの比較 | SWE-agent, CodeRabbit 等との定性比較 |
| D-6 | Cross-domain 汎化性 | Ethereum のみ。STRIDE+CWE25 の汎化性の limitation |
| D-7 | 再現性の保証 | Claude バージョン依存の議論 |
| D-8 | Phase 02c resolution rate | 一部ブランチで 17.3% と低い影響分析 |

---

## 5. RQ2 ツール別問題と対応

### 5.1 Semgrep: F1=0.000 (既知の制限)

**根本原因:** Semgrep は C/C++ 向けのルールセットがほぼ存在しない。`--config auto` で実行しても、PrimeVul の関数単位スニペットに対して有効なルールが一切発火しなかった。868 サンプル全件で検出ゼロ。

これは Docker 権限やセットアップの問題ではなく、**Semgrep の C/C++ 対応の根本的な制限**である。Semgrep の主戦場は Python/JavaScript/Go 等であり、C/C++ のメモリ安全性やポインタ操作に関するルールは公式・コミュニティともにほぼ提供されていない。

**論文での扱い:** ベースラインの既知の制限として明記する。Semgrep が他言語では有効であることにも言及し、公正な比較とする。

### 5.2 LLM Baseline: 全件エラー

**原因:** Claude CLI の API 呼び出しが全件失敗。`skipped_missing_pred: 868`。

**対応:** 環境変数の競合確認、API キー・レート制限のデバッグが必要。

### 5.3 Security Agent: 未実装

**原因:** `run_security_agent.py` の `--command` 未指定時は `runner_not_configured` を返すのみ。

**対応:** SPECA パイプライン (01a→01b→01e→02c→03→04) を単一ファイルに対して実行するラッパーの実装が必要。PrimeVul 全 868 件に対する実行コスト（時間・トークン）が課題。

### 5.4 CodeQL: 未実行

**原因:** CI 環境での CodeQL CLI セットアップ未完了。

---

## 6. RQ1 マッチ詳細

### 6.1 マッチした 15 件の内訳

| Issue ID | Severity | Confidence | Finding ID | クライアント |
|----------|----------|------------|------------|-------------|
| #15 | -- | 0.95 | PROP-6a4369e9-inv-047 | Grandine |
| #40 | high | 0.95 | PROP-56ad1eb2-inv-018 | Lighthouse |
| #48 | low | 0.95 | PROP-57888860-inv-051 | rust-eth-kzg |
| #109 | -- | 0.95 | PROP-6a4369e9-inv-047 | (同上 #15) |
| #190 | high | 0.95 | PROP-6a4369e9-inv-042 | Prysm |
| #203 | high | 0.85 | PROP-57888860-inv-001 | c-kzg |
| #210 | -- | 0.95 | PROP-5a6a79d5-inv-059 | Nethermind |
| #216 | -- | 0.95 | PROP-6a4369e9-inv-049 | Grandine |
| #308 | low | 0.95 | PROP-6a4369e9-inv-009 | Grandine |
| #319 | low | 0.95 | PROP-56ad1eb2-inv-029 | Grandine |
| #343 | low | 0.95 | PROP-6a4369e9-inv-050 | Lighthouse |
| #371 | low | 0.99 | PROP-5a6a79d5-inv-036 | Alloy |
| #376 | low | 0.95 | PROP-6a4369e9-pre-003 | Grandine |
| #381 | -- | 0.95 | PROP-56ad1eb2-inv-032 | Lodestar |
| #176 | -- | 0.95 | PROP-5a6a79d5-inv-059 | Nethermind (手動追加) |

注: #176 は LLM matcher が保守的に reject したが手動で追加。マッチング一貫性に課題あり。

### 6.2 Precision 内訳

| ラベル | 件数 | 割合 |
|--------|------|------|
| auto_tp (H/M/L match) | 17 | 16.7% |
| auto_tp_info (info match) | 23 | 22.5% |
| auto_tp_other (fixed/partial) | 13 | 12.7% |
| auto_fp_invalid | 27 | 26.5% |
| auto_unknown | 22 | 21.6% |
| **合計** | **102** | **100%** |

---

## 7. ベースライン分析: コーディングエージェントの構造的優位性

**分析対象:** PrimeVul (n=868, C/C++ 関数レベル, 72 CWE 種別)
**ベースライン:** Semgrep v1.153.0, Cppcheck v2.17.1, Flawfinder v2.0.19

### 7.1 Pairwise Accuracy が露呈する「理解の欠如」

386 ペア中、Cppcheck はたった 1 ペアしか正しく区別できていない。パターンマッチでは脆弱性の根本原因を理解していないことを数値的に証明している。Cppcheck が脆弱コードにフラグを立てても、修正後のコードにも同様にフラグを立てる (FPR=87.5%)。

**含意:** 静的解析ツールは「危険な API パターンの存在」を検出するが、「そのパターンがコンテキスト上で安全かどうか」を判定する能力がない。

### 7.2 コーディングエージェントが優位である構造的理由

**理由 1: セマンティック理解 vs パターンマッチング**

静的解析ツールは構文パターンの存在に依存する。LLM エージェントは関数の意図を理解した上で脆弱性を判定し、パッチ前後の意味的差分を認識できる。

CWE 別データがこれを裏付ける。Cppcheck の弱点:
- CWE-369 (Division by Zero): Recall 64% -- 構文から判定困難
- CWE-617 (Assertion Failure): Recall 58% -- assert 到達条件はセマンティック分析が必要
- CWE-362 (Race Condition): Recall 62% -- 並行性の理解が前提

**理由 2: Precision の根本的限界**

Cppcheck の Precision=0.499 は、フラグの半分が誤検出。静的解析は「可能性」を報告するが、実行パス上の到達可能性を判定しない。SPECA の Phase 04 (3-Gate Review) は推論ベースで FP を体系的に除去する。

**理由 3: CWE カバレッジの柔軟性**

72 CWE 種別に対し、Semgrep は 0 CWE 検出、Flawfinder はメモリ安全性系に限定、Cppcheck は論理的脆弱性に弱い。LLM エージェントは STRIDE + CWE Top 25 をプロンプトレベルで指定するため、ルール追加が不要。

**理由 4: 仕様駆動型アプローチ**

| 比較軸 | 静的解析 | SPECA |
|--------|---------|-------|
| 入力 | ソースコードのみ | 仕様 + ソースコード |
| 検出根拠 | 既知パターン照合 | プロパティ違反 |
| FP 削減 | 情報レベル抑制 | 推論ベース 3-Gate Review |
| 新規脆弱性 | ルール追加が必要 | モデル知識で対応 |

### 7.3 予想される定量的優位性

1. **Pairwise Accuracy**: 静的解析は 0.3-1.0%。エージェントが 10% 以上でも有意な差
2. **論理的 CWE**: CWE-362/369/617 で静的解析の Recall は 58-64%。セマンティック理解で上回る可能性
3. **Precision**: Cppcheck FPR=87.5% は実用不可。Phase 04 が FP を 50% 以上削減できれば大きな差
4. **Union Coverage**: 3 ツール Union でも独自検出は少ない。ツール結合でも検出不能な脆弱性を見つけられるかが鍵

### 7.4 限界と公正な比較の注意点

1. **コスト**: 静的解析は seconds/sample。LLM は API コスト + latency が桁違い
2. **再現性**: 静的解析は決定的。LLM は非決定的 (temperature, model version)
3. **スケーラビリティ**: Cppcheck は数万ファイルを数分。LLM は 868 サンプルでも数時間
4. **誤検出の性質**: 静的解析の FP は過剰検出 (安全側)。LLM の FP は幻覚 (根拠なき誤報) のリスクあり
5. **Semgrep の公正性**: C/C++ は Semgrep の主戦場ではない。Python/JS では検出力が大幅に異なる

**推奨:** 論文では「LLM エージェントが静的解析を置き換える」ではなく「**補完する**」という位置づけが適切。

---

## 8. 過去 Issues 参照

- [#63: actions/checkout EACCES 問題](https://github.com/NyxFoundation/security-agent/issues/63) -- Docker root 所有ファイルが原因。`--user $(id -u):$(id -g)` で対応済み
- RQ2 ベンチマークの詳細手順は `docs/hiro/RQ2_BENCHMARK_GUIDE.md` を参照
- パイプラインフェーズ: `01a` → `01b` → `01e` → `02c` → `03` → `04` (01c/01d は存在しない)
