"""Codex App GUI model discovery."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.orchestrator.codex_gui_model import (
    resolve_codex_gui_model,
    resolve_codex_gui_settings,
)


def test_resolve_codex_gui_model_from_thread_session(tmp_path: Path):
    sessions = tmp_path / "sessions" / "2026" / "05" / "06"
    sessions.mkdir(parents=True)
    thread_id = "thread-123"
    session = sessions / f"rollout-2026-05-06T00-00-00-{thread_id}.jsonl"
    session.write_text(
        "\n".join([
            json.dumps({
                "type": "turn_context",
                "payload": {"turn_id": "old", "model": "gpt-5.2", "effort": "high"},
            }),
            json.dumps({
                "type": "turn_context",
                "payload": {
                    "turn_id": "new",
                    "model": "gpt-5.5",
                    "effort": "xhigh",
                    "serviceTier": "fast",
                },
            }),
        ]),
        encoding="utf-8",
    )

    model = resolve_codex_gui_model(
        {"CODEX_THREAD_ID": thread_id},
        sessions_root=tmp_path / "sessions",
    )

    assert model == "gpt-5.5"


def test_resolve_codex_gui_settings_from_thread_session(tmp_path: Path):
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    thread_id = "thread-123"
    session = sessions / f"rollout-{thread_id}.jsonl"
    session.write_text(
        json.dumps({
            "type": "turn_context",
            "payload": {
                "turn_id": "new",
                "model": "gpt-5.5",
                "collaboration_mode": {
                    "settings": {
                        "model": "gpt-5.5",
                        "reasoning_effort": "xhigh",
                    },
                },
                "serviceTier": "fast",
            },
        }),
        encoding="utf-8",
    )

    settings = resolve_codex_gui_settings(
        {"CODEX_THREAD_ID": thread_id},
        sessions_root=sessions,
    )

    assert settings.model == "gpt-5.5"
    assert settings.reasoning_effort == "xhigh"
    assert settings.service_tier == "fast"


def test_resolve_codex_gui_model_prefers_explicit_env_override(tmp_path: Path):
    model = resolve_codex_gui_model(
        {"SPECA_CODEX_GUI_MODEL": "gpt-5.5"},
        sessions_root=tmp_path / "missing",
    )

    assert model == "gpt-5.5"


def test_resolve_codex_gui_model_returns_none_when_unavailable(tmp_path: Path):
    model = resolve_codex_gui_model(
        {"CODEX_THREAD_ID": "missing"},
        sessions_root=tmp_path,
    )

    assert model is None


def test_resolve_codex_gui_model_honors_empty_env(tmp_path: Path):
    model = resolve_codex_gui_model({}, sessions_root=tmp_path)

    assert model is None


def test_resolve_codex_gui_settings_prefers_env_over_session(tmp_path: Path):
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    thread_id = "thread-123"
    session = sessions / f"rollout-{thread_id}.jsonl"
    session.write_text(
        json.dumps({
            "type": "turn_context",
            "payload": {
                "model": "gpt-5.2",
                "effort": "medium",
                "serviceTier": "fast",
            },
        }),
        encoding="utf-8",
    )

    settings = resolve_codex_gui_settings(
        {
            "CODEX_THREAD_ID": thread_id,
            "SPECA_CODEX_GUI_MODEL": "gpt-5.5",
            "SPECA_CODEX_GUI_REASONING_EFFORT": "xhigh",
            "SPECA_CODEX_GUI_SERVICE_TIER": "flex",
        },
        sessions_root=sessions,
    )

    assert settings.model == "gpt-5.5"
    assert settings.reasoning_effort == "xhigh"
    assert settings.service_tier == "flex"
