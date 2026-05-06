# SPECA Codex 版

SPECA は、自然言語の仕様書からセキュリティ性質を抽出し、その性質を実装コードに対して検証する監査パイプラインです。

この変更版では、元の Claude Code 向けワークフローを残したまま、Codex App から SPECA API と `codex app-server` worker を使えるようにしています。CLI や既存 CI では従来の Claude runner を明示的に使えます。

このリポジトリは [NyxFoundation/speca](https://github.com/NyxFoundation/speca) を元にした Codex App 対応版です。MIT ライセンスと元リポジトリの著作権表示は維持しています。

元リポジトリの論文・ベンチマーク結果は上流 SPECA の実績として参照してください。この Codex 版は worker runtime を変更しているため、Codex で実行した監査が上流の Claude 実行結果をそのまま再現するとは主張しません。

このリポジトリは SPECA を Codex App で使うための非公式 fork です。上流の研究実装とは目的が異なるため、上流 main への追従は保証しません。最新の上流実装が必要な場合は [NyxFoundation/speca](https://github.com/NyxFoundation/speca) を参照してください。

英語の概要は [README.md](README.md)、Codex App 連携の詳細は [docs/CODEX_APP.ja.md](docs/CODEX_APP.ja.md) を見てください。

## Authorized Use

SPECA は防御的な監査と研究のためのツールです。自分が所有・管理しているリポジトリ、または bug bounty / 契約 / 明示的な許可により監査権限がある対象にだけ使ってください。許可のない第三者システムの探索、攻撃、悪用、認証回避、サービス妨害には使わないでください。`BUG_BOUNTY_SCOPE.json` と `TARGET_INFO.json` は、その run で許可された範囲を明確にするためにも使います。

## 重要な方針

- Codex App から dispatch した run は、既定で `CodexAppRunner` を使います。
- SPECA は scheduler として、phase 順序、batch 分割、resume、partial result 回収を担当します。
- Codex app-server は、長い監査 turn、並列 thread、進捗通知、turn diff の回収を担当します。
- CLI は互換性のため、runner 未指定なら従来の Claude runner を使います。
- `sonnet`、`opus`、`haiku` などの Claude モデル名は Codex runner には渡しません。Codex App から dispatch した run は、`model` 未指定なら現在の GUI 選択モデルと推論強度を session metadata から自動解決します。
- 同時に複数 run を動かす場合は、run ごとに必ず別の `output_dir` を指定します。
- `outputs/*_PARTIAL_*.json` は resume 用の状態ファイルです。削除や再利用には注意してください。

## 必要なもの

- Python 3.11+
- `uv`
- Node.js 20+
- Codex CLI か Codex desktop app 同梱の CLI
- git
- 既存の Claude runner を使う場合のみ Claude Code CLI

Codex CLI を npm で入れる場合:

```bash
npm install -g @openai/codex
```

`uv` が未インストールなら:

```bash
pip install uv
```

## セットアップ

GitHub の緑色の **Code** ボタンから、この公開リポジトリの clone URL をコピーして使います。

```bash
git clone <this-repository-url>
cd <repository-directory>
uv sync
```

Windows で既存 workflow 用の `sweagent` checkout に失敗する場合は、Codex App の SPECA API とテストに必要な軽量 venv だけを作れます。

```bash
uv venv
uv pip install --python .venv/Scripts/python.exe pytest fastapi pydantic httpx aiofiles tqdm "uvicorn[standard]"
```

## Codex App での使い方

この版の主な使い方は **CLI を直接叩くことではなく、Codex App 上で Codex に SPECA run を管理させること**です。人間は Codex に依頼し、Codex が `.codex/launch.json` の `speca-api` 起動、health check、phase dispatch、進捗監視、diff 回収を行います。下にある `curl` や CLI の例は、Codex が内部で実行する操作を明示したもの、または手動デバッグ用です。

最初の smoke test は Codex にこう依頼します。

```text
このリポジトリで SPECA API を起動して health check して。
Codex App runner で 01a smoke test を実行して、進捗を監視し、
完了後に outputs/smoke_01a/01a_STATE.json の要約を教えて。
seed URL は https://github.com/ethereum/EIPs/blob/master/EIPS/eip-7594.md
output_dir は outputs/smoke_01a にして。
```

本番に近い監査では、必要な入力ファイルを用意してからこう依頼します。

```text
outputs/BUG_BOUNTY_SCOPE.json と outputs/TARGET_INFO.json がある前提で、
Codex App runner を使って SPECA を 04 まで実行して。
isolated_worktrees を有効にし、output_dir は outputs/audit_<target-name>、
workers=4、max_concurrent=8 にして。
進捗、失敗batch、Codex app-server thread metadata、diff/reducer結果、
最終出力の場所をまとめて報告して。
```

複数対象を並列に見る場合はこう依頼します。

```text
2つの SPECA run を別々の output_dir で並列 dispatch して。
同じ output_dir を使わないことを確認し、各 run の進捗、失敗batch、
diff metadata、最終 partial/result を比較してまとめて。
```

Codex App のモデル選択ドロップダウンで選んだモデルと推論強度は、API dispatch 時に SPECA backend が session metadata から自動解決します。速度を明示したい場合だけ `service_tier: "fast"` のように依頼してください。

## Codex App から SPECA API を起動する

Codex App では [.codex/launch.json](.codex/launch.json) の `speca-api` を起動します。手動で起動する場合:

```bash
.venv/Scripts/python.exe -m uvicorn server.app:app --host 127.0.0.1 --port 8000
```

確認:

```bash
curl http://127.0.0.1:8000/api/health
```

期待される応答:

```json
{"status":"ok"}
```

`--reload` は API 開発時だけ使ってください。Codex App の smoke や長時間 run では、古い reloader 子プロセスが残らないように単一プロセス起動を推奨します。

## 最初の smoke test

最初は前段成果物が不要な `01a` を使います。これは seed URL から仕様書候補を集め、`outputs/smoke_01a/01a_STATE.json` を作る軽い確認です。

```bash
curl -X POST http://127.0.0.1:8000/api/phases/dispatch \
  -H "content-type: application/json" \
  -d '{"phase_id":"01a","workers":1,"max_concurrent":1,"spec_urls":"https://github.com/ethereum/EIPs/blob/master/EIPS/eip-7594.md","output_dir":"outputs/smoke_01a"}'
```

返ってきた `run_id` で進捗を見ます。

```bash
curl -N http://127.0.0.1:8000/api/runs/<run_id>/progress
```

完了後に結果を確認します。

```bash
cat outputs/smoke_01a/01a_STATE.json
```

PowerShell では:

```powershell
Get-Content outputs\smoke_01a\01a_STATE.json
```

## 本番監査の流れ

SPECA の phase は前段の出力を次段が読む構成です。`03` や `04` だけをいきなり実行するには、対応する `outputs/*.json` が既に必要です。

| 順序 | Phase | 役割 | 主な入力 |
|---|---|---|---|
| 1 | `01a` | 仕様URLの探索 | `spec_urls` |
| 2 | `01b` | 仕様subgraph抽出 | `01a_STATE.json` |
| 3 | `01e` | security property生成 | `BUG_BOUNTY_SCOPE.json` |
| 4 | `02c` | propertyとコード位置の対応付け | `TARGET_INFO.json` |
| 5 | `03` | property-grounded audit | `02c` までの出力 |
| 6 | `04` | false positive filter / severity調整 | `03` の出力 |

CLI で前段から `04` まで順に実行する場合:

```bash
uv run python scripts/run_phase.py --target 04 --runner codex-app --workers 4 --max-concurrent 8
```

API から実行する場合は、各 phase を順番に dispatch します。長い run や source 差分がありうる run では `isolated_worktrees` を有効にしてください。

## 並列 run

複数の run を同時に動かす場合は、必ず別の `output_dir` を指定します。

```bash
curl -X POST http://127.0.0.1:8000/api/phases/dispatch \
  -H "content-type: application/json" \
  -d '{"phase_id":"02c","workers":2,"max_concurrent":4,"output_dir":"outputs/inst_01"}'

curl -X POST http://127.0.0.1:8000/api/phases/dispatch \
  -H "content-type: application/json" \
  -d '{"phase_id":"02c","workers":2,"max_concurrent":4,"output_dir":"outputs/inst_02"}'
```

同じ `output_dir` に active run がある場合、server は `409 Conflict` を返します。partial、queue/context、log、debug file の衝突を防ぐためです。

## Isolated Worktrees

worker ごとに git worktree を分ける場合:

```bash
curl -X POST http://127.0.0.1:8000/api/phases/dispatch \
  -H "content-type: application/json" \
  -d '{"phase_id":"03","workers":4,"isolated_worktrees":true,"output_dir":"outputs/inst_01"}'
```

既定では `.codex/worktrees/` の下に作成されます。このディレクトリは git 管理対象外です。worktree で発生した差分と Codex app-server thread metadata は以下で確認できます。

```bash
curl http://127.0.0.1:8000/api/runs/<run_id>/diffs
curl "http://127.0.0.1:8000/api/runs/<run_id>/diffs?include_content=true"
```

## CLI で使う場合

既存 CLI は互換性のため、runner 未指定では従来の Claude runner を使います。Codex app-server runner を CLI から使う場合は明示します。

```bash
SPEC_URLS="https://github.com/ethereum/EIPs/blob/master/EIPS/eip-7594.md" \
  uv run python scripts/run_phase.py --phase 01a --runner codex-app
```

`codex exec` fallback を使う場合:

```bash
SPEC_URLS="https://github.com/ethereum/EIPs/blob/master/EIPS/eip-7594.md" \
  uv run python scripts/run_phase.py --phase 01a --runner codex
```

既存 Claude workflow を使う場合:

```bash
SPEC_URLS="https://github.com/ethereum/EIPs/blob/master/EIPS/eip-7594.md" \
  uv run python scripts/run_phase.py --phase 01a --runner claude
```

Codex モデルを明示したい場合だけ指定します。Codex App API dispatch では、`model` 未指定なら現在の GUI 選択モデルと推論強度を自動解決します。速度は app-server の `serviceTier` に対応しており、`service_tier: "fast"` のように API から明示できます。CLI では `--model` または `SPECA_CODEX_MODEL` で指定できます。

```bash
SPEC_URLS="https://github.com/ethereum/EIPs/blob/master/EIPS/eip-7594.md" \
  uv run python scripts/run_phase.py --phase 01a --runner codex-app --model <CODEX_MODEL>
```

## 主なファイル

- [scripts/orchestrator/codex_app_runner.py](scripts/orchestrator/codex_app_runner.py): `codex app-server` protocol runner
- [scripts/orchestrator/codex_runner.py](scripts/orchestrator/codex_runner.py): `codex exec` fallback runner
- [scripts/orchestrator/codex_adapter.py](scripts/orchestrator/codex_adapter.py): Claude slash skill 参照を Codex worker prompt に取り込む adapter
- [server/](server): Codex App から使う FastAPI server
- [scripts/orchestrator/paths.py](scripts/orchestrator/paths.py): run ごとの output root 解決
- [docs/CODEX_APP.ja.md](docs/CODEX_APP.ja.md): Codex App 連携の詳細
- [LICENSE](LICENSE): MIT License

## ライセンス

この repository は MIT License です。公開、改変、再配布する場合も [LICENSE](LICENSE) を保持してください。

著作権表示:

```text
Copyright (c) 2026 Nyx Foundation and SPECA contributors
```

この表示と MIT License 本文を配布物に含める必要があります。
