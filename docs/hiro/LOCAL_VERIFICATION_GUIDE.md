# SPECA ローカル手動検証ガイド

ローカル環境でパイプラインの各フェーズを手動で実行・検証するための手順書。

---

## 目次

1. [環境セットアップ](#1-環境セットアップ)
2. [事前チェック（Pre-flight）](#2-事前チェックpre-flight)
3. [フェーズ別 実行・検証手順](#3-フェーズ別-実行検証手順)
4. [出力ファイルの検証方法](#4-出力ファイルの検証方法)
5. [手動フェーズ（05・06・06b）](#5-手動フェーズ050606b)
6. [トラブルシューティング](#6-トラブルシューティング)

---

## 1. 環境セットアップ

### 1.1 前提条件のインストール

```bash
# Python 3.11+
python3 --version  # >= 3.11 を確認

# uv（Python パッケージマネージャ）
curl -LsSf https://astral.sh/uv/install.sh | sh

# Node.js & npm
node --version     # >= 18 を推奨
npm --version

# Claude Code CLI
npm install -g @anthropic-ai/claude-code
claude --version
```

### 1.2 Python 依存パッケージのインストール

```bash
cd /path/to/security-agent
uv sync
```

### 1.3 MCP サーバーの登録

```bash
# 全サーバーを登録
bash scripts/setup_mcp.sh

# 登録状態を確認
bash scripts/setup_mcp.sh --verify
```

**確認ポイント:**
- 全サーバーが `[OK]` と表示されること
- Phase 02c で Tree-sitter MCP を使用するため、`tree_sitter` の登録は必須
- GitHub MCP を使うフェーズでは `GITHUB_PERSONAL_ACCESS_TOKEN` が必要

### 1.4 環境変数の設定

```bash
# Phase 01a に必要
export KEYWORDS="geth,ethereum client,execution specs,EIP"
export SPEC_URLS="https://ethereum.github.io/execution-specs/src/,https://geth.ethereum.org/docs"

# GitHub MCP（任意）
export GITHUB_PERSONAL_ACCESS_TOKEN="ghp_..."
```

---

## 2. 事前チェック（Pre-flight）

**すべてのフェーズ実行前に必ず実施する。**

```bash
uv run python3 -m pytest tests/ -v --tb=short
```

**確認ポイント:**
- 全テストが `PASSED` であること
- スキーマ定義テスト（`test_schemas_and_config.py`）が通ること
- Phase 03 の早期終了ロジックテストが通ること

---

## 3. フェーズ別 実行・検証手順

### パイプライン依存関係

```
01a → 01b → 01e → 02c → 03 → 04
```

- Phase 01e は `outputs/BUG_BOUNTY_SCOPE.json` が必須（未配置時はオーケストレータが異常終了する）
- Phase 02c は `outputs/TARGET_INFO.json` が必須（CI ワークフローが事前に生成する）
- Phase 03/04 も同じ `TARGET_INFO.json` を参照する

---

### Phase 01a: 仕様書ディスカバリ

**実行:**
```bash
uv run python3 scripts/run_phase.py --phase 01a
```

**出力ファイル:** `outputs/01a_STATE.json`

**確認項目:**

| # | 確認内容 | 方法 |
|---|---------|------|
| 1 | ファイルが生成されている | `ls -la outputs/01a_STATE.json` |
| 2 | JSON が valid | `python3 -m json.tool outputs/01a_STATE.json > /dev/null` |
| 3 | `found_specs` 配列が空でない | 目視 or `jq '.found_specs | length'` |
| 4 | 各 spec に `url` フィールドがある | 目視で確認 |

---

### Phase 01b: サブグラフ抽出

**実行:**
```bash
uv run python3 scripts/run_phase.py --phase 01b --workers 2
```

**出力ファイル:** `outputs/01b_PARTIAL_*.json`, `outputs/graphs/*/*.mmd`

**確認項目:**

| # | 確認内容 | 方法 |
|---|---------|------|
| 1 | PARTIAL ファイルが生成されている | `ls outputs/01b_PARTIAL_*.json` |
| 2 | `outputs/graphs/` 配下にディレクトリがある | `ls outputs/graphs/` |
| 3 | Mermaid ファイル（`.mmd`）が生成されている | `find outputs/graphs -name "*.mmd"` |
| 4 | `.mmd` に YAML frontmatter がある | 先頭に `---` ブロックがあること |
| 5 | `note right of` による不変条件ブロックがある | 目視で確認 |

---

### Phase 01e: プロパティ生成

Trust Model 分析（STRIDE + CWE Top 25）とセキュリティプロパティの生成を行う。インラインプロンプト（スキルフォークなし）。

**前提条件:** `outputs/BUG_BOUNTY_SCOPE.json` が配置されていること。

**実行:**
```bash
uv run python3 scripts/run_phase.py --phase 01e --workers 2
```

**出力ファイル:** `outputs/01e_PARTIAL_*.json`

**確認項目:**

| # | 確認内容 | 方法 |
|---|---------|------|
| 1 | PARTIAL ファイルが生成されている | `ls outputs/01e_PARTIAL_*.json` |
| 2 | 各プロパティに `property_id` がある | ユニークな ID があること |
| 3 | `invariant` と `anti_property` が定義されている | 形式的な不変条件と反例が記述されていること |
| 4 | `severity` が適切 | `Critical` / `High` / `Medium` / `Low` / `Informational` |
| 5 | `covers` がプライマリ要素 ID（文字列） | 例: `"FN-001"` |
| 6 | `reachability` が 4 フィールド | `classification`, `entry_points`, `attacker_controlled`, `bug_bounty_scope` |

---

### Phase 02c: コード位置の事前解決

Tree-sitter MCP を使い、プロパティに対応するコード位置（`code_scope`）を事前に解決する。`Informational` 重要度のプロパティは自動で除外される。

**前提条件:** `outputs/TARGET_INFO.json` が配置されていること。

**実行:**
```bash
uv run python3 scripts/run_phase.py --phase 02c --workers 2
```

**出力ファイル:** `outputs/02c_PARTIAL_*.json`, `outputs/01b_SUBGRAPH_INDEX.json`

**確認項目:**

| # | 確認内容 | 方法 |
|---|---------|------|
| 1 | `TARGET_INFO.json` にターゲット情報がある | `target_repo`, `target_ref` を目視確認 |
| 2 | PARTIAL ファイルが生成されている | `ls outputs/02c_PARTIAL_*.json` |
| 3 | `01b_SUBGRAPH_INDEX.json` が生成されている | `ls outputs/01b_SUBGRAPH_INDEX.json` |
| 4 | `code_scope` にファイルパスがある | 各アイテムの `code_scope.file_path` を確認 |
| 5 | `Informational` のプロパティが除外されている | 出力に含まれないこと |

---

### Phase 03: 証明ベースフォーマル監査

Map -> Prove -> Stress-Test の 3 フェーズ統合監査。プロパティが成立することを証明し、証明のギャップを脆弱性として報告する。ツール: Read/Write/Grep/Glob のみ（MCP 不使用）。

**実行:**
```bash
uv run python3 scripts/run_phase.py --phase 03 --workers 4 --max-concurrent 64
```

**出力ファイル:** `outputs/03_PARTIAL_*.json`

**確認項目:**

| # | 確認内容 | 方法 |
|---|---------|------|
| 1 | PARTIAL ファイルが生成されている | `ls outputs/03_PARTIAL_*.json` |
| 2 | `classification` が適切 | `vulnerable` / `safe` / `inconclusive` / `out-of-scope` |
| 3 | 脆弱性にコード参照がある | `vulnerable` なアイテムにファイルパスと行番号があること |
| 4 | サーキットブレーカーが発動していない | ログに `CircuitBreaker` エラーがないこと |

```bash
# 監査結果の統計
uv run python3 -c "
import json, glob, collections
counts = collections.Counter()
for f in glob.glob('outputs/03_PARTIAL_*.json'):
    data = json.load(open(f))
    items = data.get('audit_items', data.get('items', []))
    for item in items:
        counts[item.get('classification', 'unknown')] += 1
for k, v in counts.most_common():
    print(f'  {k}: {v}')
print(f'  Total: {sum(counts.values())}')
"
```

---

### Phase 04: レビュー（3 ゲート FP フィルタ）

Dead Code -> Trust Boundary -> Scope Check の 3 ゲートで偽陽性をフィルタリング（recall-safe 設計）。ツール: Read/Write/Grep/Glob のみ（MCP 不使用）。

**実行:**
```bash
uv run python3 scripts/run_phase.py --phase 04 --workers 2
```

**出力ファイル:** `outputs/04_PARTIAL_*.json`

**確認項目:**

| # | 確認内容 | 方法 |
|---|---------|------|
| 1 | PARTIAL ファイルが生成されている | `ls outputs/04_PARTIAL_*.json` |
| 2 | verdict が付与されている | 下記 6 カテゴリのいずれか |
| 3 | Confirmed 脆弱性の根拠が明確 | 目視で判定理由を確認 |

**verdict 一覧:** `CONFIRMED_VULNERABILITY`, `CONFIRMED_POTENTIAL`, `DISPUTED_FP`, `DOWNGRADED`, `NEEDS_MANUAL_REVIEW`, `PASS_THROUGH`

```bash
# レビュー結果のサマリ
uv run python3 -c "
import json, glob, collections
verdicts = collections.Counter()
for f in glob.glob('outputs/04_PARTIAL_*.json'):
    data = json.load(open(f))
    items = data.get('reviewed_items', data.get('items', []))
    for item in items:
        verdicts[item.get('verdict', 'unknown')] += 1
for k, v in verdicts.most_common():
    print(f'  {k}: {v}')
print(f'  Total: {sum(verdicts.values())}')
"
```

---

## 4. 出力ファイルの検証方法

### 4.1 JSON バリデーション（全フェーズ共通）

```bash
for f in outputs/*PARTIAL*.json; do
  python3 -m json.tool "$f" > /dev/null 2>&1 && echo "OK: $f" || echo "INVALID: $f"
done
```

### 4.2 Pydantic スキーマ検証

```bash
uv run python3 -m pytest tests/test_schemas_and_config.py -v --tb=short
```

### 4.3 フェーズ間の ID 整合性チェック

```bash
uv run python3 -c "
import json, glob

# Phase 01e -> 02c の property_id リンク確認
prop_ids = set()
for f in glob.glob('outputs/01e_PARTIAL_*.json'):
    data = json.load(open(f))
    for item in data.get('properties', data.get('items', [])):
        prop_ids.add(item.get('property_id', ''))

code_refs = set()
for f in glob.glob('outputs/02c_PARTIAL_*.json'):
    data = json.load(open(f))
    for item in data.get('items', []):
        code_refs.add(item.get('property_id', ''))

orphans = code_refs - prop_ids
if orphans:
    print(f'WARNING: {len(orphans)} items in 02c reference unknown property_ids')
else:
    print('OK: All property_id references are valid')
"
```

### 4.4 ログの確認

```bash
# 直近のログを確認
ls -lt outputs/logs/ | head -20

# エラーが含まれるログを検索
grep -l '"error"' outputs/logs/*.jsonl 2>/dev/null || echo "No errors found"

# サーキットブレーカーの発動を確認
grep -l 'circuit_breaker\|CircuitBreaker' outputs/logs/*.jsonl 2>/dev/null || echo "No circuit breaker events"
```

---

## 5. 手動フェーズ（05・06・06b）

これらは Claude Code CLI で対話的に実行する。オーケストレータは使用しない。

### Phase 05: PoC 生成

```bash
claude
# Claude Code 内で prompts/05_poc.md の手順に従い PoC を生成
```

**確認ポイント:** PoC コードがビルド・実行可能であること、再現手順が明確であること。

### Phase 06: バグバウンティレポート

```bash
claude
# Claude Code 内で prompts/06_report.md に従い実行
```

**確認ポイント:** 深刻度の根拠が明記されていること、再現手順が第三者に理解可能であること。

### Phase 06b: 完全監査レポート

```bash
claude
# Claude Code 内で prompts/06b_audit_report.md に従い実行
```

**確認ポイント:** すべての Confirmed 脆弱性が記載されていること、内部 ID がサニタイズされていること。

---

## 6. トラブルシューティング

### 6.1 よくある問題

| 症状 | 原因 | 対処 |
|------|------|------|
| `Missing input: outputs/01a_STATE.json` | 前段フェーズ未実行 | 依存フェーズを先に実行する |
| `BUG_BOUNTY_SCOPE.json` 未配置で 01e が異常終了 | 必須ファイル未配置 | `outputs/BUG_BOUNTY_SCOPE.json` を配置する |
| `TARGET_INFO.json` 未配置で 02c が失敗 | CI ワークフロー未実行 | `outputs/TARGET_INFO.json` を手動作成する |
| `CircuitBreaker tripped` | 連続バッチ失敗 | ログを確認し、プロンプトや MCP の問題を修正 |
| `BudgetExceeded` | フェーズ予算超過 | `config.py` の `max_budget_usd` を確認 |
| MCP サーバー接続エラー | サーバー未登録/起動失敗 | `bash scripts/setup_mcp.sh --verify` で確認 |
| 空の PARTIAL ファイル | LLM が結果を返さなかった | `--force` で再実行 or バッチサイズを減らす |

### 6.2 レジューム（中断からの再開）

```bash
# 前回の途中から再開（デフォルト動作）
uv run python3 scripts/run_phase.py --phase 03 --workers 4

# 完了済みアイテムを無視して全件再実行
uv run python3 scripts/run_phase.py --phase 03 --force --workers 4
```

### 6.3 不完全バッチのクリーンアップ

```bash
# ドライラン（削除されるファイルを確認のみ）
uv run python3 scripts/run_phase.py --phase 03 --cleanup-dry-run
```

### 6.4 全フェーズ一括実行

```bash
# 依存チェーンを自動解決して Phase 04 まで実行
uv run python3 scripts/run_phase.py --target 04 --workers 4
```

---

## チェックリスト: 全フェーズ完了確認

```
[ ] 環境セットアップ完了（Python, uv, Node.js, Claude CLI, MCP）
[ ] Pre-flight テスト全件 PASSED
[ ] Phase 01a: outputs/01a_STATE.json 生成・仕様書 URL 確認
[ ] Phase 01b: outputs/graphs/ にグラフ + .mmd ファイル生成確認
[ ] Phase 01e: プロパティ生成確認（covers=文字列, reachability=4フィールド）
[ ] Phase 02c: コード位置解決・TARGET_INFO・SUBGRAPH_INDEX 確認
[ ] Phase 03:  証明ベース監査完了・分類結果確認
[ ] Phase 04:  3ゲートレビュー verdict 付与・最終判定確認
[ ] フェーズ間 ID 整合性チェック OK
[ ] ログにサーキットブレーカー/予算超過エラーなし
```
