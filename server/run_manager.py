"""Run lifecycle manager with lightweight output-dir indexes."""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from .progress import ProgressBus


RUN_ID_HEX_LENGTH = 16
RUN_INFO_FILENAME = "RUN_INFO.json"
STALE_RUN_ERROR = "Server restarted before this run completed"


class RunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class RunInfo:
    run_id: str
    phase_id: str
    output_dir: str
    status: RunStatus
    created_at: float
    inputs: dict[str, Any]
    bus: ProgressBus
    task: asyncio.Task[None] | None = None
    error: str | None = None
    result: dict[str, Any] | None = None
    completed_at: float | None = None


class RunManager:
    """Manages active and completed single-user runs."""

    def __init__(
        self,
        *,
        load_existing: bool = False,
        output_root: str | Path = "outputs",
    ) -> None:
        self._runs: dict[str, RunInfo] = {}
        if load_existing:
            self._load_run_indexes(Path(output_root))

    @property
    def active_run(self) -> RunInfo | None:
        for run in self._runs.values():
            if run.status in {RunStatus.QUEUED, RunStatus.RUNNING}:
                return run
        return None

    @property
    def active_runs(self) -> list[RunInfo]:
        return [
            run
            for run in self._runs.values()
            if run.status in {RunStatus.QUEUED, RunStatus.RUNNING}
        ]

    def create_run(self, phase_id: str, inputs: dict[str, Any]) -> RunInfo:
        output_dir = str(inputs.get("output_dir") or "outputs")
        output_key = self._output_dir_key(output_dir)
        for active in self.active_runs:
            if self._output_dir_key(active.output_dir) == output_key:
                raise RuntimeError(
                    f"A run is already active for output_dir={output_dir!r}"
                )

        run_id = self._generate_run_id()
        bus = ProgressBus()
        run = RunInfo(
            run_id=run_id,
            phase_id=phase_id,
            output_dir=output_dir,
            status=RunStatus.QUEUED,
            created_at=time.time(),
            inputs=inputs,
            bus=bus,
        )
        self._runs[run_id] = run
        self._persist_run(run)
        return run

    def _generate_run_id(self) -> str:
        while True:
            run_id = uuid.uuid4().hex[:RUN_ID_HEX_LENGTH]
            if run_id not in self._runs:
                return run_id

    @staticmethod
    def _output_dir_key(output_dir: str) -> str:
        return str(Path(output_dir).expanduser().resolve()).lower()

    def get_run(self, run_id: str) -> RunInfo | None:
        return self._runs.get(run_id)

    def list_runs(self) -> list[RunInfo]:
        return sorted(self._runs.values(), key=lambda r: r.created_at, reverse=True)

    async def cancel_run(self, run_id: str) -> bool:
        run = self._runs.get(run_id)
        if not run or not run.task:
            return False
        run.task.cancel()
        self.mark_cancelled(run_id)
        return True

    def mark_running(self, run_id: str) -> None:
        run = self._runs.get(run_id)
        if run:
            run.status = RunStatus.RUNNING
            self._persist_run(run)

    def mark_cancelled(self, run_id: str) -> None:
        run = self._runs.get(run_id)
        if run:
            run.status = RunStatus.CANCELLED
            run.completed_at = time.time()
            self._persist_run(run)

    def mark_complete(
        self,
        run_id: str,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        run = self._runs.get(run_id)
        if run:
            run.status = RunStatus.FAILED if error else RunStatus.COMPLETED
            run.error = error
            run.result = result
            run.completed_at = time.time()
            self._persist_run(run)

    def _load_run_indexes(self, output_root: Path) -> None:
        if not output_root.exists():
            return
        for path in sorted(output_root.glob(f"**/{RUN_INFO_FILENAME}")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                run = self._run_from_index(data)
            except (OSError, json.JSONDecodeError, KeyError, ValueError, TypeError):
                continue
            if Path(run.output_dir).resolve() != path.parent.resolve():
                continue
            existing = self._runs.get(run.run_id)
            if existing and existing.created_at >= run.created_at:
                continue
            self._runs[run.run_id] = run
            if run.status in {RunStatus.QUEUED, RunStatus.RUNNING}:
                run.status = RunStatus.FAILED
                run.error = run.error or STALE_RUN_ERROR
                run.completed_at = run.completed_at or time.time()
                self._persist_run(run)

    def _run_from_index(self, data: dict[str, Any]) -> RunInfo:
        completed_at = data.get("completed_at")
        return RunInfo(
            run_id=str(data["run_id"]),
            phase_id=str(data["phase_id"]),
            output_dir=str(data["output_dir"]),
            status=RunStatus(str(data["status"])),
            created_at=float(data["created_at"]),
            inputs=dict(data.get("inputs") or {}),
            bus=ProgressBus(),
            error=data.get("error"),
            result=data.get("result"),
            completed_at=float(completed_at) if completed_at is not None else None,
        )

    def _persist_run(self, run: RunInfo) -> None:
        path = Path(run.output_dir) / RUN_INFO_FILENAME
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "run_id": run.run_id,
            "phase_id": run.phase_id,
            "output_dir": run.output_dir,
            "status": run.status.value,
            "created_at": run.created_at,
            "completed_at": run.completed_at,
            "error": run.error,
            "result": run.result,
            "inputs": run.inputs,
        }
        tmp_path = path.with_name(f".{path.name}.tmp")
        tmp_path.write_text(
            json.dumps(data, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        tmp_path.replace(path)
