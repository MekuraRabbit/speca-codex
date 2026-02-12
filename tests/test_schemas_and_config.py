"""
Tests for Pydantic schemas and PhaseConfig migration.

Validates:
  - PhaseConfig construction and computed fields
  - Data model validation (ChecklistItem, AuditMapItem, etc.)
  - Phase02Partial / Phase03Partial parsing
  - Validation helpers (validate_checklist_item, validate_audit_map_item)
  - Edge cases and error handling
"""

import sys
import os
import json
import unittest

# Ensure scripts/ is on the path so `orchestrator` is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from orchestrator.config import PhaseConfig, PHASE_CONFIGS, get_phase_config, get_phase_chain
from orchestrator.schemas import (
    ChecklistItem,
    AuditMapItem,
    Phase02Partial,
    Phase03Partial,
    Phase04Partial,
    AuditTrail,
    ReviewedItem,
    QueuePayload,
    validate_checklist_item,
    validate_audit_map_item,
    Severity,
    AuditClassification,
    ReviewVerdict,
)
from pathlib import Path
from pydantic import ValidationError


# -----------------------------------------------------------------------
# PhaseConfig tests
# -----------------------------------------------------------------------

class TestPhaseConfig(unittest.TestCase):
    """Tests for the Pydantic-based PhaseConfig."""

    def test_all_phase_configs_are_valid(self):
        """Every entry in PHASE_CONFIGS must be a valid PhaseConfig."""
        for phase_id, cfg in PHASE_CONFIGS.items():
            self.assertIsInstance(cfg, PhaseConfig)
            self.assertEqual(cfg.phase_id, phase_id)
            self.assertIsInstance(cfg.skill_path, Path)
            self.assertIsInstance(cfg.prompt_path, Path)

    def test_effective_result_id_field_fallback(self):
        """effective_result_id_field should fall back to item_id_field."""
        cfg = PhaseConfig(
            phase_id="test",
            name="Test",
            description="test",
            skill_path=Path("test"),
            prompt_path=Path("test"),
            queue_pattern="",
            output_pattern="",
            item_id_field="check_id",
            result_id_field="",
        )
        self.assertEqual(cfg.effective_result_id_field, "check_id")

    def test_effective_result_id_field_explicit(self):
        """effective_result_id_field should use result_id_field when set."""
        cfg = PhaseConfig(
            phase_id="test",
            name="Test",
            description="test",
            skill_path=Path("test"),
            prompt_path=Path("test"),
            queue_pattern="",
            output_pattern="",
            item_id_field="check_id",
            result_id_field="source_url",
        )
        self.assertEqual(cfg.effective_result_id_field, "source_url")

    def test_get_phase_config_known(self):
        """get_phase_config should return config for known phases."""
        for pid in ("01a", "01b", "02", "03", "04"):
            cfg = get_phase_config(pid)
            self.assertEqual(cfg.phase_id, pid)

    def test_get_phase_config_unknown(self):
        """get_phase_config should raise for unknown phases."""
        with self.assertRaises(ValueError):
            get_phase_config("99")

    def test_get_phase_chain(self):
        """get_phase_chain should return correct dependency order."""
        chain = get_phase_chain("03")
        # 03 depends on 02, which depends on 01e, etc.
        self.assertIn("03", chain)
        self.assertEqual(chain[-1], "03")

    def test_phase03_config_values(self):
        """Phase 03 config should have expected values."""
        cfg = get_phase_config("03")
        self.assertEqual(cfg.batch_strategy, "count")
        self.assertEqual(cfg.max_batch_size, 25)
        self.assertEqual(cfg.item_id_field, "check_id")
        self.assertEqual(cfg.result_key, "audit_items")
        self.assertEqual(cfg.output_prefix, "AUDITMAP")


# -----------------------------------------------------------------------
# Schema tests – ChecklistItem
# -----------------------------------------------------------------------

class TestChecklistItem(unittest.TestCase):
    """Tests for ChecklistItem schema."""

    def test_valid_item(self):
        item = ChecklistItem(
            check_id="CHK-0001",
            property_id="PROP-001",
            title="Test check",
            severity="High",
            test_procedure="Run the test",
        )
        self.assertEqual(item.check_id, "CHK-0001")
        self.assertEqual(item.property_id, "PROP-001")

    def test_minimal_item(self):
        """Only check_id is required."""
        item = ChecklistItem(check_id="CHK-0002")
        self.assertEqual(item.check_id, "CHK-0002")
        self.assertEqual(item.property_id, "")

    def test_extra_fields_ignored(self):
        """Extra fields in raw data should not cause errors (model_validate)."""
        data = {
            "check_id": "CHK-0003",
            "property_id": "PROP-003",
            "unknown_field": "should be ignored",
        }
        item = ChecklistItem.model_validate(data)
        self.assertEqual(item.check_id, "CHK-0003")


# -----------------------------------------------------------------------
# Schema tests – AuditMapItem
# -----------------------------------------------------------------------

class TestAuditMapItem(unittest.TestCase):
    """Tests for AuditMapItem schema."""

    def test_valid_audit_item(self):
        item = AuditMapItem(
            check_id="CHK-0001",
            property_id="PROP-001",
            final_classification="vulnerable",
            bug_bounty_eligible=True,
            summary="Found vulnerability",
        )
        self.assertEqual(item.check_id, "CHK-0001")
        self.assertTrue(item.bug_bounty_eligible)

    def test_audit_trail_defaults(self):
        """AuditTrail should have sensible defaults."""
        item = AuditMapItem(check_id="CHK-0001")
        trail = item.audit_trail
        self.assertFalse(trail.phase2_symbolic_execution.counterexample_found)
        self.assertFalse(trail.phase3_invariant_proving.proof_successful)

    def test_full_audit_trail(self):
        """Full audit trail should parse correctly."""
        data = {
            "check_id": "CHK-0001",
            "final_classification": "vulnerable",
            "audit_trail": {
                "phase1_abstract_interpretation": {
                    "summary": "Anomaly found",
                    "state_anomalies_found": ["overflow"],
                },
                "phase2_symbolic_execution": {
                    "summary": "Counterexample exists",
                    "counterexample_found": True,
                    "counterexample": {"input": "0xff"},
                },
                "phase2_5_reachability_analysis": {
                    "summary": "Reachable via external call",
                    "classification": "external-reachable",
                    "attacker_controlled": True,
                },
                "phase3_invariant_proving": {
                    "summary": "Proof failed",
                    "proof_successful": False,
                },
                "phase3_5_scope_filtering": {
                    "bug_bounty_eligible": True,
                    "reason": "In scope",
                },
            },
        }
        item = AuditMapItem.model_validate(data)
        self.assertTrue(item.audit_trail.phase2_symbolic_execution.counterexample_found)
        self.assertTrue(item.audit_trail.phase2_5_reachability_analysis.attacker_controlled)


# -----------------------------------------------------------------------
# Schema tests – Phase02Partial
# -----------------------------------------------------------------------

class TestPhase02Partial(unittest.TestCase):
    """Tests for Phase02Partial schema."""

    def test_checklist_key(self):
        data = {
            "checklist": [
                {"check_id": "CHK-0001", "property_id": "PROP-001"},
            ]
        }
        partial = Phase02Partial.model_validate(data)
        self.assertEqual(len(partial.checklist), 1)

    def test_checklist_items_key_merged(self):
        """checklist_items should be merged into checklist."""
        data = {
            "checklist_items": [
                {"check_id": "CHK-0001", "property_id": "PROP-001"},
                {"check_id": "CHK-0002", "property_id": "PROP-002"},
            ]
        }
        partial = Phase02Partial.model_validate(data)
        self.assertEqual(len(partial.checklist), 2)

    def test_empty_partial(self):
        partial = Phase02Partial.model_validate({})
        self.assertEqual(len(partial.checklist), 0)


# -----------------------------------------------------------------------
# Schema tests – Phase03Partial
# -----------------------------------------------------------------------

class TestPhase03Partial(unittest.TestCase):
    """Tests for Phase03Partial schema."""

    def test_valid_partial(self):
        data = {
            "audit_items": [
                {
                    "check_id": "CHK-0001",
                    "final_classification": "safe",
                    "summary": "No issues found",
                },
            ]
        }
        partial = Phase03Partial.model_validate(data)
        self.assertEqual(len(partial.audit_items), 1)
        self.assertEqual(partial.audit_items[0].final_classification, "safe")


# -----------------------------------------------------------------------
# Schema tests – Phase04Partial
# -----------------------------------------------------------------------

class TestPhase04Partial(unittest.TestCase):
    """Tests for Phase04Partial schema."""

    def test_valid_review(self):
        data = {
            "reviewed_items": [
                {
                    "check_id": "CHK-0001",
                    "review_verdict": "Confirmed",
                    "adjusted_severity": "High",
                    "reviewer_notes": "Valid finding",
                },
            ],
            "source_files": ["outputs/03_AUDITMAP_PARTIAL_W0_B0.json"],
        }
        partial = Phase04Partial.model_validate(data)
        self.assertEqual(len(partial.reviewed_items), 1)
        self.assertEqual(partial.reviewed_items[0].review_verdict, "Confirmed")


# -----------------------------------------------------------------------
# Validation helpers
# -----------------------------------------------------------------------

class TestValidationHelpers(unittest.TestCase):
    """Tests for validate_checklist_item and validate_audit_map_item."""

    def test_validate_checklist_item_valid(self):
        data = {
            "check_id": "CHK-0001",
            "property_id": "PROP-001",
            "test_procedure": "Run test",
        }
        item, errors = validate_checklist_item(data)
        self.assertIsNotNone(item)
        self.assertEqual(len(errors), 0)

    def test_validate_checklist_item_missing_fields(self):
        """Missing property_id and test_procedure should produce warnings."""
        data = {"check_id": "CHK-0001"}
        item, errors = validate_checklist_item(data)
        self.assertIsNotNone(item)
        self.assertIn("property_id is empty", errors)
        self.assertIn("test_procedure is empty", errors)

    def test_validate_checklist_item_empty_check_id(self):
        data = {"check_id": "", "property_id": "PROP-001"}
        item, errors = validate_checklist_item(data)
        self.assertIn("check_id is empty", errors)

    def test_validate_audit_map_item_valid(self):
        data = {
            "check_id": "CHK-0001",
            "final_classification": "vulnerable",
        }
        item, errors = validate_audit_map_item(data)
        self.assertIsNotNone(item)
        self.assertEqual(len(errors), 0)

    def test_validate_audit_map_item_missing_classification(self):
        data = {"check_id": "CHK-0001"}
        item, errors = validate_audit_map_item(data)
        self.assertIsNotNone(item)
        self.assertIn("final_classification is empty", errors)


# -----------------------------------------------------------------------
# Enum tests
# -----------------------------------------------------------------------

class TestEnums(unittest.TestCase):
    """Tests for enum definitions."""

    def test_severity_values(self):
        self.assertEqual(Severity.CRITICAL.value, "Critical")
        self.assertEqual(Severity.HIGH.value, "High")

    def test_audit_classification_values(self):
        self.assertEqual(AuditClassification.VULNERABLE.value, "vulnerable")
        self.assertEqual(AuditClassification.SAFE.value, "safe")

    def test_review_verdict_values(self):
        self.assertEqual(ReviewVerdict.CONFIRMED.value, "Confirmed")
        self.assertEqual(ReviewVerdict.DISPUTED.value, "Disputed")


# -----------------------------------------------------------------------
# QueuePayload tests
# -----------------------------------------------------------------------

class TestQueuePayload(unittest.TestCase):
    """Tests for QueuePayload schema."""

    def test_valid_payload(self):
        payload = QueuePayload(
            worker_id=0,
            phase="03",
            items=[{"check_id": "CHK-0001"}],
            total_items=1,
        )
        self.assertEqual(payload.worker_id, 0)
        self.assertEqual(len(payload.items), 1)


if __name__ == "__main__":
    unittest.main()
