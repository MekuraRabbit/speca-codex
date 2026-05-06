"""Resolve the Codex App GUI-selected model when available."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


_REASONING_EFFORTS = {"none", "minimal", "low", "medium", "high", "xhigh"}
_SERVICE_TIERS = {"fast", "flex"}


@dataclass(frozen=True)
class CodexGuiSettings:
    """Codex App settings discovered from local session metadata."""

    model: str | None = None
    reasoning_effort: str | None = None
    service_tier: str | None = None


def resolve_codex_gui_model(
    env: Mapping[str, str] | None = None,
    *,
    sessions_root: Path | None = None,
) -> str | None:
    """Return the latest model recorded for the current Codex App thread.

    Codex Desktop records turn context in ``$CODEX_HOME/sessions``. When SPECA's
    local API is launched from Codex App, ``CODEX_THREAD_ID`` points at the
    current thread, so the latest ``turn_context.payload.model`` mirrors the
    GUI-selected model for that thread. If any piece is missing, callers should
    fall back to the app-server default.
    """
    return resolve_codex_gui_settings(env, sessions_root=sessions_root).model


def resolve_codex_gui_settings(
    env: Mapping[str, str] | None = None,
    *,
    sessions_root: Path | None = None,
) -> CodexGuiSettings:
    """Return Codex App model settings recorded for the current thread."""
    env = os.environ if env is None else env

    env_settings = CodexGuiSettings(
        model=_first_clean(env, ("SPECA_CODEX_GUI_MODEL", "CODEX_SELECTED_MODEL")),
        reasoning_effort=_first_reasoning_effort(
            env,
            (
                "SPECA_CODEX_GUI_REASONING_EFFORT",
                "SPECA_CODEX_REASONING_EFFORT",
                "CODEX_REASONING_EFFORT",
            ),
        ),
        service_tier=_first_service_tier(
            env,
            (
                "SPECA_CODEX_GUI_SERVICE_TIER",
                "SPECA_CODEX_GUI_SPEED_TIER",
                "SPECA_CODEX_SERVICE_TIER",
                "SPECA_CODEX_SPEED_TIER",
                "CODEX_SERVICE_TIER",
                "CODEX_SPEED_TIER",
            ),
        ),
    )

    thread_id = _clean_model(
        env.get("SPECA_CODEX_THREAD_ID") or env.get("CODEX_THREAD_ID")
    )
    if not thread_id:
        return env_settings

    root = sessions_root or _default_sessions_root(env)
    if not root.exists():
        return env_settings

    session_file = _find_thread_session(root, thread_id)
    if session_file is None:
        return env_settings

    session_settings = _latest_settings_from_session(session_file)
    return CodexGuiSettings(
        model=env_settings.model or session_settings.model,
        reasoning_effort=(
            env_settings.reasoning_effort or session_settings.reasoning_effort
        ),
        service_tier=env_settings.service_tier or session_settings.service_tier,
    )


def _default_sessions_root(env: Mapping[str, str]) -> Path:
    codex_home = env.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home) / "sessions"
    return Path.home() / ".codex" / "sessions"


def _find_thread_session(root: Path, thread_id: str) -> Path | None:
    direct_matches = sorted(root.rglob(f"*{thread_id}*.jsonl"))
    if direct_matches:
        return max(direct_matches, key=lambda path: path.stat().st_mtime)
    return None


def _latest_settings_from_session(path: Path) -> CodexGuiSettings:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return CodexGuiSettings()

    for line in reversed(lines):
        if '"turn_context"' not in line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") != "turn_context":
            continue
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        model = _clean_model(payload.get("model"))
        reasoning_effort = _clean_reasoning_effort(payload.get("effort"))
        service_tier = _clean_service_tier(
            _first_mapping_value(
                payload,
                ("serviceTier", "service_tier", "speedTier", "speed_tier"),
            )
        )
        collaboration_mode = payload.get("collaboration_mode")
        if isinstance(collaboration_mode, dict):
            settings = collaboration_mode.get("settings")
            if isinstance(settings, dict):
                model = model or _clean_model(settings.get("model"))
                reasoning_effort = reasoning_effort or _clean_reasoning_effort(
                    settings.get("reasoning_effort")
                )
                service_tier = service_tier or _clean_service_tier(
                    _first_mapping_value(
                        settings,
                        (
                            "serviceTier",
                            "service_tier",
                            "speedTier",
                            "speed_tier",
                        ),
                    )
                )
        if model or reasoning_effort or service_tier:
            return CodexGuiSettings(
                model=model,
                reasoning_effort=reasoning_effort,
                service_tier=service_tier,
            )
    return CodexGuiSettings()


def _first_clean(env: Mapping[str, str], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = _clean_model(env.get(key))
        if value:
            return value
    return None


def _first_reasoning_effort(
    env: Mapping[str, str],
    keys: tuple[str, ...],
) -> str | None:
    for key in keys:
        value = _clean_reasoning_effort(env.get(key))
        if value:
            return value
    return None


def _first_service_tier(
    env: Mapping[str, str],
    keys: tuple[str, ...],
) -> str | None:
    for key in keys:
        value = _clean_service_tier(env.get(key))
        if value:
            return value
    return None


def _first_mapping_value(mapping: Mapping[str, object], keys: tuple[str, ...]) -> object:
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def _clean_model(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _clean_reasoning_effort(value: object) -> str | None:
    value = _clean_model(value)
    if not value:
        return None
    value = value.lower()
    return value if value in _REASONING_EFFORTS else None


def _clean_service_tier(value: object) -> str | None:
    value = _clean_model(value)
    if not value:
        return None
    value = value.lower().replace("-", "_")
    if value in {"standard", "default", "auto", "normal"}:
        return None
    if value in {"high_speed", "highspeed", "quick"}:
        return "fast"
    return value if value in _SERVICE_TIERS else None
