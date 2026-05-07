import json
import sys
from pathlib import Path


_WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(_WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_ROOT))

from scripts.orchestrator.phase05_candidates import build_poc_candidate_index
from scripts.orchestrator.config import get_phase_chain, get_phase_config


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def test_builds_representative_candidates_from_phase04(tmp_path):
    _write_json(
        tmp_path / "TARGET_INFO.json",
        {
            "local_checkout": "target_workspace/damn-vulnerable-defi",
            "language": "solidity",
        },
    )
    _write_json(
        tmp_path / "03_PARTIAL_W0B0.json",
        {
            "audit_items": [
                {
                    "property_id": "PROP-truster-asm-002",
                    "classification": "vulnerability",
                    "code_path": "contracts/truster/TrusterLenderPool.sol::TrusterLenderPool.flashLoan::L14-32",
                    "summary": "Attacker calls flashLoan with approve data, then transferFrom drains the pool.",
                },
                {
                    "property_id": "PROP-truster-inv-002",
                    "classification": "vulnerability",
                    "code_path": "target_workspace/damn-vulnerable-defi/contracts/truster/TrusterLenderPool.sol::flashLoan::L14-32",
                    "summary": "Attacker calls approve and transferFrom through flashLoan.",
                },
                {
                    "property_id": "PROP-unstoppable-asm-003",
                    "classification": "vulnerability",
                    "code_path": "contracts/unstoppable/UnstoppableLender.sol::flashLoan::L29-44",
                    "summary": "Attacker transfers tokens directly to the pool and breaks the poolBalance assertion.",
                },
            ],
        },
    )
    _write_json(
        tmp_path / "04_PARTIAL_W0B0.json",
        {
            "reviewed_items": [
                {
                    "property_id": "PROP-truster-asm-002",
                    "review_verdict": "CONFIRMED_VULNERABILITY",
                    "adjusted_severity": "Critical",
                    "reviewer_notes": "Critical because the approve plus transferFrom flow drains all pool tokens.",
                },
                {
                    "property_id": "PROP-truster-inv-002",
                    "review_verdict": "CONFIRMED_VULNERABILITY",
                    "adjusted_severity": "High",
                    "reviewer_notes": "Duplicate root cause.",
                },
                {
                    "property_id": "PROP-unstoppable-asm-003",
                    "review_verdict": "CONFIRMED_POTENTIAL",
                    "adjusted_severity": "Medium",
                    "reviewer_notes": "Direct token transfer causes repeatable denial of service.",
                    "spec_reference": "SG-002",
                },
            ],
        },
    )

    index = build_poc_candidate_index(tmp_path)

    assert index["metadata"]["reviewed_candidate_items"] == 3
    assert index["metadata"]["candidate_count"] == 2

    by_family = {candidate["attack_family"]: candidate for candidate in index["candidates"]}
    truster = by_family["unauthorized-token-approval"]
    assert truster["representative_property_id"] == "PROP-truster-asm-002"
    assert truster["covered_property_ids"] == [
        "PROP-truster-asm-002",
        "PROP-truster-inv-002",
    ]
    assert truster["primary_file"] == (
        "target_workspace/damn-vulnerable-defi/contracts/truster/TrusterLenderPool.sol"
    )
    assert truster["recommended_output_path"].endswith(
        "test/speca-poc/truster/poc_unauthorized-token-approval.challenge.js"
    )
    assert truster["run_command"].startswith("npm run compile && npx mocha")

    unstoppable = by_family["direct-token-transfer-dos"]
    assert unstoppable["spec_reference"] == "SG-002"
    assert unstoppable["recommended_type"] == "it"


def test_ignores_non_candidate_phase04_items(tmp_path):
    _write_json(tmp_path / "TARGET_INFO.json", {"local_checkout": "target_workspace/repo"})
    _write_json(
        tmp_path / "03_PARTIAL_W0B0.json",
        {"audit_items": [{"property_id": "P1", "code_path": "contracts/a/A.sol::f::L1-2"}]},
    )
    _write_json(
        tmp_path / "04_PARTIAL_W0B0.json",
        {
            "reviewed_items": [
                {
                    "property_id": "P1",
                    "review_verdict": "PASS_THROUGH",
                    "adjusted_severity": "Informational",
                }
            ]
        },
    )

    index = build_poc_candidate_index(tmp_path)

    assert index["metadata"]["reviewed_candidate_items"] == 0
    assert index["candidates"] == []


def test_phase05_config_is_available():
    config = get_phase_config("05")

    assert config.depends_on == ["04"]
    assert "outputs/04_PARTIAL_*.json" in config.input_patterns
    assert get_phase_chain("05")[-2:] == ["04", "05"]
