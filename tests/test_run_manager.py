"""Tests for app-server run lifecycle constraints."""

import pytest

from server.run_manager import RunManager


def test_parallel_runs_allowed_for_distinct_output_dirs():
    manager = RunManager()

    first = manager.create_run("03", {"output_dir": "outputs/inst_01"})
    second = manager.create_run("03", {"output_dir": "outputs/inst_02"})

    assert first.run_id != second.run_id
    assert {run.output_dir for run in manager.active_runs} == {
        "outputs/inst_01",
        "outputs/inst_02",
    }


def test_active_run_rejected_for_same_output_dir():
    manager = RunManager()
    manager.create_run("03", {"output_dir": "outputs/inst_01"})

    with pytest.raises(RuntimeError, match="output_dir"):
        manager.create_run("04", {"output_dir": "outputs/inst_01"})


def test_active_run_rejected_for_same_output_dir_with_different_spelling():
    manager = RunManager()
    manager.create_run("03", {"output_dir": "outputs/inst_01"})

    with pytest.raises(RuntimeError, match="output_dir"):
        manager.create_run("04", {"output_dir": "./outputs/inst_01"})


def test_output_dir_reusable_after_completion():
    manager = RunManager()
    first = manager.create_run("03", {"output_dir": "outputs/inst_01"})
    manager.mark_complete(first.run_id)

    second = manager.create_run("04", {"output_dir": "outputs/inst_01"})

    assert second.output_dir == "outputs/inst_01"
