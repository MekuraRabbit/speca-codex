"""Run status and SSE progress stream endpoints."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..models import RunResponse
from ..run_manager import RunManager

router = APIRouter(prefix="/api/runs", tags=["runs"])

# Injected at app startup
run_manager: RunManager | None = None


def _get_manager() -> RunManager:
    assert run_manager is not None
    return run_manager


@router.get("/")
async def list_runs() -> list[RunResponse]:
    mgr = _get_manager()
    return [
        RunResponse(
            run_id=r.run_id,
            phase_id=r.phase_id,
            status=r.status.value,
            created_at=r.created_at,
            completed_at=r.completed_at,
            error=r.error,
        )
        for r in mgr.list_runs()
    ]


@router.get("/{run_id}")
async def get_run(run_id: str) -> RunResponse:
    mgr = _get_manager()
    run = mgr.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunResponse(
        run_id=run.run_id,
        phase_id=run.phase_id,
        status=run.status.value,
        created_at=run.created_at,
        completed_at=run.completed_at,
        error=run.error,
        result=run.result,
    )


@router.get("/{run_id}/progress")
async def stream_progress(run_id: str) -> StreamingResponse:
    """SSE endpoint: streams real-time progress events for a run."""
    mgr = _get_manager()
    run = mgr.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    queue = run.bus.subscribe()

    async def event_generator():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue

                if event is None:
                    yield "event: done\ndata: {}\n\n"
                    break
                yield (
                    f"event: {event.type.value}\n"
                    f"data: {json.dumps(event.data)}\n\n"
                )
        except asyncio.CancelledError:
            pass
        finally:
            run.bus.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{run_id}/cancel")
async def cancel_run(run_id: str) -> dict[str, bool]:
    mgr = _get_manager()
    success = await mgr.cancel_run(run_id)
    if not success:
        raise HTTPException(status_code=404, detail="Run not found or not cancellable")
    return {"cancelled": True}
