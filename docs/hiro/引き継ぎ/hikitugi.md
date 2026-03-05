# 引き継ぎ資料 — SPECA セキュリティエージェント

> 次回セッション開始時にこのファイルを読んで状況を把握してください。
> 最終更新: 2026-03-06

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
│   ├── rq2a/                          # RepoAudit 15プロジェクト比較 ★NEW
│   ├── archive/rq2_primevul/          # 旧 PrimeVul 関数レベル比較（アーカイブ）
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

## 5. RQ 構成変更（2026-03-04）

> **重要:** PrimeVul 等の関数レベルデータセットは廃止。
> すべての RQ でリポジトリ/プロジェクトレベルのベンチマークを使用する。
> 比較対象ツールの結果は論文記載の数値を引用し、SPECA の結果のみ新規実験で追加。
> 詳細: https://github.com/NyxFoundation/security-agent/issues/96

### 新 RQ 構成

| RQ | 内容 | ベンチマーク | 比較対象 |
|----|------|-------------|---------|
| **RQ2a** | リポジトリレベルバグ検出 | RepoAudit 15 C/C++ プロジェクト (ICML 2025) | RepoAudit, Meta Infer, CodeGuru |
| **RQ2b** | 動的テストとの比較 | ProFuzzBench (ChatAFL, NDSS 2024) | ChatAFL, AFLNet, NSFuzz |

### RQ2a: RepoAudit ベースライン（論文引用）

| ツール | TP | FP | Precision | 出典 |
|--------|----|----|-----------|------|
| RepoAudit (Claude 3.5 Sonnet) | 40 | 11 | 78.43% | Table 2, v3 |
| RepoAudit (DeepSeek R1) | — | — | 88.46% | Appendix, v3 |
| RepoAudit (Claude 3.7 Sonnet) | — | — | 86.79% | Appendix, v3 |
| RepoAudit (o3-mini) | — | — | 82.35% | Appendix, v3 |
| Meta Infer | 7 | 2 | 77.78% | Section 4.4 |
| Amazon CodeGuru | 0 | 18 | 0.00% | Section 4.4 |
| **SPECA** | **TBD** | **TBD** | **TBD** | This study |

可視化済み: `benchmarks/results/rq2a/figures/` (5図)

### RQ2b: ChatAFL ベースライン（ドラフト作成済み、手直し中）

ChatAFL (NDSS 2024) の ProFuzzBench 対象プロトコル実装に対して、
SPECA の仕様チェックとファジングの相補性を示す。
→ バグ単位の突合せ比較（同一メトリクスでの直接比較は不可）

| データ | 出典 |
|--------|------|
| State transitions (Table III) | 6 subjects × 3 tools |
| States covered (Table IV) | 6 subjects × 3 tools |
| Branch coverage (Table V) | 6 subjects × 3 tools |
| Zero-day bugs (Table VII) | 9 bugs |

対象 6 subjects: Live555 (RTSP), ProFTPD (FTP), PureFTPD (FTP), Kamailio (SIP), Exim (SMTP), forked-daapd (DAAP)

Zero-day: ChatAFL 9/9, AFLNet 3/9, NSFuzz 4/9, ChatAFL unique 5/9

可視化済み: `benchmarks/results/rq2b/figures/` (5図)

**状態:** ドラフト作成済み。変更の可能性あり。著者コンタクト未実施。

### 旧 RQ2（PrimeVul）→ アーカイブ

旧 PrimeVul ベースラインは `benchmarks/archive/rq2_primevul/` に移動。
コードは再利用可能な状態で残してある。

### RQ1 ベンチマーク結果（Sherlock Ethereum 監査）

| 指標 | 値 |
|------|-----|
| **Issue Recall** | 0.273 (3/11 issues) |
| **マッチした脆弱性** | #40 Proposer 計算境界 (High), #203 Fiat-Shamir KZG 弱点 (High), #381 署名検証バイパス (Low) |
| **総 Findings** | 254 items（6 クライアント） |

---

## 6. Web クライアント & 監査自動化 (PR #100)

> **PR**: https://github.com/NyxFoundation/security-agent/pull/100
> **ブランチ**: `webclient` (base: `master`)
> **状態**: Open, レビュー待ち
> **変更規模**: 67 files, +8,128 / -122 行

### 6.1 概要

GitHub Actions UI の課題（検索・ナビゲーションの煩雑さ、日本語 UI 不在）を解決する専用 Web クライアントと、Bug Bounty URL を入力するだけで全パイプラインを実行する監査自動化ワークフローを追加。

### 6.2 Web クライアント (`web/`)

Vite + React 19 + TypeScript SPA。全 UI 日本語、ダークテーマ、CSS Modules。

| ページ | パス | 説明 |
|--------|------|------|
| ダッシュボード | `/` | パイプライン概要、6フェーズフロー図、ブランチセレクタ |
| フェーズ詳細 | `/phase/:id` | PARTIAL_*.json テーブル (検索・ソート・フィルタ) |
| プロパティ追跡 | `/property/:id` | 01e→02c→03→04 横断表示 |
| 監査ウィザード | `/audit` | 4ステップ (入力→確認→実行中→完了) |
| 設定 | `/settings` | PAT管理・リポジトリ設定・レート制限 |

**データフロー**: ブラウザから GitHub REST API 直接アクセス。PAT は localStorage 保存（サーバー送信なし）。`outputs/` 内の PARTIAL_*.json をブラウザ側で集約・重複排除。

### 6.3 監査ウィザード (`web/src/pages/AuditWizardPage.tsx`)

- **Step 1 入力**: Bug Bounty URL, Target Repo, Target Ref (任意テキスト), Contract Addresses (アドバンスオプション), Spec URLs, Keywords, Workers, Max Concurrent
- **Step 2 確認**: 入力内容確認 → 「この内容で実行」ボタン
- **Step 3 実行中**: `workflow_dispatch` API → 10秒間隔ポーリング + 経過時間表示
- **Step 4 完了**: 成功/失敗 + GitHub Actions リンク + ダッシュボードリンク

**Sherlock/Immunefi 対応**: `target_ref` でコミットハッシュ指定可能。`contract_addresses` でスマートコントラクトアドレス一覧入力可能。

### 6.4 Full Audit ワークフロー (`.github/workflows/full-audit.yml`)

- **名前**: `hiro Full Audit Pipeline`（hiro プレフィックス必須）
- **トリガー**: `workflow_dispatch` のみ、`self-hosted` ランナー
- **入力**: bug_bounty_url, target_repo, target_ref, contract_addresses, spec_urls, keywords, workers, max_concurrent
- **ステップ**:
  - 0a: Bug Bounty スコープ抽出 (Claude --print で Sherlock/Immunefi 形式に対応)
  - 0b: ターゲットリポジトリ checkout（`ref` パラメータでコミット指定対応）
  - 0c: TARGET_INFO.json 生成
  - 0d: 入力解決 (手動 or 自動抽出)
  - Phase 01a → 01b → 01e → 02c → 03 → 04（各フェーズ後に commit & push）
- **結果ブランチ**: `audit/{target-name}/{YYYYMMDD-HHMMSS}`

### 6.5 既存パイプラインへの影響

**影響なし**: `scripts/orchestrator/`, `scripts/run_phase.py`, `schemas.py` は未変更。Web 側の `pipeline.ts` で `target_ref_type` → `target_ref` リネームのみ。

### 6.6 削除されたワークフロー

- `claude.yml` — @claude メンション bot（Claude GitHub App 用、パイプライン無関係）
- `claude-code-review.yml` — PR 自動レビュー（同上）

### 6.7 既知の課題

1. **PR スクリーンショット**: プライベートリポジトリのため画像埋め込み不可。リンク形式に変更済み。直接埋め込みするには GitHub UI からドラッグ&ドロップで貼り直す必要あり
2. **ウィザード完了→ダッシュボード遷移**: `run.head_branch` はディスパッチ元 (`master`) を返す可能性あり。ワークフロー内部で作成する `audit/...` ブランチとは異なる場合がある
3. **デプロイ先未決定**: GitHub Pages / Vercel / etc.
4. **テスト未追加**: Web クライアント側のテストはなし

### 6.8 主要ファイル一覧

```
web/
├── src/
│   ├── pages/AuditWizardPage.tsx      # 監査ウィザード本体
│   ├── pages/AuditWizardPage.module.css
│   ├── lib/github-client.ts           # dispatch, polling, API ラッパー
│   ├── lib/aggregator.ts              # PARTIAL マージ
│   ├── i18n/ja.ts                     # 全日本語ラベル
│   ├── types/pipeline.ts              # schemas.py の TS 版
│   ├── router.tsx                     # ルート定義
│   └── components/layout/Sidebar.tsx  # ナビゲーション
├── docs/screenshots/                  # PR 用スクリーンショット (5枚)
.github/workflows/full-audit.yml      # hiro Full Audit Pipeline
automation/AUDIT_PLAYBOOK.md           # CLI 版監査手順書
```

---

## 7. 未完了タスク

### 7.1 RQ2a: SPECA 実験実行（優先度: 高）

RepoAudit 15 プロジェクトに対して SPECA を実行し、`ground_truth_bugs.yaml` の `speca` フィールドを埋める。
可視化は baselines-only で完成済み。SPECA 結果を `--speca-results` で渡せば自動でグラフに追加される。

手順:
1. `benchmarks/rq2a/ground_truth_bugs.yaml` のバグ詳細を RepoAudit GitHub から取得
2. SPECA を 15 プロジェクトに実行
3. 結果を `benchmarks/results/rq2a/speca/speca_summary.json` に保存
4. `uv run python3 benchmarks/rq2a/visualize.py --speca-results ...` で再生成

### 7.2 RQ2b: ChatAFL 比較（優先度: 中）

ドラフト作成済み（`benchmarks/rq2b/`）。変更の可能性あり。

手順:
1. ChatAFL 著者にコンタクト → file/function/line 詳細を取得
   - 宛先: ruijie@comp.nus.edu.sg, marcel.boehme@mpi-sp.org
2. `benchmarks/rq2b/ground_truth_bugs.yaml` の詳細フィールドを埋める
3. SPECA を 6 プロトコル実装で実行 (RFC 文書を入力)
4. `uv run python3 benchmarks/rq2b/visualize.py --speca-results ...` で再生成

### 7.3 残りのセキュリティ脆弱性修正（優先度: 高）

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

## 8. 設計原則

1. **部分結果はファーストクラス** -- バッチ結果は即座に保存。バリデーション失敗で保存をブロックしない
2. **サーキットブレーカーは共有** -- 全ワーカーで1つ。システム障害時に高速停止
3. **MCP ファーストのコード解決** -- Phase 02c は Tree-sitter MCP、Phase 03 は Read/Grep/Glob のみ
4. **予算管理は ClaudeRunner に組み込み** -- `BudgetExceeded` で即停止
5. **Phase 02c/03 のターゲット一貫性** -- `TARGET_INFO.json` を共有
6. **インラインプロンプト（01e, 02c, 03, 04）** -- スキルフォークなしでコンテキストオーバーヘッド削減
7. **ドメイン非依存 STRIDE + CWE Top 25** -- CWE-22/78/89/94/200/502/639/770/862。特定ドメインへのハードコードなし

---

## 9. よく使うコマンド

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

# RQ2a 可視化（baselines-only）
uv run python3 benchmarks/rq2a/visualize.py

# MCP セットアップ
bash scripts/setup_mcp.sh
bash scripts/setup_mcp.sh --verify
```

---

## 10. 環境変数

| 変数 | 用途 | 必須場面 |
|------|------|---------|
| `KEYWORDS`, `SPEC_URLS` | Phase 01a 入力 | Phase 01a 実行時 |
| `FORCE_EXECUTE=1` | レジュームバイパス | `--force` で自動設定 |
| `CLAUDE_CODE_PERMISSIONS=bypassPermissions` | CI 権限スキップ | CI のみ |
| `CLAUDE_CODE_MAX_OUTPUT_TOKENS=100000` | CI 出力制限 | CI のみ |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | GitHub MCP | Phase 02c, MCP セットアップ |
| `ANTHROPIC_API_KEY` | security_agent ベンチマーク | RQ2（security_agent 使用時） |

---

## 11. ファイル命名規約

| 種類 | パターン | 例 |
|------|---------|-----|
| 出力 | `outputs/{phase_id}_PARTIAL_W{worker}B{batch}_{timestamp}.json` | `03_AUDITMAP_PARTIAL_W1B2_20260220.json` |
| キュー | `outputs/{phase_id}_QUEUE_{worker_id}.json` | `03_QUEUE_w1.json` |
| ログ | `outputs/logs/{phase_id}_W{worker}B{batch}_{timestamp}.jsonl` | |
| ベンチマーク | `benchmarks/results/rq2a/figures/*.png` | `rq2a_precision_comparison.png` |

---

## 12. 既知の問題・注意点

1. **RQ2a ground_truth_bugs.yaml**: 80% 記入済み (32/40)。残り 8件は RepoAudit 新規発見バグで公開情報なし
2. **RQ2b ドラフト作成済み**: ChatAFL 著者へのコンタクトが必要 (file/function/line 詳細)。変更の可能性あり
3. **旧 PrimeVul コード**: `benchmarks/archive/rq2_primevul/` にアーカイブ済み。再利用可能
4. **`sweagent` 依存**: `pyproject.toml` に git 依存あり。ネットワーク次第で `uv sync` が遅い/失敗する可能性
