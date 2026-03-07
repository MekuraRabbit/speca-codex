"""FastAPI application for SPECA Pipeline local execution."""

from __future__ import annotations

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


def main() -> None:
    import uvicorn
    uvicorn.run("server.app:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
