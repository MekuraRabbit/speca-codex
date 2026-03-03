# 引き継ぎ資料 — SPECA セキュリティエージェント

> 次回セッション開始時にこのファイルを読んで状況を把握してください。
> 最終更新: 2026-03-03

---

## 1. プロジェクト概要

**SPECA** (Specification-to-Property Agentic Auditing) は、Claude Code CLI を使った自動セキュリティ監査パイプラインです。仕様書からフォーマルなプログラムグラフを構築し、ドメイン非依存の STRIDE + CWE Top 25 脅威モデルによるセキュリティプロパティを生成、ターゲットコードに対して証明ベースの形式的監査（Map → Prove → Stress-Test）を実行し、recall-safe な3ゲートレビュー（Dead Code → Trust Boundary → Scope Check）で偽陽性をフィルタします。

詳細は `CLAUDE.md`（リポジトリルート）を参照。

---

## 2. パイプラインフロー

Phase IDs: `01a` → `01b` → `01e` → `02c` → `03` → `04`

```
01a Spec Discovery       仕様書URLのクロール・発見
  |
01b Subgraph Extraction  仕様書 → Mermaid 状態図 (.mmd + YAML frontmatter)
  |
01e Property Generation  ドメイン非依存 STRIDE + CWE Top 25 + セキュリティプロパティ生成
  |                      ※ BUG_BOUNTY_SCOPE.json 必須（なければ sys.exit(1)）
  |                      ※ インラインプロンプト（スキルフォークなし）
02c Code Pre-resolution  Tree-sitter MCP でコード位置の事前解決（トークン 40-60% 削減）
  |                      ※ TARGET_INFO.json 必須（ワークフローが事前作成）
  |                      ※ Informational 深刻度はゲートで除外
03  Audit Map            証明ベース3段階フォーマル監査（Map → Prove → Stress-Test）
  |                      プロパティの証明を試み、証明のギャップが finding となる
04  Review               recall-safe 3ゲート FP フィルタ（早期終了あり）
                         Dead Code → Trust Boundary → Scope Check
                         判定: CONFIRMED_VULNERABILITY / CONFIRMED_POTENTIAL /
                               DISPUTED_FP / DOWNGRADED / NEEDS_MANUAL_REVIEW / PASS_THROUGH
--- 手動フェーズ ---
05  PoC Generation       脆弱性ごとの再現テスト生成
06  Bug-Bounty Report    プラットフォーム別レポート
06b Full Audit Report    出版可能な完全監査レポート
```

**スキルシステム**: Phase 01a (`spec-discovery`), 01b (`subgraph-extractor`) のみスキルフォーク使用。01e, 02c, 03, 04 はインラインプロンプト。

---

## 3. リポジトリ構成（主要ファイル）

```
security-agent/
├── CLAUDE.md                          # Claude Code 用プロジェクト規約（必読）
├── pyproject.toml                     # Python 依存関係（uv, Python >=3.11）
├── .mcp.json                          # MCP サーバー設定
├── .claude/skills/                    # スキル定義
│   ├── spec-discovery/                # Phase 01a
│   └── subgraph-extractor/            # Phase 01b
├── scripts/
│   ├── run_phase.py                   # パイプライン実行エントリポイント
│   ├── setup_mcp.sh                   # MCP サーバー登録
│   └── orchestrator/                  # 非同期 Python オーケストレーター
│       ├── base.py                    # BaseOrchestrator（並列実行、レジューム）
│       ├── config.py                  # PhaseConfig（全フェーズ定義）
│       ├── runner.py                  # ClaudeRunner（CLI 呼び出し、サーキットブレーカー）
│       ├── watchdog.py                # LogWatcher、CostTracker（予算管理）
│       ├── resume.py                  # ResumeManager
│       ├── collector.py               # ResultCollector（部分結果の即時保存）
│       └── schemas.py                 # Pydantic データ契約（フェーズ間検証）
├── prompts/                           # フェーズ別ワーカープロンプト
│   ├── 01a_crawl.md
│   ├── 01b_extract_worker.md
│   ├── 01e_prop_worker.md             # インライン
│   ├── 02c_codelocation_worker.md     # インライン
│   ├── 03_auditmap_worker_inline.md   # インライン
│   ├── 04_review_worker.md            # インライン
│   ├── 05_poc.md                      # 手動
│   ├── 06_report.md                   # 手動
│   └── 06b_audit_report.md            # 手動
├── outputs/                           # パイプライン出力（PARTIAL_*.json）
├── tests/                             # pytest テスト
├── benchmarks/                        # RQ1 & RQ2 ベンチマーク
│   ├── rq1/                           # Sherlock 監査コンテスト評価
│   ├── rq2/                           # PrimeVul ツール比較
│   ├── runners/                       # ツール実行ラッパー
│   ├── datasets/builders/             # データセットビルダー
│   └── results/                       # ベンチマーク結果
└── .github/workflows/                 # CI/CD ワークフロー
```

---

## 4. セキュリティ脆弱性修正（SEC-C01〜C04）

Critical 4件を修正済み（PR マージ済み）。

| ID | 脆弱性 | ファイル | 修正内容 |
|---|---|---|---|
| SEC-C01 | コマンドインジェクション (`run_command`) | `benchmarks/runners/base_runner.py` | `shell=True` 時に `shlex.quote()` で全パラメータをエスケープ |
| SEC-C02 | パストラバーサル (LLM出力パス) | `scripts/orchestrator/base.py` | `_is_safe_output_path()` ヘルパー追加、`outputs/` 外へのアクセスをブロック |
| SEC-C03 | スクリプトインジェクション (GitHub Actions) | `.github/workflows/openhands-resolver.yml` | `${{ }}` 展開を `context.payload` 経由に変更 |
| SEC-C04 | コマンドインジェクション (`resolve_version`) | `benchmarks/runners/base_runner.py` | `shlex.split()` + `shell=False` に変更 |

### 追加されたセキュリティテスト

| テストファイル | 件数 | 内容 |
|---|---|---|
| `tests/test_sec_c01_c04_command_injection.py` | 8件 | シェルエスケープ検証、`shell=False` 検証 |
| `tests/test_sec_c02_path_traversal.py` | 6件 | パストラバーサルガードの正常/異常パス検証 |

### 技術的注意点

- **SEC-C02**: `_is_safe_output_path()` は `Path("outputs").resolve()` をベースにしている。CWD 依存のため、テストはリポジトリルートが CWD である前提
- **SEC-C01**: `use_shell=True` 時のみエスケープ適用。テンプレート自体にクォートを含めないこと

---

## 5. RQ2 ベンチマーク結果（PrimeVul ベースライン）

データセット: PrimeVul test paired (868 samples, 386 pairs)

### 現在のベースライン結果

| ツール | TP | FP | TN | FN | Precision | Recall | **F1** | Pairwise Acc |
|--------|----|----|----|----|-----------|--------|--------|-------------|
| **Semgrep** | 0 | 0 | 433 | 435 | 0.000 | 0.000 | **0.000** | 0.000 |
| **Cppcheck** | 377 | 379 | 54 | 58 | 0.499 | 0.867 | **0.633** | 0.003 |
| **Flawfinder** | 126 | 122 | 311 | 309 | 0.508 | 0.290 | **0.369** | 0.010 |
| LLM Baseline | - | - | - | - | - | - | - | (全エラー、coverage=0) |
| CodeQL | - | - | - | - | - | - | - | (未実行) |
| Security Agent | - | - | - | - | - | - | - | (未実行) |

### 考察

- **Semgrep**: ルールマッチング方式のため C/C++ の低レベル脆弱性（メモリ安全性）を検出できず全滅
- **Cppcheck**: 高 recall (86.7%) だが precision が低い (49.9%)。ほぼ全関数を vulnerable と判定する傾向
- **Flawfinder**: パターンマッチベースで中間的な性能。precision は最も高い (50.8%)

### RQ1 ベンチマーク結果（Sherlock Ethereum 監査）

| 指標 | 値 |
|------|-----|
| **Issue Recall** | 0.273 (3/11 issues) |
| **マッチした脆弱性** | #40 Proposer 計算境界 (High), #203 Fiat-Shamir KZG 弱点 (High), #381 署名検証バイパス (Low) |
| **総 Findings** | 254 items（6 クライアント） |

---

## 6. 未完了タスク

### 6.1 RQ2: Security Agent ベンチマーク実行（優先度: 高）

`invoke_security_agent.sh` の本体を実装し、SPECA を PrimeVul データセットで評価する。現在プレースホルダー。

### 6.2 残りのセキュリティ脆弱性修正（優先度: 高）

`docs/hiro/kijaku.md` の残り 66件。優先度順:

**P1 — 短期対応（次回推奨）**

| ID | 概要 | ファイル |
|---|---|---|
| SEC-H01 | Gitトークン漏洩（8ワークフロー） | `.github/workflows/*.yml` |
| SEC-H02 | TOCTOU レース（MCP設定ファイル） | `scripts/orchestrator/runner.py` |
| SEC-H03 | レースコンディション（PARTIAL読み取り） | `scripts/orchestrator/resume.py`, `collector.py` |
| SEC-H04 | sweagent 未ピン留め | `pyproject.toml` |
| SEC-H05 | ワークフロー権限の過剰付与 | `.github/workflows/*.yml` |
| BUG-CI01 | Heredoc で BUG_BOUNTY_SCOPE.json 不正JSON | `01e-properties.yml` |
| BUG-CI02 | git user.name/email 未設定 | `benchmark-rq1-sherlock-eval.yml` |
| BUG-ORC01 | `sys.exit()` をカスタム例外に | `scripts/orchestrator/base.py` |
| BUG-ORC03 | 正規表現 大文字/小文字不一致 | `scripts/orchestrator/resume.py` |
| BUG-SCH01/02 | スキーマと Phase 03 出力の不一致 | `scripts/orchestrator/schemas.py` |

**P2 — 中期対応**

- SEC-M01〜M06: Medium セキュリティ脆弱性 6件
- BUG-ORC02/04/05: オーケストレーターロジックバグ
- BUG-BEN01〜08: ベンチマーク/評価のバグ
- BUG-SCH03〜07: スキーマ整合性 + テスト修正

**アプローチ推奨:**
- SEC-H01（8ワークフローの一括置換）はエージェント並列実行が有効
- SEC-H02/H03（レースコンディション）はアトミック書き込み実装のため一緒に対応
- BUG-ORC/SCH 系は相互依存があるためスキーマ修正を先に行うこと

---

## 7. 設計原則

1. **部分結果はファーストクラス** -- バッチ結果は即座に保存。バリデーション失敗で保存をブロックしない
2. **サーキットブレーカーは共有** -- 全ワーカーで1つ。システム障害時に高速停止
3. **MCP ファーストのコード解決** -- Phase 02c は Tree-sitter MCP、Phase 03 は Read/Grep/Glob のみ
4. **予算管理は ClaudeRunner に組み込み** -- `BudgetExceeded` で即停止
5. **Phase 02c/03 のターゲット一貫性** -- `TARGET_INFO.json` を共有
6. **インラインプロンプト（01e, 02c, 03, 04）** -- スキルフォークなしでコンテキストオーバーヘッド削減
7. **ドメイン非依存 STRIDE + CWE Top 25** -- CWE-22/78/89/94/200/502/639/770/862。特定ドメインへのハードコードなし

---

## 8. よく使うコマンド

```bash
# 環境セットアップ
uv sync

# テスト（全フェーズ実行前に必ず実施）
uv run python3 -m pytest tests/ -v --tb=short

# セキュリティ関連テストのみ
uv run python3 -m pytest tests/test_sec_*.py -v

# パイプライン実行
uv run python3 scripts/run_phase.py --phase 01a
uv run python3 scripts/run_phase.py --phase 01a 01b 01e
uv run python3 scripts/run_phase.py --target 04 --workers 4
uv run python3 scripts/run_phase.py --phase 03 --force --workers 4 --max-concurrent 64

# ベンチマーク（ローカル）
bash benchmarks/scripts/run_rq2_local.sh primevul semgrep

# MCP セットアップ
bash scripts/setup_mcp.sh
bash scripts/setup_mcp.sh --verify
```

---

## 9. 環境変数

| 変数 | 用途 | 必須場面 |
|------|------|---------|
| `KEYWORDS`, `SPEC_URLS` | Phase 01a 入力 | Phase 01a 実行時 |
| `FORCE_EXECUTE=1` | レジュームバイパス | `--force` で自動設定 |
| `CLAUDE_CODE_PERMISSIONS=bypassPermissions` | CI 権限スキップ | CI のみ |
| `CLAUDE_CODE_MAX_OUTPUT_TOKENS=100000` | CI 出力制限 | CI のみ |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | GitHub MCP | Phase 02c, MCP セットアップ |
| `ANTHROPIC_API_KEY` | security_agent ベンチマーク | RQ2（security_agent 使用時） |

---

## 10. ファイル命名規約

| 種類 | パターン | 例 |
|------|---------|-----|
| 出力 | `outputs/{phase_id}_PARTIAL_W{worker}B{batch}_{timestamp}.json` | `03_AUDITMAP_PARTIAL_W1B2_20260220.json` |
| キュー | `outputs/{phase_id}_QUEUE_{worker_id}.json` | `03_QUEUE_w1.json` |
| ログ | `outputs/logs/{phase_id}_W{worker}B{batch}_{timestamp}.jsonl` | |
| ベンチマーク | `benchmarks/results/rq2/{dataset}/{tool}_results.json(l)` | `primevul/semgrep_results.json` |

---

## 11. 既知の問題・注意点

1. **`invoke_security_agent.sh`**: 本体未実装。`"error": "not_implemented"` を返すのみ
2. **Docker 必須**: Semgrep ランナーは Docker コンテナ内実行。Docker なし環境ではスキップされる
3. **`sweagent` 依存**: `pyproject.toml` に git 依存あり。ネットワーク次第で `uv sync` が遅い/失敗する可能性
4. **LLM Baseline 全エラー**: coverage=0、全 868 サンプルが skipped。再実行が必要
5. **CodeQL / Security Agent 未実行**: `missing_results` ステータス
