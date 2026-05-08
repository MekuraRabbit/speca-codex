"""Tests for API request models."""

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from server.models import PhaseDispatchRequest
from server.app import resolve_api_bind_host


@pytest.mark.parametrize(
    "url",
    [
        "ws://127.0.0.1:8001",
        "ws://localhost:8001",
        "ws://[::1]:8001",
        "wss://localhost:8001",
    ],
)
def test_phase_dispatch_accepts_loopback_app_server_urls(url: str):
    request = PhaseDispatchRequest(phase_id="03", app_server_url=url)

    assert request.app_server_url == url


def test_phase_dispatch_rejects_unknown_phase_id():
    with pytest.raises(ValidationError):
        PhaseDispatchRequest(phase_id="99")


def test_phase_dispatch_validator_resolves_config_without_repo_root(monkeypatch):
    repo_root = Path(__file__).resolve().parents[1]
    scripts_dir = str(repo_root / "scripts")
    module_names = (
        "scripts",
        "scripts.orchestrator",
        "scripts.orchestrator.config",
        "orchestrator",
        "orchestrator.config",
    )
    saved_modules = {
        name: sys.modules.pop(name, None)
        for name in module_names
    }

    try:
        monkeypatch.setattr(
            sys,
            "path",
            [
                entry
                for entry in sys.path
                if Path(entry or ".").resolve() != repo_root
            ],
        )
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)

        request = PhaseDispatchRequest(phase_id="03")

        assert request.phase_id == "03"
        assert "orchestrator.config" in sys.modules
        assert "scripts.orchestrator.config" not in sys.modules
    finally:
        for name in module_names:
            sys.modules.pop(name, None)
        sys.modules.update(
            {
                name: module
                for name, module in saved_modules.items()
                if module is not None
            }
        )


def test_phase_dispatch_enables_codex_gui_model_by_default():
    request = PhaseDispatchRequest(phase_id="03")

    assert request.use_codex_gui_model is True
    assert request.use_codex_gui_reasoning_effort is True
    assert request.use_codex_gui_service_tier is True


def test_phase_dispatch_accepts_codex_thread_id():
    request = PhaseDispatchRequest(phase_id="03", codex_thread_id="thread-123")

    assert request.codex_thread_id == "thread-123"


def test_phase_dispatch_accepts_codex_effort_and_service_tier():
    request = PhaseDispatchRequest(
        phase_id="03",
        reasoning_effort="xhigh",
        service_tier="fast",
    )

    assert request.reasoning_effort == "xhigh"
    assert request.service_tier == "fast"


def test_phase_dispatch_normalizes_output_dir():
    request = PhaseDispatchRequest(
        phase_id="03",
        output_dir="./outputs/inst_01",
    )

    assert request.output_dir == "outputs/inst_01"


@pytest.mark.parametrize(
    "output_dir",
    [
        "",
        "../outputs/inst_01",
        "outputs/../inst_01",
        "not_outputs/inst_01",
    ],
)
def test_phase_dispatch_rejects_unsafe_output_dirs(output_dir: str):
    with pytest.raises(ValidationError):
        PhaseDispatchRequest(phase_id="03", output_dir=output_dir)


def test_phase_dispatch_rejects_absolute_output_dir(tmp_path):
    with pytest.raises(ValidationError):
        PhaseDispatchRequest(phase_id="03", output_dir=str(tmp_path))


def test_phase_dispatch_normalizes_worktree_root():
    request = PhaseDispatchRequest(
        phase_id="03",
        worktree_root=".codex/worktrees/run_a",
    )

    assert request.worktree_root == ".codex/worktrees/run_a"


@pytest.mark.parametrize(
    "worktree_root",
    [
        "../.codex/worktrees",
        ".codex/../worktrees",
        "target_workspace/worktrees",
    ],
)
def test_phase_dispatch_rejects_unsafe_worktree_roots(worktree_root: str):
    with pytest.raises(ValidationError):
        PhaseDispatchRequest(phase_id="03", worktree_root=worktree_root)


def test_phase_dispatch_caps_worker_counts():
    with pytest.raises(ValidationError):
        PhaseDispatchRequest(phase_id="03", workers=65)

    with pytest.raises(ValidationError):
        PhaseDispatchRequest(phase_id="03", max_concurrent=65)


def test_phase_dispatch_rejects_api_fields_without_api_runner():
    with pytest.raises(ValidationError):
        PhaseDispatchRequest(
            phase_id="03",
            runner="codex-app",
            api_base_url="https://example.invalid/v1",
        )


def test_phase_dispatch_rejects_api_runner_by_default(monkeypatch):
    monkeypatch.delenv("SPECA_ENABLE_API_RUNNER_DISPATCH", raising=False)

    with pytest.raises(ValidationError):
        PhaseDispatchRequest(phase_id="03", runner="api")


def test_phase_dispatch_accepts_explicitly_allowlisted_api_runner(monkeypatch):
    monkeypatch.setenv("SPECA_ENABLE_API_RUNNER_DISPATCH", "1")
    monkeypatch.setenv(
        "SPECA_API_RUNNER_BASE_URL_ALLOWLIST",
        "https://api.example.invalid/v1",
    )
    monkeypatch.setenv("SPECA_API_RUNNER_KEY_ENV_ALLOWLIST", "API_RUNNER_KEY")

    request = PhaseDispatchRequest(
        phase_id="03",
        runner="api",
        api_base_url="https://api.example.invalid/v1",
        api_key_env="API_RUNNER_KEY",
    )

    assert request.runner == "api"


def test_phase_dispatch_rejects_unallowlisted_api_runner_fields(monkeypatch):
    monkeypatch.setenv("SPECA_ENABLE_API_RUNNER_DISPATCH", "1")
    monkeypatch.setenv(
        "SPECA_API_RUNNER_BASE_URL_ALLOWLIST",
        "https://allowed.example.invalid/v1",
    )

    with pytest.raises(ValidationError):
        PhaseDispatchRequest(
            phase_id="03",
            runner="api",
            api_base_url="https://blocked.example.invalid/v1",
        )


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8001",
        "ws://example.com:8001",
        "ws://192.168.1.10:8001",
    ],
)
def test_phase_dispatch_rejects_non_loopback_app_server_urls(url: str):
    with pytest.raises(ValidationError):
        PhaseDispatchRequest(phase_id="03", app_server_url=url)


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1", "[::1]"])
def test_api_bind_host_allows_loopback(host: str):
    assert resolve_api_bind_host(host) == host


@pytest.mark.parametrize("host", ["0.0.0.0", "", "192.168.1.10", "example.com"])
def test_api_bind_host_rejects_non_loopback_by_default(host: str):
    with pytest.raises(RuntimeError):
        resolve_api_bind_host(host)


def test_api_bind_host_accepts_non_loopback_with_explicit_remote_opt_in():
    assert resolve_api_bind_host("0.0.0.0", remote_enabled=True) == "0.0.0.0"
