"""Codex worker sandbox selection helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterable


SANDBOX_ENV = "SPECA_CODEX_SANDBOX"
SANDBOX_NETWORK_ENV = "SPECA_CODEX_SANDBOX_NETWORK"

_TRUTHY = {"1", "true", "yes", "on"}
_FALSY = {"0", "false", "no", "off"}
_VALID_SANDBOX_MODES = {"read-only", "workspace-write", "danger-full-access"}
_NETWORK_PHASES = {"01a", "01b"}


def codex_sandbox_mode(config: Any) -> str:
    """Return the Codex sandbox mode for a SPECA worker run."""
    value = _config_env(config, SANDBOX_ENV)
    if not value:
        return "workspace-write"

    normalized = value.strip().lower()
    aliases = {
        "readonly": "read-only",
        "read_only": "read-only",
        "workspace_write": "workspace-write",
        "workspacewrite": "workspace-write",
        "dangerfullaccess": "danger-full-access",
        "danger_full_access": "danger-full-access",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in _VALID_SANDBOX_MODES:
        valid = ", ".join(sorted(_VALID_SANDBOX_MODES))
        raise ValueError(f"{SANDBOX_ENV} must be one of: {valid}")
    return normalized


def codex_sandbox_network_enabled(config: Any) -> bool:
    """Return whether Codex sandboxed worker commands may use the network."""
    override = _config_env(config, SANDBOX_NETWORK_ENV)
    if override:
        value = override.strip().lower()
        if value in _TRUTHY:
            return True
        if value in _FALSY:
            return False
        raise ValueError(f"{SANDBOX_NETWORK_ENV} must be true or false")
    return getattr(config, "phase_id", "") in _NETWORK_PHASES


def codex_app_sandbox_policy(
    config: Any,
    *,
    writable_roots: Iterable[Path],
) -> dict[str, Any]:
    """Build the app-server ``sandboxPolicy`` payload for a worker turn."""
    mode = codex_sandbox_mode(config)
    if mode == "danger-full-access":
        return {"type": "dangerFullAccess"}
    if mode == "read-only":
        return {
            "type": "readOnly",
            "networkAccess": codex_sandbox_network_enabled(config),
        }
    return {
        "type": "workspaceWrite",
        "networkAccess": codex_sandbox_network_enabled(config),
        "writableRoots": [str(path.resolve()) for path in writable_roots],
    }


def codex_exec_sandbox_args(
    config: Any,
    *,
    writable_roots: Iterable[Path],
) -> list[str]:
    """Build Codex CLI sandbox arguments for non-interactive worker runs."""
    mode = codex_sandbox_mode(config)
    if mode == "danger-full-access":
        return ["--dangerously-bypass-approvals-and-sandbox"]

    args = [
        "--sandbox",
        mode,
        "-c",
        'approval_policy="never"',
    ]
    if mode == "workspace-write":
        args.extend([
            "-c",
            f"sandbox_workspace_write.network_access={str(codex_sandbox_network_enabled(config)).lower()}",
        ])
        for path in writable_roots:
            args.extend(["--add-dir", str(path.resolve())])
    return args


def _config_env(config: Any, name: str) -> str:
    runtime_env = getattr(config, "runtime_env", {}) or {}
    value = runtime_env.get(name)
    if value is None:
        value = os.environ.get(name, "")
    return str(value).strip()
