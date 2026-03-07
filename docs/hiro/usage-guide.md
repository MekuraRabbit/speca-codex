# SPECA 監査パイプライン 操作ガイド

このドキュメントは Claude に渡して監査を実行させるための指示書です。
新しい Claude セッションでこのファイルを読み込み、対象のコンテスト URL を貼ってください。

---

## あなたの役割

あなたは SPECA セキュリティ監査パイプラインのオペレーターです。
ユーザーから監査対象の URL (Sherlock, Code4rena, Immunefi 等) を受け取り、
以下の手順でパイプラインを実行してください。

## 前提条件

- 作業ディレクトリ: このリポジトリのルート
- Python 環境: `uv` が利用可能
- Claude CLI: `claude` コマンドが認証済み (`claude auth status` で確認)

## 実行手順

### Step 1: 対象の分析

ユーザーが貼った URL からコンテスト情報を取得します。

```
対象 URL を WebFetch で取得し、以下を特定:
- プロジェクト名
- 対象リポジトリ (GitHub URL)
- スコープ (対象コントラクト/ファイル)
- 技術スタック (Solidity, Rust, Go 等)
```

### Step 2: キーワードと仕様 URL の決定

Phase 01a に渡す入力を決めます。

```
キーワード例: "プロジェクト名,プロトコル種別,主要機能キーワード"
仕様URL例: "https://docs.project.xyz/,https://github.com/org/repo/tree/main/docs"
```

### Step 3: Phase 01a -- 仕様探索

```bash
KEYWORDS="決めたキーワード" SPEC_URLS="決めたURL" uv run python3 scripts/run_phase.py --phase 01a
```

出力: `outputs/01a_STATE.json`

### Step 4: Phase 01b -- サブグラフ抽出

```bash
uv run python3 scripts/run_phase.py --phase 01b --workers 4
```

出力: `outputs/01b_PARTIAL_*.json` + `outputs/subgraphs/*.mmd`

### Step 5: Phase 01e -- プロパティ生成

**事前準備**: `outputs/BUG_BOUNTY_SCOPE.json` が必要です。

```bash
# BUG_BOUNTY_SCOPE.json を作成 (対象のスコープ情報)
cat > outputs/BUG_BOUNTY_SCOPE.json << 'EOF'
{
  "program_name": "プロジェクト名",
  "platform": "sherlock",
  "scope": {
    "in_scope": ["対象コントラクト/ファイルのリスト"],
    "out_of_scope": ["除外対象"]
  },
  "severity_levels": ["Critical", "High", "Medium", "Low"],
  "reward_range": "報酬レンジ"
}
EOF

uv run python3 scripts/run_phase.py --phase 01e --workers 4
```

出力: `outputs/01e_PARTIAL_*.json`

### Step 6: Phase 02c -- コード解決

**事前準備**: `outputs/TARGET_INFO.json` が必要です。

```bash
# TARGET_INFO.json を作成
cat > outputs/TARGET_INFO.json << 'EOF'
{
  "repository": "org/repo",
  "commit": "コミットハッシュ or ブランチ",
  "local_path": "/path/to/cloned/repo"
}
EOF

uv run python3 scripts/run_phase.py --phase 02c --workers 4
```

出力: `outputs/02c_PARTIAL_*.json`

### Step 7: Phase 03 -- 監査マップ

```bash
uv run python3 scripts/run_phase.py --phase 03 --workers 4 --max-concurrent 64
```

出力: `outputs/03_PARTIAL_*.json`

### Step 8: Phase 04 -- レビュー (FP フィルタ)

```bash
uv run python3 scripts/run_phase.py --phase 04 --workers 4
```

出力: `outputs/04_PARTIAL_*.json`

### Step 9: 結果確認

```bash
# 結果サマリーを確認
python3 -c "
import json, glob
findings = []
for f in glob.glob('outputs/04_PARTIAL_*.json'):
    findings.extend(json.load(open(f)))
confirmed = [f for f in findings if f.get('verdict') in ('CONFIRMED_VULNERABILITY', 'CONFIRMED_POTENTIAL')]
print(f'Total: {len(findings)}, Confirmed: {len(confirmed)}')
for f in confirmed:
    print(f'  [{f.get(\"severity\",\"?\")}] {f.get(\"title\",\"untitled\")}')
"
```

---

## WEB UI 経由での実行

CLI の代わりに Web UI を使う場合:

```bash
# バックエンドとフロントエンドを同時起動
uv run uvicorn server.app:app --port 8000 &
cd web && npm run dev &

# ブラウザで http://localhost:5173/audit を開く
```

Web UI ではフェーズを選択して実行ボタンを押すだけです。
リアルタイムで進捗が表示されます。

---

## 一括実行 (全フェーズ)

依存関係を自動解決して Phase 04 まで一気に実行:

```bash
uv run python3 scripts/run_phase.py --target 04 --workers 4
```

途中で失敗した場合、同じコマンドで再開できます (resume 機能)。
強制再実行する場合は `--force` を付けてください。

---

## トラブルシューティング

| 問題 | 対処 |
|------|------|
| `BUG_BOUNTY_SCOPE.json が見つかりません` | Step 5 の事前準備を実行 |
| `TARGET_INFO.json が見つかりません` | Step 6 の事前準備を実行 |
| Claude CLI が exit code 1 | `claude auth status` で認証確認 |
| バッチが全て失敗 | Circuit breaker — プロンプトか API の問題を確認 |
| Budget exceeded | `scripts/orchestrator/config.py` の `max_budget_usd` を調整 |

---

## 注意事項

- Phase 03 は最もコストが高い (1回 $50-200)
- Phase 01a は append モードで既存 STATE に追記可能
- `--force` を使うと resume 状態がクリアされ全て再実行される
- 結果は Discord に自動通知されます
