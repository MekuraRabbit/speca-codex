import json
import os
import shutil
import subprocess
import time
import tomllib
from pathlib import Path

import pytest

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
    assert "Historical Anthropic auth prototype" in readme
    assert "commands/auth/" in readme
    assert "auth.flow.test.ts" in readme
    assert "optional legacy Claude Code" not in readme
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


def test_root_readme_documents_strict_schema_mode():
    readme = Path("README.md").read_text(encoding="utf-8")
    readme_ja = Path("README.ja.md").read_text(encoding="utf-8")

    assert "SPECA_STRICT_SCHEMA" in readme
    assert "schema validation failures" in readme
    assert "malformed partials" in readme
    assert "SPECA_STRICT_SCHEMA" in readme_ja
    assert "malformed partial" in readme_ja


def test_resolver_dependencies_are_not_default_install_surface():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    default_deps = "\n".join(pyproject["project"]["dependencies"]).lower()
    resolver_deps = "\n".join(pyproject["dependency-groups"]["resolver"]).lower()

    assert "sweagent" not in default_deps
    assert "swe-agent" not in default_deps
    assert "sweagent" in resolver_deps
    assert "swe-agent" in resolver_deps

    for path in (
        Path("README.md"),
        Path("README.ja.md"),
        Path("CONTRIBUTING.md"),
        Path("automation/AUDIT_PLAYBOOK.md"),
    ):
        doc = path.read_text(encoding="utf-8")
        assert "uv sync --group resolver" in doc


def test_public_readmes_link_security_and_contribution_guides():
    readme = Path("README.md").read_text(encoding="utf-8")
    readme_ja = Path("README.ja.md").read_text(encoding="utf-8")

    for doc in (readme, readme_ja):
        assert "SECURITY.md" in doc
        assert "CONTRIBUTING.md" in doc

    assert "public issue tracker" in readme
    assert "公開 issue" in readme_ja


def test_oss_metadata_uses_codex_fork_name():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    readme = Path("README.md").read_text(encoding="utf-8")
    readme_ja = Path("README.ja.md").read_text(encoding="utf-8")

    assert pyproject["project"]["name"] == "speca-codex"
    assert pyproject["project"]["readme"] == "README.md"
    assert pyproject["project"]["license"]["file"] == "LICENSE"
    assert "not as a published" in readme
    assert "PyPI package" in readme
    assert "PyPI package として配布していません" in readme_ja


def test_public_workflows_do_not_reference_stale_security_agent_repo():
    workflow_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path(".github/workflows").glob("*.yml")
    )

    assert "NyxFoundation/security-agent" not in workflow_text
    assert "grandchildrice" not in workflow_text
    assert "hirorogo" not in workflow_text
    assert "target_branch: \"master\"" not in workflow_text
    assert "ref: master" not in workflow_text
    assert "origin master" not in workflow_text


def test_mcp_setup_does_not_print_project_config_or_unmasked_tokens():
    script = Path("scripts/setup_mcp.sh").read_text(encoding="utf-8")

    assert "::add-mask::${RESOLVED_GH_TOKEN}" in script
    assert '[ "${GITHUB_ACTIONS:-}" = "true" ]' in script
    assert "mcp-server-tree-sitter==0.7.0" in script
    assert "git+https://github.com/oraios/serena@v1.2.0" in script
    assert "semgrep-mcp==0.9.0" in script
    assert "@modelcontextprotocol/server-filesystem@2026.1.14" in script
    assert "mcp-server-fetch==2025.4.7" in script
    assert "@modelcontextprotocol/server-github@2025.4.8" in script
    assert '"${SERVER_COMMAND[@]}"' in script
    assert "for dir in ${FILESYSTEM_DIRS}" not in script
    assert "uvx mcp-server-fetch" not in script
    assert "npx -y @modelcontextprotocol/server-filesystem" not in script
    assert "cat .mcp.json" not in script
    assert "Contents of .mcp.json" not in script
    assert "intentionally not printed" in script


def test_public_workflows_and_active_cli_do_not_install_legacy_claude_code():
    workflow_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path(".github/workflows").glob("*.yml")
    )
    user_surfaces = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [
            Path("README.md"),
            Path("README.ja.md"),
            Path("cli/README.md"),
            Path("cli/src/lib/checks.ts"),
        ]
    )
    unpinned_claude_install = "npm install -g @anthropic-ai/" + "claude-code"

    assert "@anthropic-ai/claude-code" not in workflow_text
    assert "CLAUDE_CODE_PERMISSIONS" not in workflow_text
    assert "@anthropic-ai/claude-code" not in user_surfaces
    assert f"{unpinned_claude_install}`" not in user_surfaces
    assert f'{unpinned_claude_install}",' not in user_surfaces
    assert 'version: "latest"' not in workflow_text
    assert workflow_text.count('version: "0.11.11"') >= 2


def test_mcp_setup_preserves_newline_filesystem_dirs_with_spaces(tmp_path):
    bash = shutil.which("bash")
    if not bash:
        pytest.skip("bash is not available")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log_path = tmp_path / "claude_args.log"

    fake_claude = bin_dir / "claude"
    fake_claude.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
if [ "${1:-}" = "mcp" ] && [ "${2:-}" = "list" ]; then
  exit 0
fi
if [ "${1:-}" = "mcp" ] && [ "${2:-}" = "add" ]; then
  {
    echo "CALL"
    for arg in "$@"; do
      printf '[%s]\\n' "$arg"
    done
  } >> "${CLAUDE_ARGS_LOG}"
  exit 0
fi
echo "unexpected claude call: $*" >&2
exit 2
""",
        encoding="utf-8",
        newline="\n",
    )
    fake_claude.chmod(0o755)

    for tool in ("npx", "uvx"):
        fake_tool = bin_dir / tool
        fake_tool.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8", newline="\n")
        fake_tool.chmod(0o755)

    spaced_scope = tmp_path / "scope one"
    plain_scope = tmp_path / "scope-two"
    spaced_scope.mkdir()
    plain_scope.mkdir()

    env = os.environ.copy()
    env["CLAUDE_ARGS_LOG"] = str(log_path)
    env["FILESYSTEM_DIRS"] = f"{spaced_scope.name}\n{plain_scope.name}"
    env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")
    for token_var in ("GITHUB_PERSONAL_ACCESS_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"):
        env.pop(token_var, None)

    subprocess.run(
        [bash, str(Path.cwd() / "scripts/setup_mcp.sh")],
        cwd=tmp_path,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )

    calls = log_path.read_text(encoding="utf-8").split("CALL\n")
    filesystem_call = next(call for call in calls if "\n[filesystem]\n" in call)

    assert "scope one]" in filesystem_call
    assert "scope-two]" in filesystem_call
    assert "[scope]" not in filesystem_call
    assert "[one]" not in filesystem_call


def test_public_ai_resolver_workflows_are_disabled():
    resolver = Path(".github/workflows/issue-resolver.yml").read_text(encoding="utf-8")
    reusable = Path(".github/workflows/openhands-resolver.yml").read_text(encoding="utf-8")
    sweagent = Path(".github/workflows/sweagent-issue-resolver.yml").read_text(encoding="utf-8")

    for workflow in (resolver, reusable, sweagent):
        assert "workflow_dispatch:" in workflow
        assert "Disabled in public fork" in workflow
        assert "contents: read" in workflow
        assert "contents: write" not in workflow
        assert "issue_comment:" not in workflow
        assert "pull_request_review" not in workflow
        assert "LLM_API_KEY" not in workflow
        assert "GITHUB_TOKEN" not in workflow

    codeowners = Path(".github/CODEOWNERS").read_text(encoding="utf-8")

    assert "@MekuraRabbit" in codeowners
    assert "@grandchildrice" not in codeowners


def test_public_api_launch_docs_use_guarded_entrypoint():
    public_docs = [
        Path("AGENTS.md"),
        Path("README.md"),
        Path("README.ja.md"),
        Path("docs/CODEX_APP.md"),
        Path("docs/CODEX_APP.ja.md"),
    ]

    for path in public_docs:
        doc = path.read_text(encoding="utf-8")
        assert "uvicorn server.app:app" not in doc
        assert "uv run python -m server.app" not in doc
        assert "uv run --no-sync python -m server.app" in doc
        assert "-m server.app" in doc

    codex_app_docs = [
        Path("README.md"),
        Path("README.ja.md"),
        Path("docs/CODEX_APP.md"),
        Path("docs/CODEX_APP.ja.md"),
    ]
    for path in codex_app_docs:
        doc = path.read_text(encoding="utf-8")
        assert ".venv/Scripts/python.exe -m server.app" in doc
        assert ".venv/bin/python -m server.app" in doc

    launch_config = json.loads(Path(".codex/launch.json").read_text(encoding="utf-8"))
    launch_entry = launch_config["configurations"][0]

    assert launch_entry["runtimeExecutable"] == "uv"
    assert launch_entry["runtimeArgs"] == [
        "run",
        "--no-sync",
        "python",
        "-m",
        "server.app",
    ]


def test_codex_app_docs_describe_run_info_persistence():
    codex_doc = Path("docs/CODEX_APP.md").read_text(encoding="utf-8")
    codex_doc_ja = Path("docs/CODEX_APP.ja.md").read_text(encoding="utf-8")

    assert "RUN_INFO.json" in codex_doc
    assert "outputs/**/RUN_INFO.json" in codex_doc
    assert "queued" in codex_doc
    assert "running" in codex_doc
    assert "RUN_INFO.json" in codex_doc_ja
    assert "outputs/**/RUN_INFO.json" in codex_doc_ja
    assert "queued" in codex_doc_ja
    assert "running" in codex_doc_ja


def test_codex_app_docs_describe_ephemeral_thread_default():
    public_docs = [
        Path("README.md"),
        Path("README.ja.md"),
        Path("docs/CODEX_APP.md"),
        Path("docs/CODEX_APP.ja.md"),
    ]

    for path in public_docs:
        doc = path.read_text(encoding="utf-8")
        assert "SPECA_CODEX_APP_EPHEMERAL_THREADS" in doc
        assert "ephemeral" in doc


def test_codex_docs_describe_sandbox_defaults():
    public_docs = [
        Path("README.md"),
        Path("README.ja.md"),
        Path("docs/CODEX_APP.md"),
        Path("docs/CODEX_APP.ja.md"),
    ]

    for path in public_docs:
        doc = path.read_text(encoding="utf-8")
        assert "SPECA_CODEX_SANDBOX" in doc
        assert "workspace-write" in doc
        assert "danger-full-access" in doc
