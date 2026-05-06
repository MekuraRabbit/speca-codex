"""Pydantic request/response models for the API."""

from __future__ import annotations

from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, field_validator


class PhaseDispatchRequest(BaseModel):
    phase_id: str
    workers: int = 4
    max_concurrent: int = 8
    force: bool = False
    output_dir: str | None = None
    runner: Literal[
        "codex-app",
        "codex_app",
        "app-server",
        "app_server",
        "codex",
        "claude",
        "api",
    ] | None = None
    model: str | None = None
    app_server_url: str | None = None
    isolated_worktrees: bool = False
    worktree_root: str | None = None
    worktree_base_ref: str | None = None
    api_base_url: str | None = None
    api_key_env: str | None = None
    reasoning_effort: Literal[
        "none",
        "minimal",
        "low",
        "medium",
        "high",
        "xhigh",
    ] | None = None
    service_tier: Literal["fast", "flex"] | None = None
    use_codex_gui_model: bool = True
    use_codex_gui_reasoning_effort: bool = True
    use_codex_gui_service_tier: bool = True
    codex_thread_id: str | None = None
    # Phase-specific inputs
    keywords: str | None = None
    spec_urls: str | None = None
    target_repo: str | None = None
    target_ref_type: str | None = None
    audit_scope: str | None = None
    min_severity: str | None = None

    @field_validator("app_server_url")
    @classmethod
    def validate_app_server_url(cls, value: str | None) -> str | None:
        if value is None:
            return value

        parsed = urlparse(value)
        if parsed.scheme not in {"ws", "wss"}:
            raise ValueError("app_server_url must use ws:// or wss://")

        if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("app_server_url must point to a loopback host")

        return value


class RunResponse(BaseModel):
    run_id: str
    phase_id: str
    output_dir: str
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
