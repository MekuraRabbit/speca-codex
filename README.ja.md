# SPECA Codex 版

SPECA は、自然言語の仕様書からセキュリティ性質を抽出し、その性質を実装コードに対して検証する監査パイプラインです。

この変更版では、SPECA を Codex App から実行できるようにし、SPECA API と `codex app-server` worker を主導線にしています。元の Claude Code workflow を使いたい場合は、上流の [NyxFoundation/speca](https://github.com/NyxFoundation/speca) を使ってください。

このリポジトリは [NyxFoundation/speca](https://github.com/NyxFoundation/speca) を元にした Codex App 対応版です。MIT ライセンスと元リポジトリの著作権表示は維持しています。

元リポジトリの論文・ベンチマーク結果は上流 SPECA の実績として参照してください。この Codex 版は worker runtime を変更しているため、Codex で実行した監査が上流の Claude 実行結果をそのまま再現するとは主張しません。

このリポジトリは SPECA を Codex App で使うための非公式 fork です。NyxFoundation や元リポジトリの著者による公式配布物・推奨版ではありません。上流の研究実装とは目的が異なるため、上流 main への追従は保証しません。最新の上流実装が必要な場合は [NyxFoundation/speca](https://github.com/NyxFoundation/speca) を参照してください。

この fork では、上流のロゴ、論文用の生成済み図表、過去 run の出力、raw worker trace は同梱しません。必要な場合は上流リポジトリや論文を参照し、この Codex 版では自分が許可を持つ対象に対して新しく run を作成してください。

英語の概要は [README.md](README.md)、Codex App 連携の詳細は [docs/CODEX_APP.ja.md](docs/CODEX_APP.ja.md) を見てください。

## Authorized Use

SPECA は防御的な監査と研究のためのツールです。自分が所有・管理しているリポジトリ、または bug bounty / 契約 / 明示的な許可により監査権限がある対象にだけ使ってください。許可のない第三者システムの探索、攻撃、悪用、認証回避、サービス妨害には使わないでください。`BUG_BOUNTY_SCOPE.json` と `TARGET_INFO.json` は、その run で許可された範囲を明確にするためにも使います。

## 重要な方針

- Codex App から dispatch した run は、既定で `CodexAppRunner` を使います。
- SPECA は scheduler として、phase 順序、batch 分割、resume、partial result 回収を担当します。
- Codex app-server は、長い監査 turn、並列 thread、進捗通知、turn diff の回収を担当します。
- CLI から実行する場合も、この fork の公開導線では `--runner codex-app` または `--runner codex` を明示します。
- `sonnet`、`opus`、`haiku` などの Claude モデル名は Codex runner には渡しません。Codex App から dispatch した run は、`model` 未指定なら現在の GUI 選択モデルと推論強度を session metadata から自動解決します。
- Codex app-server worker thread は既定で ephemeral です。ローカルデバッグで永続化が必要な場合だけ `SPECA_CODEX_APP_EPHEMERAL_THREADS=0` を設定します。
- `scripts/setup_mcp.sh` が登録する MCP server package は既定で version pin しています。意図的に更新する場合だけ `MCP_*_SPEC` で上書きします。
- 同時に複数 run を動かす場合は、run ごとに必ず別の `output_dir` を指定します。
- `outputs/*_PARTIAL_*.json` は resume 用の状態ファイルです。削除や再利用には注意してください。
- 既定では schema validation の失敗は警告として扱い、partial result の保存と resume を優先します。CI や fixture run で厳密に検出したい場合は、`SPECA_STRICT_SCHEMA=1` を設定すると malformed partial を保存する前に失敗します。

## 必要なもの

- Python 3.11+
- `uv`
- Node.js 20+
- Codex CLI か Codex desktop app 同梱の CLI
- git

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
git clone https://github.com/MekuraRabbit/speca-codex
cd speca-codex
uv sync
```

通常の `uv sync` は、local API、orchestrator、Codex runner 経路、テストに
必要な依存だけを入れます。無効化済みの legacy resolver helper を触る場合だけ、
SWE-agent などの追加依存を入れてください。

このリポジトリは現時点では PyPI package として配布していません。clone した
checkout から `uv` で実行してください。

```bash
uv sync --group resolver
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
uv run --no-sync python -m server.app
```

`--no-sync` を使うので、既存の軽量 `.venv` を使い、任意の resolver extra
dependency の full sync を強制しません。platform ごとの venv interpreter
を直接呼ぶこともできます。

```bash
.venv/Scripts/python.exe -m server.app
```

```bash
.venv/bin/python -m server.app
```

> **この API を公開しないでください。** SPECA API は、agent worker run
> を起動できるローカル単一ユーザー向けの制御面です。認証はありません。
> `127.0.0.1`、`localhost`、`::1` の loopback にだけ bind してください。
> 非 loopback host への bind は、明示的に確認したローカル環境で
> `SPECA_ENABLE_REMOTE_API=1` を設定した場合だけ許可されます。

Codex worker turn は既定で `workspace-write` で動き、full filesystem access
は使いません。`01a`/`01b` は operator が指定した仕様 URL を取得するため、
sandbox 内の network access を既定で許可します。target code を読む後段 phase
では、明示的に上書きしない限り sandbox 内の network access は無効です。
`SPECA_CODEX_SANDBOX=danger-full-access` は、外側で sandbox され、権限範囲を
確認済みの trusted local run だけで使ってください。

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
| 7 | `05` | PoC代表候補の作成とPoC生成 | `04` の出力 |

CLI で前段から `04` まで順に実行する場合:

```bash
uv run python scripts/run_phase.py --target 04 --runner codex-app --workers 4 --max-concurrent 8
```

Phase `02c`、`03`、`04`、`05` の実行前に、SPECA は
`TARGET_INFO.local_checkout` が存在する Git repository root で、clean で、
`target_commit` と一致し、`origin` remote がある場合は `target_repo` と
一致することを検証します。信頼済みの legacy/local run だけ、
`SPECA_ALLOW_UNVERIFIED_TARGET_CHECKOUT=1` でこの事前検証を省略できます。

Phase 04 の confirmed / potential finding から、重複した根本原因をまとめた PoC 代表候補を作る場合:

```bash
uv run python scripts/run_phase.py --phase 05 --output-dir outputs/<run>
```

これにより `outputs/<run>/05_POC_CANDIDATES.json` が作られます。Phase 05 は、fee-on-transfer や要求量より少ない量しか届かない underlying token のような条件付き統合ハザードを、近接するシンボルごとではなく前提条件ごとにまとめます。Codex に PoC 生成を依頼する場合は、候補の `candidate_id` を指定して `prompts/05_poc.md` の形式で進めます。

API から実行する場合は、各 phase を順番に dispatch します。長い run や source 差分がありうる run では `isolated_worktrees` を有効にしてください。

## ローカル検証結果

この fork では、教育用に意図的な脆弱性を含む
[OpenZeppelin Damn Vulnerable DeFi](https://github.com/OpenZeppelin/damn-vulnerable-defi)
と、[OpenZeppelin Contracts](https://github.com/OpenZeppelin/openzeppelin-contracts)
の ERC-4626 周辺を対象に、Codex App runner 経由のローカル rehearsal を通しています。
これは Codex App 対応経路の互換性と品質を確認するための検証であり、実運用プロトコルの監査実績や未知の脆弱性発見を主張するものではありません。

2026 年 5 月のローカル rehearsal では:

- pinned local checkout に対して Phase 03/04 を完了し、入力 property 187 件すべてを accounted にしました。
- Phase 04 の confirmed / potential finding から、Phase 05 で 9 件の代表 PoC 候補を作成しました。
- 9 件すべての代表 PoC test を pinned target checkout 配下に手動実装し、ローカルで passing を確認しました。
- 許可した教育用ターゲット範囲内で完結し、外部 target fetch、RPC、registry、explorer、deployment、account infrastructure は不要でした。

再現メモは
[`docs/rehearsals/damn-vulnerable-defi-2026-05.md`](docs/rehearsals/damn-vulnerable-defi-2026-05.md)
にあります。

同じく 2026 年 5 月に、OpenZeppelin Contracts ERC-4626 `v5.6.1` を対象にした smoke rehearsal も行いました:

- ERC-4626 周辺の generated property 125 件について Phase 03/04 を完了しました。
- 元の Phase 05 candidate index では 6 件の PoC 候補が作られました。
- run 後のトリアージでは、それらを 2 つの根本原因ファミリーに整理しました。ひとつは最大値境界での standards-compliance edge case、もうひとつは short-delivering underlying asset に依存する条件付き統合ハザードです。
- 最大値境界のファミリーはローカル Hardhat PoC で再現しました。short-delivery 系は統合上の注意点として扱い、OpenZeppelin 本体の独立した脆弱性発見とは表現していません。

smoke rehearsal のメモは
[`docs/rehearsals/openzeppelin-erc4626-2026-05.md`](docs/rehearsals/openzeppelin-erc4626-2026-05.md)
にあります。

注意点:

- Damn Vulnerable DeFi は教育目的の intentionally vulnerable target です。この結果は任意の本番 repository に対する性能を示すものではありません。
- OpenZeppelin ERC-4626 の rehearsal はローカル smoke test であり、vendor-ready な監査レポートではありません。
- Phase 03 の finding 数は property 単位の信号であり、独立した脆弱性数ではありません。
- Phase 05 は PoC 候補の選択と構造化を行う段階です。現時点では exploit test の実装まで完全自動化するものではありません。

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

Codex app-server runner を CLI から使う場合は、`--runner codex-app` を明示します。

```bash
SPEC_URLS="https://github.com/ethereum/EIPs/blob/master/EIPS/eip-7594.md" \
  uv run python scripts/run_phase.py --phase 01a --runner codex-app
```

`codex exec` fallback を使う場合:

```bash
SPEC_URLS="https://github.com/ethereum/EIPs/blob/master/EIPS/eip-7594.md" \
  uv run python scripts/run_phase.py --phase 01a --runner codex
```

Codex モデルを明示したい場合だけ指定します。Codex App API dispatch では、`model` 未指定なら現在の GUI 選択モデルと推論強度を自動解決します。速度は app-server の `serviceTier` に対応しており、`service_tier: "fast"` のように API から明示できます。CLI では `--model` または `SPECA_CODEX_MODEL` で指定できます。

```bash
SPEC_URLS="https://github.com/ethereum/EIPs/blob/master/EIPS/eip-7594.md" \
  uv run python scripts/run_phase.py --phase 01a --runner codex-app --model <CODEX_MODEL>
```

Codex worker の sandbox mode は `SPECA_CODEX_SANDBOX` で上書きできます。
既定は `workspace-write` です。`danger-full-access` は、trusted local run
で外側の isolation を確認している場合だけ使ってください。
`SPECA_CODEX_SANDBOX_NETWORK` を設定すると sandbox 内 network access を
明示的に上書きできます。

## 主なファイル

- [scripts/orchestrator/codex_app_runner.py](scripts/orchestrator/codex_app_runner.py): `codex app-server` protocol runner
- [scripts/orchestrator/codex_runner.py](scripts/orchestrator/codex_runner.py): `codex exec` fallback runner
- [scripts/orchestrator/codex_adapter.py](scripts/orchestrator/codex_adapter.py): Claude slash skill 参照を Codex worker prompt に取り込む adapter
- [server/](server): Codex App から使う FastAPI server
- [scripts/orchestrator/paths.py](scripts/orchestrator/paths.py): run ごとの output root 解決
- [docs/CODEX_APP.ja.md](docs/CODEX_APP.ja.md): Codex App 連携の詳細
- [SECURITY.md](SECURITY.md): セキュリティ報告の手順
- [CONTRIBUTING.md](CONTRIBUTING.md): issue / pull request の方針
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md): コミュニティ上の行動規範
- [LICENSE](LICENSE): MIT License

## セキュリティ報告

このリポジトリ、GitHub Actions、runner isolation、生成物の扱いに関するセキュリティ上の問題は、公開 issue ではなく [SECURITY.md](SECURITY.md) の手順で報告してください。

SPECA で第三者ターゲットを検証して得た候補 finding は、人間が検証したうえで、そのターゲットの disclosure policy や bug bounty 窓口に報告してください。このリポジトリの公開 issue に第三者ターゲットの未調整な脆弱性詳細を書かないでください。

## 貢献

issue や pull request は歓迎します。詳しい方針は [CONTRIBUTING.md](CONTRIBUTING.md) を見てください。

- bug report / feature request は、再現手順や具体的な use-case を添えてください。
- user-facing な説明や検証メモを変える場合は、`README.md` と `README.ja.md` の内容を揃えてください。
- ログやスクリーンショットには、API key、token、account identifier、private repository 名、ローカル絶対パスを含めないでください。
- セキュリティ上センシティブな内容は公開 issue に書かず、[SECURITY.md](SECURITY.md) の手順を使ってください。

## ライセンス

この repository は MIT License です。公開、改変、再配布する場合も [LICENSE](LICENSE) を保持してください。

著作権表示:

```text
Copyright (c) 2026 Nyx Foundation and SPECA contributors
```

この表示と MIT License 本文を配布物に含める必要があります。
