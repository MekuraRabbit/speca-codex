"""Tests for per-run PhaseConfig isolation."""

from scripts.orchestrator.config import get_phase_config


def test_get_phase_config_returns_isolated_copy():
    first = get_phase_config("03")
    second = get_phase_config("03")

    first.model = "custom-model"
    first.runtime_env["API_RUNNER_MODEL"] = "gpt-test"

    assert second.model == "sonnet"
    assert "API_RUNNER_MODEL" not in second.runtime_env
