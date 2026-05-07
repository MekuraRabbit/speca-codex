"""Tests for the Codex app-server runner."""

import asyncio
import json
import re
import subprocess
from pathlib import Path

from scripts.orchestrator.codex_app_runner import (
    CodexAppRunner,
    CodexAppServerClient,
    TurnCapture,
)
from scripts.orchestrator.config import get_phase_config
from scripts.orchestrator.paths import output_root_context
from scripts.orchestrator.watchdog import CostTracker


def test_codex_app_runner_injects_adapter_instructions(tmp_path: Path):
    with output_root_context(tmp_path):
        config = get_phase_config("03")
        config.workdir = str(tmp_path)
        runner = CodexAppRunner(config, asyncio.Semaphore(1))

        prompt = runner._build_prompt(
            worker_id=0,
            queue_file=str(tmp_path / "q.json"),
            context_file=str(tmp_path / "c.json"),
            batch_size=1,
            iteration=0,
            timestamp=1,
            output_file=str(tmp_path / "out.json"),
        )

    assert "<codex_app_worker_adapter>" in prompt
    assert "OUTPUT_FILE=" in prompt
    assert "isolated worktree" in prompt
    assert "translate that path to" in prompt
    assert "never probe" in prompt
    assert "repository-root `outputs/` as a fallback" in prompt
    assert "TARGET_INFO.local_checkout" in prompt
    assert "Do not list/search its" in prompt


def test_codex_app_runner_inlines_referenced_claude_skill(tmp_path: Path):
    with output_root_context(tmp_path):
        config = get_phase_config("01b")
        config.workdir = str(tmp_path)
        runner = CodexAppRunner(config, asyncio.Semaphore(1))

        prompt = runner._build_prompt(
            worker_id=0,
            queue_file=str(tmp_path / "q.json"),
            context_file=str(tmp_path / "c.json"),
            batch_size=1,
            iteration=0,
            timestamp=1,
            output_dir=str(tmp_path / "graphs"),
        )

    assert "<codex_skill_context>" in prompt
    assert "/subgraph-extractor" in prompt
    assert ".claude/skills/subgraph-extractor/SKILL.md" in prompt
    assert "Do not recursively fetch links" in prompt
    assert "TARGET_INFO.local_checkout" in prompt


def test_codex_app_client_replays_early_turn_notifications(tmp_path: Path):
    client = CodexAppServerClient(
        url="ws://127.0.0.1:1",
        cwd=tmp_path,
        timeout_seconds=1,
    )

    client._handle_notification({
        "method": "item/agentMessage/delta",
        "params": {
            "threadId": "thread-1",
            "turnId": "turn-1",
            "itemId": "item-1",
            "delta": "hello",
        },
    })
    client._handle_notification({
        "method": "turn/diff/updated",
        "params": {
            "threadId": "thread-1",
            "turnId": "turn-1",
            "diff": "diff --git a/a b/a\n",
        },
    })
    client._handle_notification({
        "method": "thread/tokenUsage/updated",
        "params": {
            "threadId": "thread-1",
            "tokenUsage": {
                "total": {
                    "inputTokens": 1000,
                    "cachedInputTokens": 100,
                    "outputTokens": 50,
                }
            },
        },
    })
    client._handle_notification({
        "method": "turn/completed",
        "params": {
            "threadId": "thread-1",
            "turn": {"id": "turn-1", "status": "completed"},
        },
    })

    capture = TurnCapture(thread_id="thread-1", turn_id="turn-1")
    client._register_capture(capture)

    assert capture.text == "hello"
    assert capture.diff == "diff --git a/a b/a\n"
    assert capture.token_usage["total"]["inputTokens"] == 1000
    assert capture.completed is not None
    assert capture.completed["turn"]["status"] == "completed"


def test_codex_app_client_close_times_out_stuck_websocket(tmp_path: Path, monkeypatch):
    import scripts.orchestrator.codex_app_runner as module

    monkeypatch.setattr(module, "_WEBSOCKET_CLOSE_TIMEOUT_SECONDS", 0.01)

    class StuckWebSocket:
        async def close(self):
            await asyncio.sleep(3600)

    async def run() -> None:
        client = CodexAppServerClient(
            url="ws://127.0.0.1:1",
            cwd=tmp_path,
            timeout_seconds=1,
        )
        client._ws = StuckWebSocket()
        await asyncio.wait_for(client.close(), timeout=1)
        assert client._ws is None

    asyncio.run(run())


def test_codex_app_runner_uses_absolute_output_root(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with output_root_context("outputs/inst_01"):
        config = get_phase_config("03")
        config.workdir = str(tmp_path)
        runner = CodexAppRunner(config, asyncio.Semaphore(1))

    assert runner.output_dir == (tmp_path / "outputs" / "inst_01").resolve()


def test_codex_app_runner_skips_lfs_smudge_when_creating_worktree(tmp_path: Path, monkeypatch):
    import scripts.orchestrator.codex_app_runner as module

    seen: dict[str, object] = {}
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    with output_root_context(tmp_path / "outputs" / "inst"):
        config = get_phase_config("03")
        config.workdir = str(repo_root)
        config.isolated_worktrees = True
        runner = CodexAppRunner(config, asyncio.Semaphore(1))

    monkeypatch.setattr(runner, "_git_repo_root", lambda cwd: repo_root)
    monkeypatch.setattr(runner, "_looks_like_worktree", lambda path: False)

    def fake_run(cmd, **kwargs):
        seen["cmd"] = cmd
        seen["env"] = kwargs.get("env")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    cwd = runner._batch_cwd(worker_id=0)

    assert cwd.name.startswith("03_")
    env = seen["env"]
    assert isinstance(env, dict)
    assert env["GIT_LFS_SKIP_SMUDGE"] == "1"
    assert env["GIT_TERMINAL_PROMPT"] == "0"


def test_codex_app_runner_executes_with_fake_app_server(tmp_path: Path):
    async def run() -> list[dict]:
        with output_root_context(tmp_path):
            config = get_phase_config("03")
            config.workdir = str(tmp_path)
            config.runtime_env["SPECA_RUN_ID"] = "run-test"
            runner = CodexAppRunner(config, asyncio.Semaphore(1))

            class FakeClient:
                async def run_turn(self, *, prompt, cwd, model, effort, service_tier, timeout_seconds, developer_instructions):
                    assert model is None
                    assert effort is None
                    assert service_tier is None
                    matches = re.findall(r"OUTPUT_FILE=(\S+)", prompt)
                    assert matches
                    output_file = Path(matches[-1].strip('"'))
                    output_file.write_text(
                        json.dumps({"audit_items": [{"property_id": "p1"}]}),
                        encoding="utf-8",
                    )
                    capture = TurnCapture(thread_id="thread-1", turn_id="turn-1")
                    capture.completed = {"turn": {"status": "completed"}}
                    capture.diff = "diff --git a/file b/file\n"
                    return {"thread": {"id": "thread-1", "path": "thread-path"}}, capture

            async def fake_client():
                return FakeClient()

            runner._get_client = fake_client  # type: ignore[method-assign]
            return await runner._execute_batch(
                [
                    {
                        "property_id": "p1",
                        "text": "x",
                        "type": "invariant",
                        "assertion": "x",
                        "severity": "Low",
                        "covers": [],
                        "reachability": "unknown",
                        "exploitability": "unknown",
                        "code_scope": {},
                        "code_excerpt": "",
                    }
                ],
                worker_id=0,
                batch_index=0,
            )

    results = asyncio.run(run())

    assert results == [{"property_id": "p1"}]
    metadata_files = list((tmp_path / "codex_app_threads").glob("*.json"))
    assert len(metadata_files) == 1
    metadata = json.loads(metadata_files[0].read_text(encoding="utf-8"))
    assert metadata["run_id"] == "run-test"
    assert metadata["thread_id"] == "thread-1"
    assert metadata["has_diff"] is False
    assert metadata["requested_model"] is None
    assert metadata["model_source"] == "codex-app-default"
    assert metadata["requested_effort"] is None
    assert metadata["effort_source"] == "codex-app-default"
    assert metadata["requested_service_tier"] is None
    assert metadata["service_tier_source"] == "codex-app-default"


def test_codex_app_runner_synthesizes_01b_results_from_directory_artifacts(tmp_path: Path):
    async def run() -> list[dict]:
        with output_root_context(tmp_path):
            config = get_phase_config("01b")
            config.workdir = str(tmp_path)
            runner = CodexAppRunner(config, asyncio.Semaphore(1))

            class FakeClient:
                async def run_turn(self, *, prompt, cwd, model, effort, service_tier, timeout_seconds, developer_instructions):
                    matches = re.findall(r"OUTPUT_DIR=(\S+)", prompt)
                    assert matches
                    output_dir = Path(matches[-1].strip('"'))
                    for rel in (
                        "unstoppable/SG-001_halt_flow.mmd",
                        "unstoppable/SG-002_flashLoan.mmd",
                        "naive-receiver/SG-001_fee_drain_flow.mmd",
                    ):
                        path = output_dir / rel
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_text("---\ntitle: test\n---\nstateDiagram-v2\n", encoding="utf-8")
                    capture = TurnCapture(thread_id="thread-1", turn_id="turn-1")
                    capture.completed = {"turn": {"status": "completed"}}
                    capture.text_parts.append(f"Output Directory: {output_dir}")
                    return {"thread": {"id": "thread-1"}}, capture

            async def fake_client():
                return FakeClient()

            runner._get_client = fake_client  # type: ignore[method-assign]
            return await runner._execute_batch(
                [
                    {
                        "url": "https://www.damnvulnerabledefi.xyz/challenges/unstoppable/",
                        "title": "Unstoppable",
                    },
                    {
                        "url": "https://www.damnvulnerabledefi.xyz/challenges/naive-receiver/",
                        "title": "Naive receiver",
                    },
                ],
                worker_id=0,
                batch_index=0,
            )

    results = asyncio.run(run())

    by_title = {item["title"]: item for item in results}
    assert len(results) == 2
    assert len(by_title["Unstoppable"]["sub_graphs"]) == 2
    assert len(by_title["Naive receiver"]["sub_graphs"]) == 1
    first_file = by_title["Unstoppable"]["sub_graphs"][0]["mermaid_file"]
    assert first_file.startswith("graphs/batch_w0b0_")
    assert first_file.endswith("/unstoppable/SG-001_halt_flow.mmd")


def test_codex_app_runner_collects_diff_only_for_isolated_worktree(tmp_path: Path):
    async def run() -> dict:
        with output_root_context(tmp_path):
            config = get_phase_config("03")
            config.workdir = str(tmp_path)
            config.runtime_env["SPECA_RUN_ID"] = "run-test"
            config.isolated_worktrees = True
            runner = CodexAppRunner(config, asyncio.Semaphore(1))

            class FakeClient:
                async def run_turn(self, *, prompt, cwd, model, effort, service_tier, timeout_seconds, developer_instructions):
                    matches = re.findall(r"OUTPUT_FILE=(\S+)", prompt)
                    output_file = Path(matches[-1].strip('"'))
                    output_file.write_text(
                        json.dumps({"audit_items": [{"property_id": "p1"}]}),
                        encoding="utf-8",
                    )
                    capture = TurnCapture(thread_id="thread-1", turn_id="turn-1")
                    capture.completed = {"turn": {"status": "completed"}}
                    capture.diff = "diff --git a/file b/file\n"
                    return {"thread": {"id": "thread-1"}}, capture

            async def fake_client():
                return FakeClient()

            runner._get_client = fake_client  # type: ignore[method-assign]
            runner._batch_cwd = lambda worker_id: tmp_path  # type: ignore[method-assign]
            await runner._execute_batch(
                [
                    {
                        "property_id": "p1",
                        "text": "x",
                        "type": "invariant",
                        "assertion": "x",
                        "severity": "Low",
                        "covers": [],
                        "reachability": "unknown",
                        "exploitability": "unknown",
                        "code_scope": {},
                        "code_excerpt": "",
                    }
                ],
                worker_id=0,
                batch_index=0,
            )
            metadata_files = list((tmp_path / "codex_app_threads").glob("*.json"))
            return json.loads(metadata_files[0].read_text(encoding="utf-8"))

    metadata = asyncio.run(run())

    assert metadata["has_diff"] is True
    assert metadata["diff_file"]


def test_codex_app_runner_records_app_server_token_usage(tmp_path: Path):
    async def run() -> dict:
        with output_root_context(tmp_path):
            config = get_phase_config("03")
            config.workdir = str(tmp_path)
            cost_tracker = CostTracker(max_budget_usd=1000)
            runner = CodexAppRunner(
                config,
                asyncio.Semaphore(1),
                cost_tracker=cost_tracker,
            )

            class FakeClient:
                async def run_turn(self, *, prompt, cwd, model, effort, service_tier, timeout_seconds, developer_instructions):
                    matches = re.findall(r"OUTPUT_FILE=(\S+)", prompt)
                    output_file = Path(matches[-1].strip('"'))
                    output_file.write_text(
                        json.dumps({"audit_items": [{"property_id": "p1"}]}),
                        encoding="utf-8",
                    )
                    capture = TurnCapture(thread_id="thread-1", turn_id="turn-1")
                    capture.completed = {"turn": {"status": "completed"}}
                    capture.token_usage = {
                        "total": {
                            "inputTokens": 1000,
                            "cachedInputTokens": 100,
                            "outputTokens": 50,
                        }
                    }
                    return {"thread": {"id": "thread-1"}}, capture

            async def fake_client():
                return FakeClient()

            runner._get_client = fake_client  # type: ignore[method-assign]
            await runner._execute_batch(
                [
                    {
                        "property_id": "p1",
                        "text": "x",
                        "type": "invariant",
                        "assertion": "x",
                        "severity": "Low",
                        "covers": [],
                        "reachability": "unknown",
                        "exploitability": "unknown",
                        "code_scope": {},
                        "code_excerpt": "",
                    }
                ],
                worker_id=2,
                batch_index=3,
            )
            return cost_tracker.get_stats()

    stats = asyncio.run(run())

    assert stats["total_input_tokens"] == 900
    assert stats["total_cache_read_tokens"] == 100
    assert stats["total_output_tokens"] == 50
    assert stats["total_turns"] == 1
    assert stats["batch_count"] == 1


def test_codex_app_runner_passes_codex_model_override(tmp_path: Path):
    seen: dict[str, str | None] = {}

    async def run() -> None:
        with output_root_context(tmp_path):
            config = get_phase_config("03")
            config.workdir = str(tmp_path)
            config.model = "gpt-5.2"
            runner = CodexAppRunner(config, asyncio.Semaphore(1))

            class FakeClient:
                async def run_turn(self, *, prompt, cwd, model, effort, service_tier, timeout_seconds, developer_instructions):
                    seen["model"] = model
                    matches = re.findall(r"OUTPUT_FILE=(\S+)", prompt)
                    output_file = Path(matches[-1].strip('"'))
                    output_file.write_text(
                        json.dumps({"audit_items": [{"property_id": "p1"}]}),
                        encoding="utf-8",
                    )
                    capture = TurnCapture(thread_id="thread-1", turn_id="turn-1")
                    capture.completed = {"turn": {"status": "completed"}}
                    return {"thread": {"id": "thread-1"}}, capture

            async def fake_client():
                return FakeClient()

            runner._get_client = fake_client  # type: ignore[method-assign]
            await runner._execute_batch(
                [
                    {
                        "property_id": "p1",
                        "text": "x",
                        "type": "invariant",
                        "assertion": "x",
                        "severity": "Low",
                        "covers": [],
                        "reachability": "unknown",
                        "exploitability": "unknown",
                        "code_scope": {},
                        "code_excerpt": "",
                    }
                ],
                worker_id=0,
                batch_index=0,
            )

    asyncio.run(run())

    assert seen["model"] == "gpt-5.2"


def test_codex_app_runner_records_gui_model_source(tmp_path: Path):
    async def run() -> dict:
        with output_root_context(tmp_path):
            config = get_phase_config("03")
            config.workdir = str(tmp_path)
            config.runtime_env["SPECA_CODEX_MODEL"] = "gpt-5.5"
            config.runtime_env["SPECA_CODEX_MODEL_SOURCE"] = "codex-gui"
            config.runtime_env["SPECA_CODEX_REASONING_EFFORT"] = "xhigh"
            config.runtime_env["SPECA_CODEX_REASONING_EFFORT_SOURCE"] = "codex-gui"
            config.runtime_env["SPECA_CODEX_SERVICE_TIER"] = "fast"
            config.runtime_env["SPECA_CODEX_SERVICE_TIER_SOURCE"] = "codex-gui"
            runner = CodexAppRunner(config, asyncio.Semaphore(1))

            class FakeClient:
                async def run_turn(self, *, prompt, cwd, model, effort, service_tier, timeout_seconds, developer_instructions):
                    assert model == "gpt-5.5"
                    assert effort == "xhigh"
                    assert service_tier == "fast"
                    matches = re.findall(r"OUTPUT_FILE=(\S+)", prompt)
                    output_file = Path(matches[-1].strip('"'))
                    output_file.write_text(
                        json.dumps({"audit_items": [{"property_id": "p1"}]}),
                        encoding="utf-8",
                    )
                    capture = TurnCapture(thread_id="thread-1", turn_id="turn-1")
                    capture.completed = {"turn": {"status": "completed"}}
                    return {"thread": {"id": "thread-1"}}, capture

            async def fake_client():
                return FakeClient()

            runner._get_client = fake_client  # type: ignore[method-assign]
            await runner._execute_batch(
                [
                    {
                        "property_id": "p1",
                        "text": "x",
                        "type": "invariant",
                        "assertion": "x",
                        "severity": "Low",
                        "covers": [],
                        "reachability": "unknown",
                        "exploitability": "unknown",
                        "code_scope": {},
                        "code_excerpt": "",
                    }
                ],
                worker_id=0,
                batch_index=0,
            )
            metadata_files = list((tmp_path / "codex_app_threads").glob("*.json"))
            return json.loads(metadata_files[0].read_text(encoding="utf-8"))

    metadata = asyncio.run(run())

    assert metadata["requested_model"] == "gpt-5.5"
    assert metadata["model_source"] == "codex-gui"
    assert metadata["requested_effort"] == "xhigh"
    assert metadata["effort_source"] == "codex-gui"
    assert metadata["requested_service_tier"] == "fast"
    assert metadata["service_tier_source"] == "codex-gui"


def test_codex_app_client_omits_model_when_defaulting_to_app_server(tmp_path: Path):
    client = CodexAppServerClient(
        url="ws://127.0.0.1:1",
        cwd=tmp_path,
        timeout_seconds=1,
    )
    calls: list[tuple[str, dict]] = []

    async def fake_request(method: str, params=None):
        calls.append((method, params or {}))
        if method == "thread/start":
            return {"thread": {"id": "thread-1"}}
        if method == "turn/start":
            client._completed[("thread-1", "turn-1")] = {
                "threadId": "thread-1",
                "turn": {"id": "turn-1", "status": "completed"},
            }
            return {"turn": {"id": "turn-1"}}
        raise AssertionError(method)

    client.request = fake_request  # type: ignore[method-assign]

    asyncio.run(client.run_turn(
        prompt="hello",
        cwd=tmp_path,
        model=None,
        effort=None,
        service_tier=None,
        timeout_seconds=1,
        developer_instructions="dev",
    ))

    thread_params = calls[0][1]
    turn_params = calls[1][1]
    assert "model" not in thread_params
    assert "model" not in turn_params
    assert "effort" not in turn_params
    assert "serviceTier" not in thread_params
    assert "serviceTier" not in turn_params


def test_codex_app_client_sends_model_effort_and_service_tier(tmp_path: Path):
    client = CodexAppServerClient(
        url="ws://127.0.0.1:1",
        cwd=tmp_path,
        timeout_seconds=1,
    )
    calls: list[tuple[str, dict]] = []

    async def fake_request(method: str, params=None):
        calls.append((method, params or {}))
        if method == "thread/start":
            return {"thread": {"id": "thread-1"}}
        if method == "turn/start":
            client._completed[("thread-1", "turn-1")] = {
                "threadId": "thread-1",
                "turn": {"id": "turn-1", "status": "completed"},
            }
            return {"turn": {"id": "turn-1"}}
        raise AssertionError(method)

    client.request = fake_request  # type: ignore[method-assign]

    asyncio.run(client.run_turn(
        prompt="hello",
        cwd=tmp_path,
        model="gpt-5.5",
        effort="xhigh",
        service_tier="fast",
        timeout_seconds=1,
        developer_instructions="dev",
    ))

    thread_params = calls[0][1]
    turn_params = calls[1][1]
    assert thread_params["model"] == "gpt-5.5"
    assert thread_params["serviceTier"] == "fast"
    assert turn_params["model"] == "gpt-5.5"
    assert turn_params["effort"] == "xhigh"
    assert turn_params["serviceTier"] == "fast"
