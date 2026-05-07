"""Tests for the Codex CLI runner."""

import asyncio
import json
from pathlib import Path

from scripts.orchestrator.codex_runner import CodexRunner
from scripts.orchestrator.config import get_phase_config


def test_codex_runner_command_uses_codex_exec_stdin():
    config = get_phase_config("03")
    runner = CodexRunner(config, asyncio.Semaphore(1))

    cmd, stdin_bytes = runner._build_cmd("hello")

    assert "exec" in cmd
    assert "--json" in cmd
    assert "--skip-git-repo-check" in cmd
    assert cmd[-1] == "-"
    assert stdin_bytes == b"hello"


def test_codex_runner_does_not_pass_claude_model_alias():
    config = get_phase_config("03")
    config.model = "sonnet"
    runner = CodexRunner(config, asyncio.Semaphore(1))

    cmd, _ = runner._build_cmd("hello")

    assert "--model" not in cmd


def test_codex_runner_passes_codex_model_override():
    config = get_phase_config("03")
    config.model = "gpt-5.2"
    runner = CodexRunner(config, asyncio.Semaphore(1))

    cmd, _ = runner._build_cmd("hello")

    model_index = cmd.index("--model")
    assert cmd[model_index + 1] == "gpt-5.2"


def test_codex_runner_passes_codex_model_env_override(monkeypatch):
    monkeypatch.setenv("SPECA_CODEX_MODEL", "gpt-5.2")
    config = get_phase_config("03")
    config.model = "sonnet"
    runner = CodexRunner(config, asyncio.Semaphore(1))

    cmd, _ = runner._build_cmd("hello")

    model_index = cmd.index("--model")
    assert cmd[model_index + 1] == "gpt-5.2"


def test_codex_runner_runtime_model_override_wins_over_env(monkeypatch):
    monkeypatch.setenv("SPECA_CODEX_MODEL", "gpt-5.2")
    config = get_phase_config("03")
    config.runtime_env["SPECA_CODEX_MODEL"] = "gpt-5.5"
    runner = CodexRunner(config, asyncio.Semaphore(1))

    cmd, _ = runner._build_cmd("hello")

    model_index = cmd.index("--model")
    assert cmd[model_index + 1] == "gpt-5.5"


def test_codex_runner_injects_adapter_instructions():
    config = get_phase_config("03")
    runner = CodexRunner(config, asyncio.Semaphore(1))

    prompt = runner._build_prompt(
        worker_id=0,
        queue_file="outputs/q.json",
        context_file="outputs/c.json",
        batch_size=1,
        iteration=0,
        timestamp=1,
        output_file="outputs/out.json",
    )

    assert "<codex_worker_adapter>" in prompt
    assert "codex exec" in prompt
    assert "OUTPUT_FILE=outputs/out.json" in prompt
    assert "SPECA_OUTPUT_DIR" in prompt
    assert "never probe" in prompt
    assert "repository-root `outputs/` as a fallback" in prompt
    assert "TARGET_INFO.local_checkout" in prompt
    assert "Do not list/search its" in prompt


def test_codex_runner_inlines_referenced_claude_skill():
    config = get_phase_config("01a")
    runner = CodexRunner(config, asyncio.Semaphore(1))

    prompt = runner._build_prompt(
        worker_id=0,
        queue_file="outputs/q.json",
        context_file="outputs/c.json",
        batch_size=1,
        iteration=0,
        timestamp=1,
        output_file="outputs/01a_STATE.json",
        url="https://example.com/spec",
    )

    assert "<codex_skill_context>" in prompt
    assert "/spec-discovery" in prompt
    assert ".claude/skills/spec-discovery/SKILL.md" in prompt


def test_runner_parses_utf8_bom_json(tmp_path: Path):
    config = get_phase_config("04")
    runner = CodexRunner(config, asyncio.Semaphore(1))
    output_file = tmp_path / "out.json"
    output_file.write_text(
        json.dumps({"reviewed_items": [{"property_id": "p1"}]}),
        encoding="utf-8-sig",
    )

    assert runner._parse_results(output_file) == [{"property_id": "p1"}]
