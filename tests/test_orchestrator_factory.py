import asyncio

import pytest

from scripts.orchestrator.base import (
    BaseOrchestrator,
    Phase01Orchestrator,
    Phase02cOrchestrator,
    Phase03Orchestrator,
    Phase04Orchestrator,
    resolve_runner_type,
)
from scripts.orchestrator.codex_app_runner import CodexAppRunner
from scripts.orchestrator.codex_runner import CodexRunner
from scripts.orchestrator.factory import create_orchestrator


@pytest.mark.parametrize(
    ("phase_id", "expected_type"),
    [
        ("01a", Phase01Orchestrator),
        ("02c", Phase02cOrchestrator),
        ("03", Phase03Orchestrator),
        ("04", Phase04Orchestrator),
        ("05", BaseOrchestrator),
    ],
)
def test_create_orchestrator_selects_phase_specific_classes(phase_id, expected_type):
    orchestrator = create_orchestrator(phase_id, num_workers=2, max_concurrent=3)

    assert type(orchestrator) is expected_type
    assert orchestrator.num_workers == 2
    assert orchestrator.max_concurrent == 3


def test_create_orchestrator_rejects_unknown_phase():
    with pytest.raises(ValueError, match="Unknown phase"):
        create_orchestrator("99")


def test_orchestrator_defaults_to_codex_app_runner(monkeypatch):
    monkeypatch.delenv("ORCHESTRATOR_RUNNER", raising=False)

    orchestrator = BaseOrchestrator("01a", num_workers=1, max_concurrent=1)
    monkeypatch.setattr(orchestrator, "load_items", lambda: [])

    asyncio.run(orchestrator.run())

    assert resolve_runner_type(orchestrator.config) == "codex-app"
    assert isinstance(orchestrator.runner, CodexAppRunner)


def test_orchestrator_runner_env_override_still_works(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_RUNNER", "codex")

    orchestrator = BaseOrchestrator("01a", num_workers=1, max_concurrent=1)
    monkeypatch.setattr(orchestrator, "load_items", lambda: [])

    asyncio.run(orchestrator.run())

    assert resolve_runner_type(orchestrator.config) == "codex"
    assert isinstance(orchestrator.runner, CodexRunner)
