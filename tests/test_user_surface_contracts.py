import json
import time
from pathlib import Path

from server.discord import _build_embed
from server.progress import ProgressBus
from server.run_manager import RunInfo, RunStatus


def test_discord_embed_reports_token_usage_without_dollar_estimates():
    run = RunInfo(
        run_id="run-123",
        phase_id="03",
        output_dir="outputs/inst_01",
        status=RunStatus.COMPLETED,
        created_at=time.time() - 10,
        completed_at=time.time(),
        inputs={},
        bus=ProgressBus(),
        result={
            "total_results": 7,
            "cost": {
                "total_input_tokens": 100_000,
                "total_cache_read_tokens": 250_000,
                "total_cache_creation_tokens": 10_000,
                "total_output_tokens": 30_000,
                "total_tokens": 390_000,
                "total_turns": 12,
                "total_cost_usd": 8.50,
                "budget_utilization_pct": 28.3,
            },
        },
    )

    embed = _build_embed(run)
    fields = {field["name"]: field["value"] for field in embed["fields"]}

    assert "Token usage" in fields
    assert "Total: 390,000" in fields["Token usage"]
    assert "Input: 100,000" in fields["Token usage"]
    assert "Cache read: 250,000" in fields["Token usage"]
    assert "Output: 30,000" in fields["Token usage"]
    assert "Turns: 12" in fields["Token usage"]
    assert "Estimated token cost" not in fields
    assert "Budget utilization" not in fields
    assert "$" not in fields["Token usage"]


def test_discord_embed_accepts_native_token_usage_field():
    run = RunInfo(
        run_id="run-456",
        phase_id="04",
        output_dir="outputs/inst_02",
        status=RunStatus.COMPLETED,
        created_at=time.time() - 5,
        completed_at=time.time(),
        inputs={},
        bus=ProgressBus(),
        result={
            "token_usage": {
                "total_input_tokens": 10,
                "total_output_tokens": 2,
            },
        },
    )

    embed = _build_embed(run)
    fields = {field["name"]: field["value"] for field in embed["fields"]}

    assert fields["Token usage"] == "Total: 12\nInput: 10\nOutput: 2"


def test_github_issue_helper_uses_current_outputs_path():
    script = Path("scripts/get_github_issues.sh").read_text(encoding="utf-8")

    assert "outputs/00_SIMILAR_ISSUES.json" in script
    assert "--output path" in script
    assert "security-agent/outputs" not in script


def test_web_readme_describes_design_only_surface():
    readme = Path("web/README.md").read_text(encoding="utf-8")
    design = Path("web/WEB_APP_DESIGN.md").read_text(encoding="utf-8")

    assert "not a runnable frontend application yet" in readme
    assert "React + TypeScript + Vite" not in readme
    assert "template provides" not in readme
    assert "ann.md" not in design
    assert "security-agent/" not in design


def test_automation_playbook_does_not_advertise_unimplemented_web_client():
    playbook = Path("automation/AUDIT_PLAYBOOK.md").read_text(encoding="utf-8")

    assert "Max concurrent worker turns" in playbook
    assert '| `--max-concurrent` | `8` |' in playbook
    assert "--runner codex-app" in playbook
    assert "not an implemented `/audit` slash command" in playbook
    assert "not a runnable client yet" in playbook
    assert "/audit <bug_bounty_url>" not in playbook
    assert "cd web && npm run dev" not in playbook
    assert "http://localhost:5173" not in playbook
    assert "Max concurrent Claude calls" not in playbook


def test_cli_metadata_points_at_codex_fork():
    readme = Path("cli/README.md").read_text(encoding="utf-8")
    package = json.loads(Path("cli/package.json").read_text(encoding="utf-8"))

    assert "https://github.com/MekuraRabbit/speca-codex" in readme
    assert "auth login" in readme
    assert "commands/auth/" in readme
    assert "auth.flow.test.ts" in readme
    assert "optional legacy Claude Code" in readme
    assert "Stack (M1)" not in readme
    assert package["repository"]["url"] == "https://github.com/MekuraRabbit/speca-codex.git"
    assert "https://github.com/NyxFoundation/speca/issues/3" not in readme


def test_root_readme_describes_token_usage_without_api_cost_surface():
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "token-usage telemetry" in readme
    assert "Normal Codex App summaries report token counts" in readme
    assert "raw runner/API payloads may still include estimated-cost fields" in readme
    assert "actual API spend unless an API runner was explicitly used" in readme
    assert "structured log/cost telemetry" not in readme
    assert "per-phase budget enforcement" not in readme
