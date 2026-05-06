"""Tests for the centralized output directory resolution (paths.py + resolve_pattern)."""

import os
from pathlib import Path

import pytest


def test_default_output_root():
    """Default OUTPUT_ROOT is 'outputs' when SPECA_OUTPUT_DIR is not set."""
    # Ensure env var is not set for this test
    env_backup = os.environ.pop("SPECA_OUTPUT_DIR", None)
    try:
        from scripts.orchestrator.paths import get_output_root
        assert get_output_root() == Path("outputs")
    finally:
        if env_backup is not None:
            os.environ["SPECA_OUTPUT_DIR"] = env_backup


def test_env_var_override(monkeypatch):
    """SPECA_OUTPUT_DIR overrides OUTPUT_ROOT."""
    monkeypatch.setenv("SPECA_OUTPUT_DIR", "outputs/instance_42")
    from scripts.orchestrator.paths import get_output_root
    assert get_output_root() == Path("outputs/instance_42")


def test_context_override_beats_env(monkeypatch):
    """Task-local output root overrides SPECA_OUTPUT_DIR."""
    monkeypatch.setenv("SPECA_OUTPUT_DIR", "outputs/from_env")
    from scripts.orchestrator.paths import get_output_root, output_root_context

    with output_root_context("outputs/from_context"):
        assert get_output_root() == Path("outputs/from_context")

    assert get_output_root() == Path("outputs/from_env")


def test_resolve_pattern_default():
    """resolve_pattern with default root is identity."""
    env_backup = os.environ.pop("SPECA_OUTPUT_DIR", None)
    try:
        from scripts.orchestrator.config import resolve_pattern
        assert resolve_pattern("outputs/01a_STATE.json") == "outputs/01a_STATE.json"
        assert resolve_pattern("outputs/01b_PARTIAL_*.json") == "outputs/01b_PARTIAL_*.json"
    finally:
        if env_backup is not None:
            os.environ["SPECA_OUTPUT_DIR"] = env_backup


def test_resolve_pattern_custom(monkeypatch):
    """resolve_pattern replaces outputs/ prefix with custom dir."""
    monkeypatch.setenv("SPECA_OUTPUT_DIR", "outputs/inst_01")
    from scripts.orchestrator.config import resolve_pattern
    assert resolve_pattern("outputs/01a_STATE.json") == "outputs/inst_01/01a_STATE.json"
    assert resolve_pattern("outputs/01e_PARTIAL_*.json") == "outputs/inst_01/01e_PARTIAL_*.json"
    assert resolve_pattern("outputs/BUG_BOUNTY_SCOPE.json") == "outputs/inst_01/BUG_BOUNTY_SCOPE.json"


def test_resolve_pattern_no_prefix():
    """resolve_pattern leaves non-outputs patterns unchanged."""
    from scripts.orchestrator.config import resolve_pattern
    assert resolve_pattern("some/other/path.json") == "some/other/path.json"
    assert resolve_pattern("") == ""


def test_backward_compatibility():
    """When SPECA_OUTPUT_DIR is not set, all paths resolve to 'outputs/'."""
    env_backup = os.environ.pop("SPECA_OUTPUT_DIR", None)
    try:
        from scripts.orchestrator.paths import get_output_root
        from scripts.orchestrator.config import resolve_pattern

        root = get_output_root()
        assert root == Path("outputs")

        # All config patterns should resolve to themselves
        test_patterns = [
            "outputs/01a_STATE.json",
            "outputs/01b_QUEUE_{worker_id}.json",
            "outputs/01e_PARTIAL_*.json",
            "outputs/02c_PARTIAL_*.json",
            "outputs/03_PARTIAL_*.json",
            "outputs/04_PARTIAL_*.json",
        ]
        for pattern in test_patterns:
            assert resolve_pattern(pattern) == pattern, f"Pattern {pattern} should be unchanged"
    finally:
        if env_backup is not None:
            os.environ["SPECA_OUTPUT_DIR"] = env_backup
