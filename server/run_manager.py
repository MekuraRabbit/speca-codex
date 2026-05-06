"""In-memory run lifecycle manager (single-user)."""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from .progress import ProgressBus


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
    """Manages active and completed runs. Single-user, in-memory."""

    def __init__(self) -> None:
        self._runs: dict[str, RunInfo] = {}

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

        run_id = str(uuid.uuid4())[:8]
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
        return run

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
        run.status = RunStatus.CANCELLED
        run.completed_at = time.time()
        return True

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
