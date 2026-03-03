# RQ2 ベンチマーク ガイド

> 最終更新: 2026-03-03
> 対象ディレクトリ: `benchmarks/rq2/`, `benchmarks/runners/`, `benchmarks/datasets/`

---

## 1. 概要

RQ2 は「Security Agent が従来の静的解析ツールと比較して、ラベル付き脆弱性データセット上でどの程度の検出性能を発揮するか」を定量評価するベンチマークである。

SPECA パイプラインのフェーズ構成: `01a` → `01b` → `01e` → `02c` → `03` → `04`（01c/01d は存在しない）。

---

## 2. データセット

| データセット | 言語 | 規模 | 取得元 | 状態 |
|---|---|---|---|---|
| **PrimeVul** | C/C++ | 868 サンプル (435 vulnerable, 433 clean) | Hugging Face | 取得済み・評価完了 |
| **CVEFixes** | C/C++ 他 | 約 12GB (Zenodo v1.0.8) | Zenodo | 未処理（要ダウンロード） |

各データセットは「脆弱なコード (vulnerable)」と「修正済みコード (clean)」のペアとして JSONL 形式で保存される。`pair_id` で紐付け（PrimeVul: 412 ペア、うち 386 がスコアリング対象）。

### 2.1 PrimeVul の取得

```bash
uv run python benchmarks/datasets/builders/setup_benchmark.py
```

確認:
```bash
wc -l benchmarks/data/primevul/primevul_test_paired.jsonl  # 868 行
```

### 2.2 CVEFixes（未処理）

Zenodo から約 12GB の SQLite DB をダウンロードする必要がある。サブセット抽出スクリプトは `benchmarks/datasets/builders/setup_cvefixes_subset.py` に実装済み。

```bash
bash benchmarks/datasets/fetch_cvefixes.sh
uv run python benchmarks/datasets/builders/setup_cvefixes_subset.py
```

注意: ダウンロードに時間がかかる。ディスク容量を事前に確認すること。

---

## 3. 評価対象ツール

### 3.1 結果が存在するツール

| ツール | バージョン | 実行スクリプト | 結果ファイル |
|---|---|---|---|
| **Semgrep** | v1.153.0 | `runners/run_semgrep.py` | `semgrep_results.json` |
| **Cppcheck** | v2.17.1 | `runners/run_cppcheck.py` | `cppcheck_results.json` |
| **Flawfinder** | v2.0.19 | `runners/run_flawfinder.py` | `flawfinder_results.json` |

### 3.2 未実行のツール

| ツール | 実行スクリプト | 状態 |
|---|---|---|
| **Security Agent** | `runners/run_security_agent.py` | PrimeVul 未実行 |
| **CodeQL** | `runners/run_codeql.py` | 未実行 |
| **LLM Baseline** | `runners/run_llm_baseline.py` | 故障中（20 件全エラー、0 結果） |

---

## 4. 現在のベンチマーク結果（PrimeVul）

### 4.1 主要指標

| ツール | Precision | Recall | F1 | Accuracy | FPR |
|---|---|---|---|---|---|
| **Cppcheck** | 0.499 | 0.867 | 0.633 | 0.497 | 87.5% |
| **Flawfinder** | 0.508 | 0.290 | 0.369 | 0.503 | 28.2% |
| **Semgrep** | 0.000 | 0.000 | 0.000 | 0.499 | 0.0% |
| **Security Agent** | -- | -- | -- | -- | -- |

Cppcheck: Recall は高いが Precision が低く、ほぼ全サンプルを vulnerable と判定している（FP=379/433）。
Semgrep: C/C++ 向けルールが不十分で TP=0。`--config auto` では関数単位スニペットに対して有効なルールがほぼ発火しない。

### 4.2 Pairwise Accuracy

ペア単位の正解率（vulnerable 側を True かつ clean 側を False と判定できた割合）:

| ツール | Correct | Total | Accuracy |
|---|---|---|---|
| **Cppcheck** | 1 | 386 | 0.3% |
| **Flawfinder** | 4 | 386 | 1.0% |
| **Semgrep** | 0 | 386 | 0.0% |

全ツールとも pairwise accuracy が極めて低い。静的解析ツールは関数単位の差分検出には本質的に不向きであることが示唆される。

### 4.3 生成済みファイル

```
benchmarks/results/rq2/
  metrics.json                         # 全ツール集計メトリクス
  evaluation_summary.json              # 詳細評価
  report.md                            # Markdown レポート
  primevul/
    semgrep_results.json
    cppcheck_results.json
    flawfinder_results.json
    llm_baseline_results.jsonl         # 全エラー (0 結果)
  figures/
    fig1_tool_comparison.png
    fig2_confusion_matrix.png
    fig3_cwe_coverage.png
    fig4_overview.png
    fig5_cwe_distribution.png
```

---

## 5. ツール実行手順

### 5.1 Cppcheck

```bash
uv run python benchmarks/runners/run_cppcheck.py \
  --dataset benchmarks/data/primevul/primevul_test_paired.jsonl \
  --output benchmarks/results/rq2/primevul/cppcheck_results.json \
  --timeout 30
```

### 5.2 Flawfinder

```bash
uv run python benchmarks/runners/run_flawfinder.py \
  --dataset benchmarks/data/primevul/primevul_test_paired.jsonl \
  --output benchmarks/results/rq2/primevul/flawfinder_results.json \
  --timeout 30
```

### 5.3 Semgrep（Docker 経由）

```bash
docker build -t security-agent-benchmark -f benchmarks/Dockerfile .

UIDGID="$(id -u):$(id -g)"
docker run --rm --user "$UIDGID" -v "$PWD":/app -e PYTHONPATH=/app \
  security-agent-benchmark \
  python3 /app/benchmarks/runners/run_semgrep.py \
    --dataset /app/benchmarks/data/primevul/primevul_test_paired.jsonl \
    --output /app/benchmarks/results/rq2/primevul/semgrep_results.json \
    --timeout 60
```

### 5.4 Security Agent（未実行）

```bash
uv run python benchmarks/runners/run_security_agent.py \
  --dataset benchmarks/data/primevul/primevul_test_paired.jsonl \
  --output benchmarks/results/rq2/primevul/security_agent_results.jsonl \
  --tmp-dir benchmarks/tmp/security_agent \
  --command "bash benchmarks/runners/invoke_security_agent.sh {code_path} {output_path} {case_id}" \
  --shell \
  --timeout 300 \
  --limit 10  # まず少数でテスト
```

出力 JSON の必須フィールド: `predicted_vulnerable` (true/false)。

### 5.5 CodeQL（未実行）

```bash
uv run python benchmarks/runners/run_codeql.py \
  --dataset benchmarks/data/primevul/primevul_test_paired.jsonl \
  --output benchmarks/results/rq2/primevul/codeql_results.jsonl \
  --tmp-dir benchmarks/tmp/codeql \
  --timeout 120
```

---

## 6. 評価と可視化

### 6.1 評価の実行

```bash
uv run python benchmarks/rq2/evaluate.py \
  --dataset primevul \
  --dataset-path benchmarks/data/primevul/primevul_test_paired.jsonl
```

`--output-dir` オプションで出力先を変更可能:

```bash
uv run python benchmarks/rq2/evaluate.py \
  --dataset primevul \
  --dataset-path benchmarks/data/primevul/primevul_test_paired.jsonl \
  --output-dir benchmarks/results/rq2_custom
```

生成ファイル:
- `evaluation_summary.json` -- 全ツールの TP/FP/TN/FN、CWE カバレッジ
- `metrics.json` -- 集計メトリクス

### 6.2 可視化

```bash
uv run python benchmarks/rq2/visualize.py \
  --metrics benchmarks/results/rq2/metrics.json
```

`visualize.py` はデータセット名を `metrics.json` から動的に取得してグラフタイトルに反映する。表示対象ツールは `DISPLAY_ORDER` で制御（デフォルト: Semgrep, Cppcheck, Flawfinder, Security Agent）。

出力先: `benchmarks/results/rq2/figures/` (fig1〜fig5)

### 6.3 評価指標

| 指標 | 説明 |
|---|---|
| Precision / Recall / F1 | 標準的な二値分類指標 |
| Coverage | スコアリングされたサンプル数 / 全サンプル数 |
| Pairwise Accuracy | ペア単位の正解率（vulnerable=True かつ clean=False） |
| CWE Coverage | CWE カテゴリごとの Recall |
| Unique Detections | Security Agent のみが検出した脆弱性 |
| McNemar Exact Test | ツール間の有意差検定 |
| Cliff's Delta | 効果量 (negligible / small / medium / large) |
| Bootstrap CI | 95% 信頼区間 (2000 サンプル) |

---

## 7. 既知の問題

### 7.1 Docker root パーミッション問題

Semgrep を Docker で実行すると、コンテナ内で生成されたファイルが root 所有になり、後続ジョブの `actions/checkout` クリーンアップが `EACCES` で失敗する。

対策: `docker run` に `--user "$(id -u):$(id -g)"` を付与する（上記 5.3 参照）。

### 7.2 Semgrep の C/C++ ルール不足

`--config auto` では PrimeVul の関数単位スニペットに対してルールがほぼ発火しない（TP=0, F1=0.000）。C/C++ 向けの Semgrep ルールセットが根本的に不十分。カスタムルールの作成か、別の設定の検討が必要。

### 7.3 LLM Baseline の故障

20 件実行して全件エラー。`skipped_missing_pred: 868` で有効な予測が 0 件。Claude CLI の呼び出し部分のデバッグが必要。

### 7.4 CVEFixes の大容量ダウンロード

Zenodo から約 12GB の SQLite DB をダウンロードする必要がある。ネットワーク環境とディスク容量を事前に確認すること。

### 7.5 Cppcheck の高 FPR

Cppcheck は Recall 86.7% だが FPR が 87.5%（433 clean のうち 379 を vulnerable と誤判定）。関数単位の解析では「何らかの警告が出る」ことが多く、ほぼ全件を vulnerable と判定する傾向がある。

---

## 8. 主要スクリプト一覧

| ファイル | 説明 |
|---|---|
| `benchmarks/runners/run_semgrep.py` | Semgrep ランナー (Docker 経由) |
| `benchmarks/runners/run_cppcheck.py` | Cppcheck ランナー |
| `benchmarks/runners/run_flawfinder.py` | Flawfinder ランナー |
| `benchmarks/runners/run_codeql.py` | CodeQL ランナー |
| `benchmarks/runners/run_security_agent.py` | Security Agent ランナー |
| `benchmarks/runners/run_llm_baseline.py` | LLM Baseline ランナー |
| `benchmarks/rq2/evaluate.py` | 評価パイプライン (`--output-dir` 対応) |
| `benchmarks/rq2/visualize.py` | グラフ生成 (動的データセットタイトル) |
| `benchmarks/rq2/generate_report.py` | Markdown レポート生成 |
| `benchmarks/datasets/builders/setup_benchmark.py` | PrimeVul データセット取得 |
| `benchmarks/datasets/builders/setup_cvefixes_subset.py` | CVEFixes サブセット抽出 |
| `benchmarks/datasets/fetch_cvefixes.sh` | CVEFixes DB ダウンロード |
| `benchmarks/bench_utils.py` | ID/ラベル/コード抽出ユーティリティ |
| `benchmarks/tools/registry.py` | ツールレジストリ |
| `benchmarks/datasets/registry.py` | データセットレジストリ |
| `benchmarks/metrics/classification.py` | 分類指標の計算 |
| `benchmarks/metrics/stats.py` | 統計検定・ブートストラップ CI |

---

## 9. 次のステップ

1. **Security Agent の PrimeVul 実行** -- `invoke_security_agent.sh` の本体実装が前提
2. **CodeQL の実行** -- `codeql` CLI のセットアップと実行
3. **LLM Baseline の修正** -- エラー原因の特定と再実行
4. **CVEFixes データセットの処理** -- 12GB ダウンロードとサブセット抽出
5. **評価の再実行と比較** -- 全ツール揃った状態での統計的比較
