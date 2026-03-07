"""Pydantic request/response models for the API."""

from __future__ import annotations

from pydantic import BaseModel
from typing import Any


class PhaseDispatchRequest(BaseModel):
    phase_id: str
    workers: int = 4
    max_concurrent: int = 8
    force: bool = False
    # Phase-specific inputs
    keywords: str | None = None
    spec_urls: str | None = None
    target_repo: str | None = None
    target_ref_type: str | None = None
    audit_scope: str | None = None
    min_severity: str | None = None


class RunResponse(BaseModel):
    run_id: str
    phase_id: str
    status: str
    created_at: float
    completed_at: float | None = None
    error: str | None = None
    result: dict[str, Any] | None = None


class PhaseInfo(BaseModel):
    phase_id: str
    name: str
    description: str
    depends_on: list[str]
    max_budget_usd: float
