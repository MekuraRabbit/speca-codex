"""Tests for API dispatch behavior of Phase 05."""

from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path

from server.orchestrator_bridge import _run_phase
from server.run_manager import RunManager, RunStatus


def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def _make_target_checkout(path: Path) -> str:
    path.mkdir(parents=True)
    _git(path, "init")
    _git(path, "config", "user.email", "speca@example.invalid")
    _git(path, "config", "user.name", "SPECA Test")
    (path / "README.md").write_text("target\n", encoding="utf-8")
    _git(path, "add", "README.md")
    _git(path, "commit", "-m", "initial")
    _git(path, "remote", "add", "origin", "https://github.com/example/repo.git")
    return _git(path, "rev-parse", "HEAD")


def test_api_phase05_dispatch_builds_candidate_index(tmp_path):
    output_dir = tmp_path / "outputs" / "phase05"
    output_dir.mkdir(parents=True)
    checkout = tmp_path / "target_workspace" / "example"
    head = _make_target_checkout(checkout)
    (output_dir / "TARGET_INFO.json").write_text(
        json.dumps(
            {
                "target_repo": "example/repo",
                "target_commit": head,
                "local_checkout": str(checkout),
                "language": "solidity",
            }
        ),
        encoding="utf-8",
    )
    (output_dir / "03_PARTIAL_W0B0_1.json").write_text(
        json.dumps(
            {
                "audit_items": [
                    {
                        "property_id": "PROP-001",
                        "classification": "vulnerability",
                        "code_path": "contracts/Challenge.sol::withdraw::L10-20",
                        "proof_trace": "withdraw updates state after transfer",
                        "attack_scenario": "reentrant withdraw drains funds",
                        "checklist_id": "PROP-001",
                    }
                ],
                "metadata": {"processed_ids": ["PROP-001"]},
            }
        ),
        encoding="utf-8",
    )
    (output_dir / "04_PARTIAL_W0B0_1.json").write_text(
        json.dumps(
            {
                "reviewed_items": [
                    {
                        "property_id": "PROP-001",
                        "review_verdict": "CONFIRMED_VULNERABILITY",
                        "original_classification": "vulnerability",
                        "adjusted_severity": "High",
                        "reviewer_notes": "An attacker can trigger this via withdraw.",
                        "spec_reference": "",
                    }
                ],
                "metadata": {"processed_ids": ["PROP-001"]},
            }
        ),
        encoding="utf-8",
    )

    manager = RunManager()
    run = manager.create_run(
        "05",
        {
            "phase_id": "05",
            "output_dir": str(output_dir),
            "force": False,
        },
    )

    asyncio.run(_run_phase(run, manager))

    candidate_path = output_dir / "05_POC_CANDIDATES.json"
    data = json.loads(candidate_path.read_text(encoding="utf-8"))
    assert run.status == RunStatus.COMPLETED
    assert run.result["total_results"] == 1
    assert data["metadata"]["candidate_count"] == 1
    assert data["metadata"]["output_dir"] == "phase05"
