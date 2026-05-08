"""Pydantic request/response models for the API."""

from __future__ import annotations

import os
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator

from .path_safety import normalize_output_dir, normalize_worktree_root


_TRUTHY = {"1", "true", "yes", "on"}


class PhaseDispatchRequest(BaseModel):
    phase_id: str
    workers: int = Field(default=4, ge=1, le=64)
    max_concurrent: int = Field(default=8, ge=1, le=64)
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

    @field_validator("phase_id")
    @classmethod
    def validate_phase_id(cls, value: str) -> str:
        from scripts.orchestrator.config import PHASE_CONFIGS

        if value not in PHASE_CONFIGS:
            allowed = ", ".join(PHASE_CONFIGS)
            raise ValueError(f"unknown phase_id '{value}'; expected one of: {allowed}")
        return value

    @field_validator("output_dir")
    @classmethod
    def validate_output_dir(cls, value: str | None) -> str | None:
        return normalize_output_dir(value)

    @field_validator("worktree_root")
    @classmethod
    def validate_worktree_root(cls, value: str | None) -> str | None:
        return normalize_worktree_root(value)

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

    @model_validator(mode="after")
    def validate_api_runner_dispatch(self) -> "PhaseDispatchRequest":
        runner = (self.runner or "").replace("_", "-").lower()
        if runner != "api":
            if self.api_base_url or self.api_key_env:
                raise ValueError("api_base_url/api_key_env require runner='api'")
            return self

        if os.environ.get("SPECA_ENABLE_API_RUNNER_DISPATCH", "").lower() not in _TRUTHY:
            raise ValueError(
                "API runner dispatch is disabled by default; set "
                "SPECA_ENABLE_API_RUNNER_DISPATCH=1 to opt in"
            )

        if self.api_base_url:
            allowed_bases = _csv_env("SPECA_API_RUNNER_BASE_URL_ALLOWLIST")
            if self.api_base_url not in allowed_bases:
                raise ValueError(
                    "api_base_url must be listed in "
                    "SPECA_API_RUNNER_BASE_URL_ALLOWLIST"
                )

        if self.api_key_env:
            allowed_keys = _csv_env("SPECA_API_RUNNER_KEY_ENV_ALLOWLIST")
            if self.api_key_env not in allowed_keys:
                raise ValueError(
                    "api_key_env must be listed in "
                    "SPECA_API_RUNNER_KEY_ENV_ALLOWLIST"
                )

        return self


def _csv_env(name: str) -> set[str]:
    return {
        item.strip()
        for item in os.environ.get(name, "").split(",")
        if item.strip()
    }


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
