"""Tests for API dispatch behavior of Phase 05."""

from __future__ import annotations

import asyncio
import json

from server.orchestrator_bridge import _run_phase
from server.run_manager import RunManager, RunStatus


def test_api_phase05_dispatch_builds_candidate_index(tmp_path):
    output_dir = tmp_path / "outputs" / "phase05"
    output_dir.mkdir(parents=True)
    (output_dir / "TARGET_INFO.json").write_text(
        json.dumps(
            {
                "target_repo": "example/repo",
                "target_commit": "abc123",
                "local_checkout": "target_workspace/example",
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
