"""
Centralized output directory resolution.

All orchestrator modules import get_output_root() from here. The value is
resolved at call time from, in order:

1. A task-local override used by the app server.
2. The SPECA_OUTPUT_DIR environment variable.
3. The historical "outputs" default.

The environment variable keeps existing CLI/CI flows working. The task-local
override lets the FastAPI app server run multiple SPECA instances concurrently
inside one Python process without racing on process-wide environment state.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from contextvars import ContextVar, Token
from pathlib import Path
from typing import Iterator


_output_root_var: ContextVar[str | None] = ContextVar(
    "speca_output_root",
    default=None,
)


def get_output_root() -> Path:
    """Return the effective output root directory."""
    override = _output_root_var.get()
    if override:
        return Path(override)
    return Path(os.environ.get("SPECA_OUTPUT_DIR", "outputs"))


def set_output_root(path: str | Path | None) -> Token[str | None]:
    """Set a task-local output root and return the reset token."""
    value = str(path) if path else None
    return _output_root_var.set(value)


def reset_output_root(token: Token[str | None]) -> None:
    """Reset a task-local output root set by set_output_root()."""
    _output_root_var.reset(token)


@contextmanager
def output_root_context(path: str | Path | None) -> Iterator[None]:
    """Temporarily set the output root for the current async task context."""
    token = set_output_root(path)
    try:
        yield
    finally:
        reset_output_root(token)
