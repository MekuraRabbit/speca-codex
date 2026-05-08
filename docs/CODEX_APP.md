# Codex App Integration

Japanese version: [CODEX_APP.ja.md](CODEX_APP.ja.md)

SPECA still supports the original Claude Code flow for backwards compatibility.
Codex App support is added as an app-server layer whose default worker runtime
is `codex app-server`, so the actual phase work is performed by Codex threads
while the SPECA phase order, output schemas, resume behavior, and parallel
batching stay intact. `codex exec` remains available as a local fallback runner.

## Authorized Use

Use SPECA only on repositories and systems you own, maintain, or are explicitly
authorized to assess through a contract, bug bounty, or other clear permission.
When asking Codex to run SPECA, keep the run within the boundary described by
`BUG_BOUNTY_SCOPE.json` and `TARGET_INFO.json`; do not broaden the task to
unrelated repositories, live services, accounts, or infrastructure.

## Ask Codex This Way

In Codex App, users do not need to memorize the API calls. The intended path is
to ask Codex to start SPECA, dispatch phases, watch progress, and summarize the
outputs.

First smoke test:

```text
Start the SPECA API for this repository and check /api/health.
Run a Codex App runner 01a smoke test and watch progress.
Use seed URL https://github.com/ethereum/EIPs/blob/master/EIPS/eip-7594.md
and output_dir outputs/smoke_01a. Summarize 01a_STATE.json when it finishes.
```

Production-like audit:

```text
Assuming outputs/BUG_BOUNTY_SCOPE.json and outputs/TARGET_INFO.json exist,
run SPECA through phase 04 with the Codex App runner and isolated_worktrees.
Use output_dir outputs/audit_<target-name>, workers=4, and max_concurrent=8.
Report progress, failed batches, thread metadata, diff/reducer results,
and final outputs.
```

The `curl` examples below show the underlying API operations for manual
debugging and reproducibility.

The dispatch API does not clone a target repository or derive audit scope from
request fields. Before target-code phases, prepare `outputs/TARGET_INFO.json`
and `outputs/BUG_BOUNTY_SCOPE.json`; `target_repo`, `target_ref_type`, and
`audit_scope` are rejected until a real setup endpoint exists.

## Start The App Server

From Codex App, launch `speca-api` from `.codex/launch.json`.

Manual equivalent:

```bash
uv run --no-sync python -m server.app
```

The `--no-sync` flag reuses an existing lightweight `.venv` without forcing a
full project sync of legacy workflow dependencies.

> **Do not expose this API.** The SPECA API is a local single-user control
> plane that can launch agent worker runs. It is unauthenticated and should
> stay bound to loopback (`127.0.0.1`, `localhost`, or `::1`). Non-loopback
> binds are refused unless `SPECA_ENABLE_REMOTE_API=1` is set for an explicitly
> reviewed local environment.

On Windows, if you want to bypass the launcher and call the lightweight venv
directly:

```bash
.venv/Scripts/python.exe -m server.app
```

On macOS/Linux, the equivalent direct venv command is:

```bash
.venv/bin/python -m server.app
```

Use `--reload` only for interactive API development. For Codex App worker smoke
tests, prefer the single-process command above so stale reloader children do not
keep serving old code.

Health check:

```bash
curl http://127.0.0.1:8000/api/health
```

## Dispatch A Smoke Phase

Use `01a` first because it does not require earlier SPECA outputs. Phases `03`
and `04` require the preceding `outputs/*.json` artifacts.

```bash
curl -X POST http://127.0.0.1:8000/api/phases/dispatch \
  -H "content-type: application/json" \
  -d '{"phase_id":"01a","workers":1,"max_concurrent":1,"spec_urls":"https://github.com/ethereum/EIPs/blob/master/EIPS/eip-7594.md","output_dir":"outputs/smoke_01a"}'
```

Then stream progress:

```bash
curl -N http://127.0.0.1:8000/api/runs/<run_id>/progress
```

## Parallel Runs

Each concurrent run must use a different `output_dir`.

```bash
curl -X POST http://127.0.0.1:8000/api/phases/dispatch \
  -H "content-type: application/json" \
  -d '{"phase_id":"02c","workers":2,"max_concurrent":4,"output_dir":"outputs/inst_01"}'

curl -X POST http://127.0.0.1:8000/api/phases/dispatch \
  -H "content-type: application/json" \
  -d '{"phase_id":"02c","workers":2,"max_concurrent":4,"output_dir":"outputs/inst_02"}'
```

The app server rejects two active runs pointed at the same output directory.
This prevents partial files, logs, MCP configs, and debug files from colliding.

## Runner Selection

Default:

```json
{
  "phase_id": "01a",
  "spec_urls": "https://github.com/ethereum/EIPs/blob/master/EIPS/eip-7594.md",
  "output_dir": "outputs/smoke_01a"
}
```

Uses `CodexAppRunner`, which creates Codex app-server threads for each worker
batch. If no external app-server URL is provided, SPECA starts a loopback
`codex app-server` process for the run.

To use an existing Codex app-server websocket:

```json
{
  "phase_id": "01a",
  "runner": "codex-app",
  "app_server_url": "ws://127.0.0.1:8765",
  "spec_urls": "https://github.com/ethereum/EIPs/blob/master/EIPS/eip-7594.md",
  "output_dir": "outputs/smoke_01a"
}
```

Claude-oriented model aliases left in `PhaseConfig` or `CLAUDE.md` (`sonnet`,
`opus`, `haiku`, or full Claude model names) are ignored by Codex runners.
When an API run is launched from Codex App and `model` is omitted, SPECA tries
to read the latest `turn_context` for the current `CODEX_THREAD_ID` from
Codex's local session metadata. If found, the GUI-selected model and reasoning
effort are passed to the app-server turn and recorded with sources such as
`model_source: "codex-gui"` and `effort_source: "codex-gui"`.

The current Codex App protocol also accepts `serviceTier` (`fast` or `flex`) on
app-server turns. SPECA will pass a GUI service tier if future session metadata
contains one. Today, the standard speed setting is not stored as a distinct
session value, so SPECA treats it as the app-server default.

You can still pass a model explicitly:

```json
{
  "phase_id": "03",
  "model": "<CODEX_MODEL>",
  "output_dir": "outputs/inst_01"
}
```

To force the app-server default instead of the GUI-selected model:

```json
{
  "phase_id": "03",
  "use_codex_gui_model": false,
  "output_dir": "outputs/inst_01"
}
```

You can also override reasoning effort or service tier explicitly:

```json
{
  "phase_id": "03",
  "reasoning_effort": "xhigh",
  "service_tier": "fast",
  "output_dir": "outputs/inst_01"
}
```

To isolate worker checkouts and collect diffs:

```json
{
  "phase_id": "03",
  "workers": 4,
  "isolated_worktrees": true,
  "output_dir": "outputs/inst_01"
}
```

Collected thread metadata is available at:

```bash
curl http://127.0.0.1:8000/api/runs/<run_id>/diffs
curl "http://127.0.0.1:8000/api/runs/<run_id>/diffs?include_content=true"
```

Source diffs are collected for isolated worktree runs. Non-isolated runs still
record thread metadata, but suppress workspace diffs so unrelated local changes
are not swept into run metadata.

Explicit Claude fallback for old local/CI workflows:

```json
{
  "phase_id": "03",
  "runner": "claude",
  "output_dir": "outputs/inst_01"
}
```

CLI equivalent for Codex workers:

```bash
SPEC_URLS="https://github.com/ethereum/EIPs/blob/master/EIPS/eip-7594.md" \
  uv run python scripts/run_phase.py --phase 01a --runner codex-app
SPEC_URLS="https://github.com/ethereum/EIPs/blob/master/EIPS/eip-7594.md" \
  uv run python scripts/run_phase.py --phase 01a --runner codex  # codex exec fallback
```

An OpenAI-compatible API runner remains available for explicit opt-in:

```bash
API_RUNNER_API_KEY="$OPENAI_API_KEY" \
uv run python scripts/run_phase.py --phase 03 --runner api --model <OPENAI_MODEL>
```

## Shared Data For Instance Runs

For N parallel SPECA instances, run shared phases once, then isolate later
phases by output directory:

```bash
uv run python scripts/run_phase.py --phase 01a 01b 01e --workers 4
```

Prepare instance directories with links/copies of shared inputs:

```bash
mkdir -p outputs/inst_01 outputs/inst_02
```

Each instance directory should contain the shared files needed by its target
phase, for example `01e_PARTIAL_*.json`, `BUG_BOUNTY_SCOPE.json`,
`TARGET_INFO.json`, and graph outputs as required by the phase.

## Implementation Notes

- `scripts/orchestrator/paths.py` uses a task-local output root for app-server
  runs and `SPECA_OUTPUT_DIR` for CLI/CI compatibility.
- `scripts/orchestrator/codex_app_runner.py` is the Codex app-server protocol
  runner. It records thread ids and turn ids under
  `<output_dir>/codex_app_threads/`, and collects source diffs for isolated
  worktree runs.
- `scripts/orchestrator/codex_adapter.py` inlines referenced
  `.claude/skills/*/SKILL.md` files into Codex worker prompts. Codex does not
  execute Claude slash skills directly.
- `server/run_manager.py` allows concurrent runs with distinct output dirs.
- `PhaseConfig` objects returned by `get_phase_config()` are copies, so per-run
  app-server overrides cannot leak into another run.
- Codex/Claude debug and MCP config scratch files are written under the selected
  output root during worker execution.
- Discord notifications are optional. Set `SPECA_DISCORD_WEBHOOK_URL` in the
  server environment to enable them; no webhook URL is stored in the repository.
