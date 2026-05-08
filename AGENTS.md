# SPECA Agent Guide

This repository is SPECA: a specification-to-property security audit pipeline.
It was originally optimized for Claude Code, but it now has Codex-friendly
entry points as well. Keep the Claude workflow intact when making changes.

## Core Commands

```bash
uv run python -m pytest tests/ -v --tb=short
uv run python scripts/run_phase.py --phase 01a
uv run python scripts/run_phase.py --phase 01a 01b 01e
uv run python scripts/run_phase.py --target 04 --workers 4
uv run python scripts/run_phase.py --phase 03 --force --workers 4 --max-concurrent 64
uv run --no-sync python -m server.app
.venv/Scripts/python.exe -m server.app
.venv/bin/python -m server.app
```

## Codex App Workflow

- Use `.codex/launch.json` to start the SPECA API app server from Codex App.
  It calls `uv run --no-sync python -m server.app`, which reuses the existing
  lightweight `.venv` on Windows/macOS/Linux. Legacy resolver extras such as
  SWE-agent are optional and live outside the default dependency set.
- The app server exposes:
  - `GET /api/health`
  - `GET /api/phases/`
  - `POST /api/phases/dispatch`
  - `GET /api/runs/`
  - `GET /api/runs/{run_id}`
  - `GET /api/runs/{run_id}/diffs`
  - `GET /api/runs/{run_id}/progress`
- Codex App server runs default to `CodexAppRunner`, which dispatches SPECA
  worker batches as `codex app-server` threads. `CodexRunner` remains as the
  `codex exec` fallback.
- For parallel app-server runs, always give each run a unique `output_dir`
  such as `outputs/inst_01`, `outputs/inst_02`, etc. The server rejects two
  active runs that target the same output directory.

Example dispatch:

```bash
curl -X POST http://127.0.0.1:8000/api/phases/dispatch \
  -H "content-type: application/json" \
  -d '{"phase_id":"03","workers":2,"max_concurrent":4,"output_dir":"outputs/inst_01"}'
```

The app-server default worker runtime is Codex app-server. The CLI keeps the
historical Claude default unless `--runner codex-app` or `--runner codex` is
provided, so upstream scripts do not break.

```bash
uv run python scripts/run_phase.py --phase 03 --runner codex-app
uv run python scripts/run_phase.py --phase 03 --runner codex  # codex exec fallback
```

Claude model aliases in legacy config or docs (`sonnet`, `opus`, `haiku`, or
full Claude model names) are ignored by Codex runners. Use `--model gpt-*` or
dispatch `"model": "gpt-*"` only when the user explicitly wants a Codex model
override.

Optional app-server dispatch fields:

```json
{
  "phase_id": "03",
  "output_dir": "outputs/inst_01",
  "isolated_worktrees": true
}
```

## Architecture Notes

- Phase configs live in `scripts/orchestrator/config.py`.
- `scripts/orchestrator/codex_app_runner.py` is the Codex app-server protocol
  runner used by the SPECA app server by default.
- `scripts/orchestrator/codex_runner.py` is the Codex CLI (`codex exec`)
  fallback runner.
- `scripts/orchestrator/codex_adapter.py` inlines referenced
  `.claude/skills/*/SKILL.md` files into Codex worker prompts. Codex does not
  execute Claude slash skills directly.
- `scripts/orchestrator/runner.py` is the original Claude CLI runner, retained
  for backwards compatibility with existing scripts and CI.
- `scripts/orchestrator/api_runner.py` is an optional OpenAI-compatible API
  runner for environments that explicitly choose it.
- `scripts/orchestrator/paths.py` resolves `SPECA_OUTPUT_DIR`. It also supports
  task-local output roots so the FastAPI app server can run multiple isolated
  instances in one Python process.
- `server/` is the app-server integration used by Codex App. It should not rely
  on process-global env mutation for per-run state.

## Safety Rails

- Use SPECA only for repositories and systems the operator owns, maintains, or
  is explicitly authorized to assess. If authorization or scope is unclear,
  ask for confirmation before launching an audit run.
- Treat `outputs/BUG_BOUNTY_SCOPE.json` and `outputs/TARGET_INFO.json` as the
  authorized boundary for a SPECA run. Do not broaden the target to unrelated
  repositories, live services, accounts, or infrastructure.
- Do not delete or rename `CLAUDE.md`, `.claude/`, or GitHub Actions that invoke
  Claude Code unless the user explicitly asks.
- Preserve partial-result and resume behavior. `outputs/*_PARTIAL_*.json` files
  are first-class state.
- Do not share one output directory across concurrent runs.
