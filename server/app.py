"""FastAPI application for SPECA Pipeline local execution."""

from __future__ import annotations

import ipaddress
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .run_manager import RunManager
from .routes import phases, runs

# Ensure scripts/ is importable
_scripts_dir = str(Path(__file__).resolve().parent.parent / "scripts")
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)


@asynccontextmanager
async def lifespan(app: FastAPI):
    manager = RunManager()
    phases.run_manager = manager
    runs.run_manager = manager
    yield


app = FastAPI(title="SPECA Pipeline API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(phases.router)
app.include_router(runs.router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def _env_flag_enabled(value: str | None) -> bool:
    return (value or "").lower() in {"1", "true", "yes", "on"}


def _is_loopback_host(host: str) -> bool:
    normalized = host.strip().lower()
    if normalized in {"localhost"}:
        return True
    if normalized.startswith("[") and normalized.endswith("]"):
        normalized = normalized[1:-1]
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def resolve_api_bind_host(host: str, *, remote_enabled: bool = False) -> str:
    if _is_loopback_host(host) or remote_enabled:
        return host
    raise RuntimeError(
        "Refusing to bind SPECA API to a non-loopback host without "
        "SPECA_ENABLE_REMOTE_API=1. The API is unauthenticated and can launch "
        "local agent runs."
    )


def main() -> None:
    import os
    import uvicorn

    host = resolve_api_bind_host(
        os.environ.get("SPECA_API_HOST", "127.0.0.1"),
        remote_enabled=_env_flag_enabled(os.environ.get("SPECA_ENABLE_REMOTE_API")),
    )
    port = int(os.environ.get("SPECA_API_PORT", "8000"))
    reload = os.environ.get("SPECA_API_RELOAD", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    uvicorn.run("server.app:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    main()
