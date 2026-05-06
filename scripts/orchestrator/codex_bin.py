"""Resolve the Codex executable used by SPECA runners."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


def resolve_codex_bin() -> str:
    """Return a Codex binary path suitable for long-running child processes.

    On Windows, the npm `codex.cmd` shim launches Node, which then launches the
    native Codex binary. Terminating the shim can leave the native app-server
    process behind, so prefer the package's vendored `codex.exe` when present.
    """
    if sys.platform == "win32":
        cmd = shutil.which("codex.cmd")
        if cmd:
            vendor = (
                Path(cmd).resolve().parent
                / "node_modules"
                / "@openai"
                / "codex"
                / "node_modules"
                / "@openai"
                / "codex-win32-x64"
                / "vendor"
                / "x86_64-pc-windows-msvc"
                / "codex"
                / "codex.exe"
            )
            if vendor.exists():
                return str(vendor)

        exe = shutil.which("codex.exe")
        if exe:
            return exe
        if cmd:
            return cmd

    return shutil.which("codex") or "codex"
