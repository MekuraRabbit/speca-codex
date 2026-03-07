"""Progress event bus for real-time SSE streaming."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EventType(str, Enum):
    PHASE_START = "phase_start"
    ITEMS_LOADED = "items_loaded"
    BATCH_COMPLETE = "batch_complete"
    BATCH_FAILED = "batch_failed"
    COST_UPDATE = "cost_update"
    CIRCUIT_BREAKER = "circuit_breaker"
    PHASE_COMPLETE = "phase_complete"
    PHASE_ERROR = "phase_error"
    LOG = "log"


@dataclass
class ProgressEvent:
    type: EventType
    data: dict[str, Any]
    timestamp: float = field(default_factory=time.time)


class ProgressBus:
    """Per-run event queue. Multiple SSE clients can subscribe."""

    def __init__(self) -> None:
        self._subscribers: list[asyncio.Queue[ProgressEvent | None]] = []

    def subscribe(self) -> asyncio.Queue[ProgressEvent | None]:
        q: asyncio.Queue[ProgressEvent | None] = asyncio.Queue()
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[ProgressEvent | None]) -> None:
        try:
            self._subscribers.remove(q)
        except ValueError:
            pass

    async def publish(self, event: ProgressEvent) -> None:
        for q in self._subscribers:
            await q.put(event)

    async def close(self) -> None:
        for q in self._subscribers:
            await q.put(None)
