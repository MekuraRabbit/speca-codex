"""Tests for the NDJSON event emitter used by ``run_phase.py --json``."""

from __future__ import annotations

import io
import json
import re
import subprocess
import sys
from pathlib import Path

from scripts.orchestrator.json_events import JsonEventEmitter


ISO_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}\+00:00$")


def test_disabled_emitter_writes_nothing():
    buf = io.StringIO()
    emitter = JsonEventEmitter(enabled=False, stream=buf)
    emitter.emit("phase-started", phase="01a")
    assert buf.getvalue() == ""


def test_enabled_emitter_writes_one_ndjson_line_per_event():
    buf = io.StringIO()
    emitter = JsonEventEmitter(enabled=True, stream=buf)
    emitter.emit("phase-started", phase="01a", workers=4)
    emitter.emit("phase-completed", phase="01a", duration_s=1.23, total_results=7)

    lines = buf.getvalue().splitlines()
    assert len(lines) == 2

    started = json.loads(lines[0])
    assert started["type"] == "phase-started"
    assert started["phase"] == "01a"
    assert started["workers"] == 4
    assert ISO_UTC_RE.match(started["ts"])

    completed = json.loads(lines[1])
    assert completed["type"] == "phase-completed"
    assert completed["duration_s"] == 1.23
    assert completed["total_results"] == 7


def test_emitter_serialises_non_json_payloads_via_default_str():
    """Non-JSON-serialisable values (e.g. Path) must not crash the emitter."""
    buf = io.StringIO()
    emitter = JsonEventEmitter(enabled=True, stream=buf)
    emitter.emit("phase-failed", phase="03", reason="boom", path=Path("/tmp/x"))

    record = json.loads(buf.getvalue())
    assert record["path"] == str(Path("/tmp/x"))


def test_emitter_disables_itself_on_broken_pipe():
    class BrokenStream:
        def write(self, _: str) -> int:
            raise BrokenPipeError("consumer hung up")

        def flush(self) -> None:  # pragma: no cover - never reached
            pass

    emitter = JsonEventEmitter(enabled=True, stream=BrokenStream())
    emitter.emit("phase-started", phase="01a")
    # Subsequent emits must be no-ops (no exception).
    emitter.emit("phase-completed", phase="01a")
    assert emitter.enabled is False


def test_run_phase_json_flag_emits_pipeline_started_on_stdout(tmp_path: Path):
    """End-to-end: a dependency-failing run still emits NDJSON on stdout.

    Run from a clean tmp cwd so Phase 01b's dependency check (looking for
    01a output under ./outputs/) fails immediately. The pipeline-started
    + phase-started + phase-failed + pipeline-completed events must all
    land on stdout (decorative output goes to stderr).
    """
    repo_root = Path(__file__).resolve().parents[1]

    proc = subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "run_phase.py"), "--phase", "01b", "--json"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )

    # Decorative output went to stderr; stdout is pure NDJSON.
    stdout_lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    assert stdout_lines, f"no NDJSON on stdout. stderr was:\n{proc.stderr}"

    events = [json.loads(ln) for ln in stdout_lines]
    types = [e["type"] for e in events]

    assert "pipeline-started" in types
    assert "phase-started" in types
    # Dependency check fails for 01b in an empty workspace -> phase-failed.
    assert "phase-failed" in types
    assert "pipeline-completed" in types

    # Every event has an ISO-UTC timestamp.
    for ev in events:
        assert "ts" in ev and ISO_UTC_RE.match(ev["ts"])
