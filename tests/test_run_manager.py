"""Tests for app-server run lifecycle constraints."""

import pytest

from server.run_manager import RUN_ID_HEX_LENGTH, RunManager


def test_parallel_runs_allowed_for_distinct_output_dirs():
    manager = RunManager()

    first = manager.create_run("03", {"output_dir": "outputs/inst_01"})
    second = manager.create_run("03", {"output_dir": "outputs/inst_02"})

    assert first.run_id != second.run_id
    assert {run.output_dir for run in manager.active_runs} == {
        "outputs/inst_01",
        "outputs/inst_02",
    }


def test_run_ids_use_long_hex_prefixes():
    manager = RunManager()

    run = manager.create_run("03", {"output_dir": "outputs/inst_01"})

    assert len(run.run_id) == RUN_ID_HEX_LENGTH
    assert int(run.run_id, 16) >= 0
    assert "-" not in run.run_id


def test_run_id_generation_retries_on_collision(monkeypatch):
    class FakeUuid:
        def __init__(self, value: str) -> None:
            self.hex = value

    generated = iter([
        FakeUuid("a" * 32),
        FakeUuid("a" * 32),
        FakeUuid("b" * 32),
    ])
    monkeypatch.setattr("server.run_manager.uuid.uuid4", lambda: next(generated))
    manager = RunManager()

    first = manager.create_run("03", {"output_dir": "outputs/inst_01"})
    second = manager.create_run("03", {"output_dir": "outputs/inst_02"})

    assert first.run_id == "a" * RUN_ID_HEX_LENGTH
    assert second.run_id == "b" * RUN_ID_HEX_LENGTH


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
