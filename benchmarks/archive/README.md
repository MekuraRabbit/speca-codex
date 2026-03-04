# Archive: 旧 RQ2 (PrimeVul 関数レベルベンチマーク)

**アーカイブ日:** 2026-03-04
**理由:** RQ 構成変更により、関数レベルデータセット (PrimeVul) は廃止。
リポジトリ/プロジェクトレベルのベンチマークに移行。

詳細: https://github.com/NyxFoundation/security-agent/issues/96

## 新しい RQ 構成

| RQ | 内容 | ベンチマーク |
|----|------|-------------|
| RQ2a | リポジトリレベルバグ検出 | RepoAudit 15 プロジェクト |
| RQ2b | 動的テストとの比較 | ProFuzzBench (ChatAFL) |

## アーカイブ内容

### 評価コード
- `rq2_primevul/` — PrimeVul 評価・可視化スクリプト (evaluate.py, visualize.py)
- `results_rq2/` — PrimeVul ベースライン結果 (Semgrep, Cppcheck, Flawfinder)

### ツールランナー
- `runners/` — 旧ベンチマーク用ツール実行スクリプト (Semgrep, CodeQL, Cppcheck, Flawfinder, LLM baseline, Security Agent)
- `Dockerfile` — Semgrep 用 Docker イメージ定義

### データセット
- `datasets/` — PrimeVul / CVEFixes / Vul4J データセット取得・ビルドスクリプト
- `run_cvefixes_baseline.sh` — CVEFixes 自動化スクリプト

### ユーティリティ
- `bench_utils.py` — JSONL 入出力、ラベル正規化、言語判定ヘルパー
- `tools/` — ツール結果ローダー・レジストリ
- `metrics/` — 分類メトリクス (Confusion Matrix, Bootstrap CI, McNemar, Cliff's delta)

### スクリプト・ワークフロー
- `scripts/run_rq2_local.sh` — 旧 PrimeVul ローカル実行パイプライン
- `workflows/` — 旧 GitHub Actions ワークフロー (setup, tools, evaluate)

### テスト
- `tests/test_rq2_pipeline.py` — 旧 PrimeVul 評価パイプラインのテスト
- `tests/test_sec_c01_c04_command_injection.py` — base_runner コマンドインジェクション防止テスト

## 再利用可能性

- `evaluate.py` のメトリクス計算ロジック (Precision/Recall/F1, Pairwise Accuracy) は流用可能
- `visualize.py` のグラフ生成パターンも参考にできる
- `metrics/stats.py` の Bootstrap CI / McNemar 検定は統計比較に再利用可能
- PrimeVul ベースライン結果 (Cppcheck F1=0.633, Flawfinder F1=0.369) は論文の背景説明に引用可能
