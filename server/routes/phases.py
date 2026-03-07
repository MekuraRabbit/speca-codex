"""Phase dispatch and listing endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..models import PhaseDispatchRequest, RunResponse, PhaseInfo
from ..run_manager import RunManager
from ..orchestrator_bridge import launch_phase

router = APIRouter(prefix="/api/phases", tags=["phases"])

# Injected at app startup
run_manager: RunManager | None = None


def _get_manager() -> RunManager:
    assert run_manager is not None
    return run_manager


@router.get("/")
async def list_phases() -> list[PhaseInfo]:
    import sys
    from pathlib import Path
    _scripts_dir = str(Path(__file__).resolve().parent.parent.parent / "scripts")
    if _scripts_dir not in sys.path:
        sys.path.insert(0, _scripts_dir)
    from orchestrator.config import PHASE_CONFIGS

    return [
        PhaseInfo(
            phase_id=c.phase_id,
            name=c.name,
            description=c.description,
            depends_on=c.depends_on,
            max_budget_usd=c.max_budget_usd,
        )
        for c in PHASE_CONFIGS.values()
    ]


@router.post("/dispatch")
async def dispatch_phase(req: PhaseDispatchRequest) -> RunResponse:
    mgr = _get_manager()
    try:
        run = mgr.create_run(req.phase_id, req.model_dump())
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))

    await launch_phase(run, mgr)

    return RunResponse(
        run_id=run.run_id,
        phase_id=run.phase_id,
        status=run.status.value,
        created_at=run.created_at,
    )
