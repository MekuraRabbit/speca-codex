"""Tests for app-server run lifecycle constraints."""

import json
import os

import pytest

from server.run_manager import (
    RUN_ID_HEX_LENGTH,
    RUN_INFO_FILENAME,
    STALE_RUN_ERROR,
    RunManager,
    RunStatus,
)


def test_parallel_runs_allowed_for_distinct_output_dirs(tmp_path):
    manager = RunManager()
    first_output = str(tmp_path / "outputs" / "inst_01")
    second_output = str(tmp_path / "outputs" / "inst_02")

    first = manager.create_run("03", {"output_dir": first_output})
    second = manager.create_run("03", {"output_dir": second_output})

    assert first.run_id != second.run_id
    assert {run.output_dir for run in manager.active_runs} == {
        first_output,
        second_output,
    }


def test_run_ids_use_long_hex_prefixes(tmp_path):
    manager = RunManager()

    run = manager.create_run(
        "03",
        {"output_dir": str(tmp_path / "outputs" / "inst_01")},
    )

    assert len(run.run_id) == RUN_ID_HEX_LENGTH
    assert int(run.run_id, 16) >= 0
    assert "-" not in run.run_id


def test_run_id_generation_retries_on_collision(monkeypatch, tmp_path):
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

    first = manager.create_run(
        "03",
        {"output_dir": str(tmp_path / "outputs" / "inst_01")},
    )
    second = manager.create_run(
        "03",
        {"output_dir": str(tmp_path / "outputs" / "inst_02")},
    )

    assert first.run_id == "a" * RUN_ID_HEX_LENGTH
    assert second.run_id == "b" * RUN_ID_HEX_LENGTH


def test_create_run_writes_run_info_index(tmp_path):
    manager = RunManager()
    output_dir = tmp_path / "outputs" / "inst_01"

    run = manager.create_run("03", {"output_dir": str(output_dir), "workers": 2})

    data = json.loads((output_dir / RUN_INFO_FILENAME).read_text(encoding="utf-8"))
    assert data["run_id"] == run.run_id
    assert data["phase_id"] == "03"
    assert data["output_dir"] == str(output_dir)
    assert data["status"] == "queued"
    assert data["inputs"]["workers"] == 2


def test_run_info_index_updates_on_status_transitions(tmp_path):
    manager = RunManager()
    output_dir = tmp_path / "outputs" / "inst_01"
    run = manager.create_run("03", {"output_dir": str(output_dir)})

    manager.mark_running(run.run_id)
    running = json.loads((output_dir / RUN_INFO_FILENAME).read_text(encoding="utf-8"))
    assert running["status"] == "running"

    manager.mark_complete(run.run_id, result={"total_results": 3})
    completed = json.loads((output_dir / RUN_INFO_FILENAME).read_text(encoding="utf-8"))
    assert completed["status"] == "completed"
    assert completed["completed_at"] is not None
    assert completed["result"] == {"total_results": 3}


def test_load_existing_run_indexes_restores_completed_runs(tmp_path):
    output_root = tmp_path / "outputs"
    first_manager = RunManager()
    run = first_manager.create_run("03", {"output_dir": str(output_root / "inst_01")})
    first_manager.mark_complete(run.run_id, result={"total_results": 3})

    restored_manager = RunManager(load_existing=True, output_root=output_root)
    restored = restored_manager.get_run(run.run_id)

    assert restored is not None
    assert restored.status == RunStatus.COMPLETED
    assert restored.result == {"total_results": 3}
    assert restored.task is None


def test_load_existing_run_indexes_marks_active_runs_failed(tmp_path):
    output_root = tmp_path / "outputs"
    output_dir = output_root / "inst_01"
    output_dir.mkdir(parents=True)
    index_path = output_dir / RUN_INFO_FILENAME
    index_path.write_text(
        json.dumps({
            "run_id": "a" * RUN_ID_HEX_LENGTH,
            "phase_id": "03",
            "output_dir": str(output_dir),
            "status": "running",
            "created_at": 123.0,
            "completed_at": None,
            "error": None,
            "result": None,
            "inputs": {"output_dir": str(output_dir)},
        }),
        encoding="utf-8",
    )

    manager = RunManager(load_existing=True, output_root=output_root)
    restored = manager.get_run("a" * RUN_ID_HEX_LENGTH)

    assert restored is not None
    assert restored.status == RunStatus.FAILED
    assert restored.error == STALE_RUN_ERROR
    assert restored.completed_at is not None
    persisted = json.loads(index_path.read_text(encoding="utf-8"))
    assert persisted["status"] == "failed"
    assert persisted["error"] == STALE_RUN_ERROR


def test_load_existing_run_indexes_ignores_mismatched_output_dir(tmp_path):
    output_root = tmp_path / "outputs"
    output_dir = output_root / "inst_01"
    output_dir.mkdir(parents=True)
    (output_dir / RUN_INFO_FILENAME).write_text(
        json.dumps({
            "run_id": "a" * RUN_ID_HEX_LENGTH,
            "phase_id": "03",
            "output_dir": str(tmp_path / "elsewhere"),
            "status": "completed",
            "created_at": 123.0,
            "completed_at": 456.0,
            "error": None,
            "result": None,
            "inputs": {},
        }),
        encoding="utf-8",
    )

    manager = RunManager(load_existing=True, output_root=output_root)

    assert manager.list_runs() == []


def test_active_run_rejected_for_same_output_dir(tmp_path):
    manager = RunManager()
    output_dir = str(tmp_path / "outputs" / "inst_01")
    manager.create_run("03", {"output_dir": output_dir})

    with pytest.raises(RuntimeError, match="output_dir"):
        manager.create_run("04", {"output_dir": output_dir})


def test_active_run_rejected_for_same_output_dir_with_different_spelling(tmp_path):
    manager = RunManager()
    output_dir = tmp_path / "outputs" / "inst_01"
    manager.create_run("03", {"output_dir": str(output_dir)})

    with pytest.raises(RuntimeError, match="output_dir"):
        manager.create_run(
            "04",
            {"output_dir": f"{output_dir.parent}{os.sep}.{os.sep}{output_dir.name}"},
        )


def test_output_dir_reusable_after_completion(tmp_path):
    manager = RunManager()
    output_dir = str(tmp_path / "outputs" / "inst_01")
    first = manager.create_run("03", {"output_dir": output_dir})
    manager.mark_complete(first.run_id)

    second = manager.create_run("04", {"output_dir": output_dir})

    assert second.output_dir == output_dir
