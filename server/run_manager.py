"""In-memory run lifecycle manager (single-user)."""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
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
        self._active_run_id: str | None = None

    @property
    def active_run(self) -> RunInfo | None:
        if self._active_run_id:
            return self._runs.get(self._active_run_id)
        return None

    def create_run(self, phase_id: str, inputs: dict[str, Any]) -> RunInfo:
        if self._active_run_id:
            active = self._runs.get(self._active_run_id)
            if active and active.status == RunStatus.RUNNING:
                raise RuntimeError("A run is already active")

        run_id = str(uuid.uuid4())[:8]
        bus = ProgressBus()
        run = RunInfo(
            run_id=run_id,
            phase_id=phase_id,
            status=RunStatus.QUEUED,
            created_at=time.time(),
            inputs=inputs,
            bus=bus,
        )
        self._runs[run_id] = run
        self._active_run_id = run_id
        return run

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
        if self._active_run_id == run_id:
            self._active_run_id = None
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
            if self._active_run_id == run_id:
                self._active_run_id = None
