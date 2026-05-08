# Codex App 連携

この文書は、SPECA を Codex App から実行するための日本語ガイドです。目的は、SPECA の既存ワークフローを壊さず、実際の worker 作業を Codex で実行できるようにすることです。

英語版は [CODEX_APP.md](CODEX_APP.md) です。

## 構成

```text
Codex App
  -> SPECA FastAPI server
    -> SPECA scheduler
      -> CodexAppRunner
        -> codex app-server thread/turn
          -> optional isolated git worktree
      -> partial result / progress / diff reducer
```

SPECA は phase 順序、依存関係、batch 分割、resume、partial result 保存を担当します。Codex app-server は長い turn、並列 thread、進捗通知、turn diff、thread metadata を担当します。

## Authorized Use

SPECA は、自分が所有・管理しているリポジトリ、または bug bounty / 契約 / 明示的な許可により監査権限がある対象にだけ使ってください。Codex に依頼するときも、`BUG_BOUNTY_SCOPE.json` と `TARGET_INFO.json` で許可された範囲を明確にし、無関係なリポジトリ、実サービス、アカウント、インフラへ範囲を広げないでください。

## Codex への頼み方

Codex App 上では、人間が `curl` や CLI を直接覚える必要はありません。Codex に「SPECA API を起動して、phase を dispatch し、進捗と成果物を確認して」と頼むのが主導線です。

最初の確認:

```text
このリポジトリで SPECA API を起動して health check して。
Codex App runner で 01a smoke test を実行し、進捗を監視して。
seed URL は https://github.com/ethereum/EIPs/blob/master/EIPS/eip-7594.md、
output_dir は outputs/smoke_01a にして。
完了後に 01a_STATE.json を要約して。
```

本番寄りの監査:

```text
outputs/BUG_BOUNTY_SCOPE.json と outputs/TARGET_INFO.json がある前提で、
Codex App runner + isolated_worktrees で SPECA を 04 まで実行して。
output_dir は outputs/audit_<target-name>、workers=4、max_concurrent=8。
進捗、失敗batch、thread metadata、diff/reducer結果、最終出力を報告して。
```

以下の `curl` 例は、Codex が内部で実行する API 操作を手動でも確認できるようにしたものです。

dispatch API は、request field から target repository を clone したり audit scope
を作ったりしません。target-code phase の前に `outputs/TARGET_INFO.json` と
`outputs/BUG_BOUNTY_SCOPE.json` を用意してください。実際の setup endpoint が
できるまでは、`target_repo`、`target_ref_type`、`audit_scope` は拒否されます。

## SPECA API の起動

Codex App では [.codex/launch.json](../.codex/launch.json) の `speca-api` を起動します。手動で起動する場合:

```bash
uv run --no-sync python -m server.app
```

`--no-sync` を使うので、既存の軽量 `.venv` を使い、legacy workflow
dependency の full sync を強制しません。

軽量 venv を直接呼びたい場合:

```bash
.venv/Scripts/python.exe -m server.app
```

```bash
.venv/bin/python -m server.app
```

> **この API を公開しないでください。** SPECA API は agent worker run を
> 起動できるローカル単一ユーザー向けの制御面です。認証はありません。
> `127.0.0.1`、`localhost`、`::1` の loopback にだけ bind してください。
> 非 loopback host への bind は、明示的に確認したローカル環境で
> `SPECA_ENABLE_REMOTE_API=1` を設定した場合だけ許可されます。

health check:

```bash
curl http://127.0.0.1:8000/api/health
```

`--reload` は API 開発時だけ使ってください。Codex App の smoke や長時間 worker run では、古い reloader 子プロセスが残らないように単一プロセス起動を推奨します。

## Smoke phase の dispatch

前段成果物が不要な `01a` で接続確認します。`03` や `04` は前段の `outputs/*.json` が必要です。

```bash
curl -X POST http://127.0.0.1:8000/api/phases/dispatch \
  -H "content-type: application/json" \
  -d '{"phase_id":"01a","workers":1,"max_concurrent":1,"spec_urls":"https://github.com/ethereum/EIPs/blob/master/EIPS/eip-7594.md","output_dir":"outputs/smoke_01a"}'
```

返ってきた `run_id` で進捗を SSE で見ます。

```bash
curl -N http://127.0.0.1:8000/api/runs/<run_id>/progress
```

app server は軽量な run index を `<output_dir>/RUN_INFO.json` に保存します。
再起動後の `/api/runs/` は `outputs/**/RUN_INFO.json` から記録を読み直します。
再起動時点で `queued` または `running` だった run は、worker process が残っていないため
`failed` として扱われます。

## Runner 選択

Codex App server の既定:

```json
{
  "phase_id": "01a",
  "spec_urls": "https://github.com/ethereum/EIPs/blob/master/EIPS/eip-7594.md",
  "output_dir": "outputs/smoke_01a"
}
```

この場合は `CodexAppRunner` が使われ、worker batch ごとに Codex app-server thread が作られます。外部の Codex app-server websocket を使う場合:

```json
{
  "phase_id": "01a",
  "runner": "codex-app",
  "app_server_url": "ws://127.0.0.1:8765",
  "spec_urls": "https://github.com/ethereum/EIPs/blob/master/EIPS/eip-7594.md",
  "output_dir": "outputs/smoke_01a"
}
```

`PhaseConfig` や `CLAUDE.md` に残っている `sonnet`、`opus`、`haiku`、Claude の完全なモデル名は Claude runner 用の互換設定です。Codex runner はそれらを Codex へ渡しません。Codex App から起動された API run で `model` を省略した場合、SPECA は現在の `CODEX_THREAD_ID` に対応する Codex session metadata から最新の `turn_context` を読み、GUI で選ばれているモデルと推論強度を app-server turn に渡します。この場合 metadata には `model_source: "codex-gui"` や `effort_source: "codex-gui"` が残ります。

Codex App protocol は app-server turn の `serviceTier` (`fast` / `flex`) も受け付けます。SPECA は将来 session metadata に速度設定が記録されていればそれも渡します。現在の標準速度は独立した値として保存されていないため、SPECA では app-server の既定値として扱います。

```json
{
  "phase_id": "03",
  "model": "<CODEX_MODEL>",
  "output_dir": "outputs/inst_01"
}
```

GUI 選択モデルを使わず、app-server 側の既定モデルに任せたい場合:

```json
{
  "phase_id": "03",
  "use_codex_gui_model": false,
  "output_dir": "outputs/inst_01"
}
```

推論強度や速度を明示したい場合:

```json
{
  "phase_id": "03",
  "reasoning_effort": "xhigh",
  "service_tier": "fast",
  "output_dir": "outputs/inst_01"
}
```

古い Claude workflow を明示的に使う場合:

```json
{
  "phase_id": "03",
  "runner": "claude",
  "output_dir": "outputs/inst_01"
}
```

`codex exec` fallback を使う場合:

```json
{
  "phase_id": "03",
  "runner": "codex",
  "output_dir": "outputs/inst_01"
}
```

CLI から Codex app-server runner を使う場合:

```bash
SPEC_URLS="https://github.com/ethereum/EIPs/blob/master/EIPS/eip-7594.md" \
  uv run python scripts/run_phase.py --phase 01a --runner codex-app
```

## 並列 run

並列実行では、run ごとに別の `output_dir` を指定します。

```bash
curl -X POST http://127.0.0.1:8000/api/phases/dispatch \
  -H "content-type: application/json" \
  -d '{"phase_id":"02c","workers":2,"max_concurrent":4,"output_dir":"outputs/inst_01"}'

curl -X POST http://127.0.0.1:8000/api/phases/dispatch \
  -H "content-type: application/json" \
  -d '{"phase_id":"02c","workers":2,"max_concurrent":4,"output_dir":"outputs/inst_02"}'
```

同じ `output_dir` に active run がある場合、server は `409 Conflict` を返します。これにより、partial、queue/context、log、MCP config、debug file の衝突を避けます。

## Isolated Worktrees

長い調査 turn や並列 thread で source 差分が発生しうる場合は、worker ごとに git worktree を分けます。

```json
{
  "phase_id": "03",
  "workers": 4,
  "isolated_worktrees": true,
  "output_dir": "outputs/inst_01"
}
```

既定では `.codex/worktrees/` の下に作成されます。別の場所を使う場合:

```json
{
  "phase_id": "03",
  "isolated_worktrees": true,
  "worktree_root": "E:/tmp/speca-worktrees",
  "worktree_base_ref": "HEAD",
  "output_dir": "outputs/inst_01"
}
```

SPECA の出力 artifact は、prompt 内で指定された絶対 path の `output_dir` に書かれます。worker の cwd が isolated worktree でも、scheduler の出力場所は混ざりません。

## Diff 回収

`CodexAppRunner` は thread id と turn id を `<output_dir>/codex_app_threads/` に保存します。source diff は isolated worktree run のときだけ回収します。非 isolated run では、手元の未コミット差分を run metadata に巻き込まないように workspace diff を抑制します。

API から見る場合:

```bash
curl http://127.0.0.1:8000/api/runs/<run_id>/diffs
curl "http://127.0.0.1:8000/api/runs/<run_id>/diffs?include_content=true"
```

これは reducer agent を置くための入口です。現状は SPECA の既存 `ResultCollector` が partial result を統合し、diff metadata は別経路で回収します。

## N 並列 instance の考え方

共有 phase を先に一度だけ実行します。

```bash
uv run python scripts/run_phase.py --phase 01a 01b 01e --workers 4 --runner codex-app
```

その後、後段 phase 用に instance directory を分けます。

```bash
mkdir -p outputs/inst_01 outputs/inst_02
```

各 instance directory には、対象 phase が必要とする共有入力を置きます。例:

- `01a_STATE.json`
- `01b_PARTIAL_*.json`
- `01e_PARTIAL_*.json`
- `BUG_BOUNTY_SCOPE.json`
- `TARGET_INFO.json`
- `graphs/`

## 実装メモ

- `scripts/orchestrator/codex_app_runner.py` は `codex app-server` protocol runner です。
- `scripts/orchestrator/codex_runner.py` は `codex exec` fallback runner です。
- `scripts/orchestrator/codex_adapter.py` は、prompt が `.claude/skills/*/SKILL.md` を参照している場合に、その内容を Codex worker prompt へ取り込みます。Codex は Claude slash skill を直接実行しません。
- `server/run_manager.py` は、異なる `output_dir` の active run を並列に許可します。
- `scripts/orchestrator/paths.py` は、app server 内で task-local な output root を扱います。
- `get_phase_config()` は `PhaseConfig` の copy を返すため、run ごとの上書きが別 run に漏れません。
- Discord 通知は任意です。使う場合は server 環境変数 `SPECA_DISCORD_WEBHOOK_URL` に webhook URL を設定します。repository には webhook URL を保存しません。

## 公開時の注意

この repository は MIT License です。改変版を公開する場合も、[../LICENSE](../LICENSE) を保持してください。

`ClaudeRunner` と `.claude/` は互換性のため残っていますが、Codex App server の通常経路では `CodexAppRunner` が使われます。
