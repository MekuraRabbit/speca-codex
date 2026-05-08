"""Tests for server run routes that expose local run artifacts."""

from __future__ import annotations

import asyncio
import json

from server.routes import runs as run_routes
from server.run_manager import RunManager


def test_get_run_diffs_reads_diff_inside_metadata_dir(tmp_path):
    manager = RunManager()
    output_dir = tmp_path / "outputs" / "run"
    run = manager.create_run("03", {"output_dir": str(output_dir)})
    meta_dir = output_dir / "codex_app_threads"
    meta_dir.mkdir(parents=True)
    diff_path = meta_dir / "03_W0B0.diff"
    diff_path.write_text("diff --git a/file b/file\n", encoding="utf-8")
    (meta_dir / "03_W0B0.json").write_text(
        json.dumps({"run_id": run.run_id, "diff_file": str(diff_path)}),
        encoding="utf-8",
    )

    previous = run_routes.run_manager
    run_routes.run_manager = manager
    try:
        result = asyncio.run(run_routes.get_run_diffs(run.run_id, include_content=True))
    finally:
        run_routes.run_manager = previous

    assert result[0]["diff"] == "diff --git a/file b/file\n"


def test_get_run_diffs_refuses_diff_file_outside_metadata_dir(tmp_path):
    manager = RunManager()
    output_dir = tmp_path / "outputs" / "run"
    run = manager.create_run("03", {"output_dir": str(output_dir)})
    meta_dir = output_dir / "codex_app_threads"
    meta_dir.mkdir(parents=True)
    secret_path = tmp_path / "secret.txt"
    secret_path.write_text("secret", encoding="utf-8")
    (meta_dir / "03_W0B0.json").write_text(
        json.dumps({"run_id": run.run_id, "diff_file": str(secret_path)}),
        encoding="utf-8",
    )

    previous = run_routes.run_manager
    run_routes.run_manager = manager
    try:
        result = asyncio.run(run_routes.get_run_diffs(run.run_id, include_content=True))
    finally:
        run_routes.run_manager = previous

    assert result[0]["diff"] == ""
