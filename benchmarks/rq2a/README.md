# RQ2a: リポジトリレベルバグ検出ベンチマーク

**ベンチマーク:** RepoAudit 15 C/C++ プロジェクト (ICML 2025)
**Issue:** https://github.com/NyxFoundation/security-agent/issues/96

## 概要

RepoAudit 論文で使用された 15 個の C/C++ OSS プロジェクトに対して、
SPECA の検出性能を既存ツール (Meta Infer, Amazon CodeGuru, 各種 LLM) と比較する。

**比較対象ツールの結果は論文記載の数値を引用し、SPECA の結果のみ新規実験で追加する。**

## ファイル構成

```
benchmarks/rq2a/
  published_baselines.yaml   # 論文データ (集約数値 + per-project, 手動転記)
  ground_truth_bugs.yaml     # 具体的バグリスト (照合用, TODO: 詳細を埋める)
  visualize.py               # 可視化スクリプト
  README.md                  # このファイル

benchmarks/results/rq2a/
  figures/                   # 生成グラフ
  speca/                     # SPECA 結果 (後で追加)
```

## 実行方法

```bash
# 可視化 (baselines-only)
uv run python3 benchmarks/rq2a/visualize.py

# SPECA 結果を含む場合
uv run python3 benchmarks/rq2a/visualize.py --speca-results benchmarks/results/rq2a/speca/speca_summary.json
```

## データソース

### 論文

- **RepoAudit: An Autonomous LLM-Agent for Repository-Level Code Auditing**
- 会議: ICML 2025
- arXiv: https://arxiv.org/abs/2501.18160
- PDF (v3, camera-ready): https://arxiv.org/pdf/2501.18160v3
- GitHub: https://github.com/PurCL/RepoAudit

> **注意:** v3 (camera-ready) の数値を使用。v1 とは異なる（例: DeepSeek R1 Precision v3=88.46% vs v1=75.86%）。

### ベースライン数値の出典

| ツール | TP | FP | Precision | 出典 |
|--------|----|----|-----------|------|
| RepoAudit (Claude 3.5 Sonnet) | 40 | 11 | 78.43% | Table 2, v3 |
| RepoAudit (DeepSeek R1) | — | — | 88.46% | Appendix, v3 |
| RepoAudit (Claude 3.7 Sonnet) | — | — | 86.79% | Appendix, v3 |
| RepoAudit (o3-mini) | — | — | 82.35% | Appendix, v3 |
| Meta Infer | 7 | 2 | 77.78% | Section 4.4, v3 |
| Amazon CodeGuru | 0 | 18 | 0.00% | Section 4.4, v3 |
| Single-function LLM | 1 | — | — | Section 4.3, v3 |
| **SPECA** | **TBD** | **TBD** | **TBD** | This study |

### per-project 内訳の出典

- Table 2 (v3): 15プロジェクト別の Old TP / New TP / FP 内訳
- Appendix B (v3): DeepSeek R1, Claude 3.7 Sonnet, o3-mini のプロジェクト別内訳
- コスト情報: Section 4.2 (v3) — Avg $2.54/project, $0.95/bug, 0.44h/project

### Ground Truth バグの出典

| ソース | 件数 | 取得方法 |
|--------|------|----------|
| RepoAudit バグリスト (GitHub) | 40件の ID・種別・プロジェクト | https://repoaudit-home.github.io/static/bug/old/ |
| sofa-pbrpc PRs #248-#250 | NPD 3件のファイル/関数/行 | https://github.com/baidu/sofa-pbrpc/pull/248 等 |
| memcached PRs #1208-#1217 | MLK 10件のファイル/関数/行 | https://github.com/memcached/memcached/pull/1208 等 |
| libsass PR #3192 | NPD 1件のファイル/関数/行 | https://github.com/sass/libsass/pull/3192 |
| OpenLDAP ITS#10309 | MLK 1件のファイル/関数/行 | https://bugs.openldap.org/show_bug.cgi?id=10309 |
| CVE-2022-48670 (Linux kernel) | UAF 1件のファイル/関数/行 | Linux kernel commit |
| 論文 Table 2 + Appendix B | プロジェクト別 Old/New 内訳 | arXiv v3 PDF |
| 残り 8件 (New bugs) | 公開情報なし | 著者コンタクトまたはサブモジュール調査が必要 |
