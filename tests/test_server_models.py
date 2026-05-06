"""Tests for API request models."""

import pytest
from pydantic import ValidationError

from server.models import PhaseDispatchRequest


@pytest.mark.parametrize(
    "url",
    [
        "ws://127.0.0.1:8001",
        "ws://localhost:8001",
        "ws://[::1]:8001",
        "wss://localhost:8001",
    ],
)
def test_phase_dispatch_accepts_loopback_app_server_urls(url: str):
    request = PhaseDispatchRequest(phase_id="03", app_server_url=url)

    assert request.app_server_url == url


def test_phase_dispatch_enables_codex_gui_model_by_default():
    request = PhaseDispatchRequest(phase_id="03")

    assert request.use_codex_gui_model is True
    assert request.use_codex_gui_reasoning_effort is True
    assert request.use_codex_gui_service_tier is True


def test_phase_dispatch_accepts_codex_thread_id():
    request = PhaseDispatchRequest(phase_id="03", codex_thread_id="thread-123")

    assert request.codex_thread_id == "thread-123"


def test_phase_dispatch_accepts_codex_effort_and_service_tier():
    request = PhaseDispatchRequest(
        phase_id="03",
        reasoning_effort="xhigh",
        service_tier="fast",
    )

    assert request.reasoning_effort == "xhigh"
    assert request.service_tier == "fast"


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8001",
        "ws://example.com:8001",
        "ws://192.168.1.10:8001",
    ],
)
def test_phase_dispatch_rejects_non_loopback_app_server_urls(url: str):
    with pytest.raises(ValidationError):
        PhaseDispatchRequest(phase_id="03", app_server_url=url)
