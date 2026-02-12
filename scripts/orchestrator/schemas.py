"""
Pydantic Data Models for Security Agent Pipeline

Defines strict schemas for data flowing between phases.
These models serve as the single source of truth for:
  - Input/output validation at phase boundaries
  - Type-safe access in orchestrator code
  - Documentation of the data contract between phases

Each model corresponds to a specific data structure used in the pipeline.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Shared enums
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    """Severity levels used across the pipeline."""
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    INFORMATIONAL = "Informational"


class ReachabilityClassification(str, Enum):
    """Reachability classification for properties and checklist items."""
    EXTERNAL_REACHABLE = "external-reachable"
    INTERNAL_ONLY = "internal-only"
    API_ONLY = "api-only"


class BugBountyScope(str, Enum):
    """Bug bounty scope classification."""
    IN_SCOPE = "in-scope"
    OUT_OF_SCOPE = "out-of-scope"
    CONDITIONAL = "conditional"


class AuditClassification(str, Enum):
    """Final classification from the formal audit."""
    VULNERABLE = "vulnerable"
    SAFE = "safe"
    INCONCLUSIVE = "inconclusive"
    OUT_OF_SCOPE = "out-of-scope"


class ReviewVerdict(str, Enum):
    """Review verdict from Phase 04."""
    CONFIRMED = "Confirmed"
    DISPUTED = "Disputed"
    NEEDS_MORE_INFO = "Needs More Info"


class ChecklistMindset(str, Enum):
    """Mindset used for checklist generation."""
    BOUNDARY_GUARD = "Boundary Guard"
    FORMAL_VERIFICATION_ENGINEER = "Formal Verification Engineer"


# ---------------------------------------------------------------------------
# Phase 01a – Discovery
# ---------------------------------------------------------------------------

class DiscoveredSpec(BaseModel):
    """A single specification URL discovered in Phase 01a."""
    url: str
    title: str = ""
    status: str = "pending"


class Phase01aState(BaseModel):
    """Output of Phase 01a: discovered specification URLs."""
    found_specs: list[DiscoveredSpec] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Phase 01e – Properties
# ---------------------------------------------------------------------------

class PropertyReachability(BaseModel):
    """Reachability information for a property."""
    classification: str = ""
    entry_points: list[str] = Field(default_factory=list)
    attacker_controlled: bool = False
    bug_bounty_scope: str = "conditional"


class PropertyCovers(BaseModel):
    """Coverage information for a property."""
    primary_element: str | None = None
    edges: list[str] = Field(default_factory=list)
    nodes: list[str] = Field(default_factory=list)
    is_boundary_edge: bool = False


class Property(BaseModel):
    """A single formal property from Phase 01e."""
    id: str
    type: str = ""
    assertion: str = ""
    severity: str = ""
    covers: PropertyCovers = Field(default_factory=PropertyCovers)
    reachability: PropertyReachability = Field(default_factory=PropertyReachability)
    exploitability: str = ""


class Phase01ePartial(BaseModel):
    """Output of Phase 01e: properties extracted from trust model."""
    properties: list[Property] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Phase 02 – Checklist
# ---------------------------------------------------------------------------

class ChecklistReachability(BaseModel):
    """Reachability information for a checklist item."""
    classification: str = ""
    entry_points: list[str] = Field(default_factory=list)
    attacker_controlled: bool = False
    bug_bounty_scope: str = "conditional"


class ChecklistItem(BaseModel):
    """A single checklist item from Phase 02."""
    check_id: str
    property_id: str = ""
    title: str = ""
    severity: str = ""
    mindset: str = ""
    is_boundary_check: bool = False
    reachability: ChecklistReachability = Field(default_factory=ChecklistReachability)
    test_procedure: str = ""
    bug_class: str = ""
    risk_category: str = ""
    notes: str = ""
    # Optional fields from graph element
    graph_element_under_test: str | None = None
    code_scope: dict[str, Any] = Field(default_factory=dict)


class Phase02Partial(BaseModel):
    """Output of Phase 02: checklist items."""
    checklist: list[ChecklistItem] = Field(default_factory=list)
    # Alias: some outputs use 'checklist_items' instead of 'checklist'
    checklist_items: list[ChecklistItem] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _merge_checklist_keys(self) -> "Phase02Partial":
        """Merge checklist_items into checklist for consistency."""
        if self.checklist_items and not self.checklist:
            self.checklist = self.checklist_items
        return self


# ---------------------------------------------------------------------------
# Phase 03 – Audit Map
# ---------------------------------------------------------------------------

class Phase1AbstractInterpretation(BaseModel):
    """Phase 1 audit trail: abstract interpretation results."""
    summary: str = ""
    state_anomalies_found: list[Any] = Field(default_factory=list)


class Phase2SymbolicExecution(BaseModel):
    """Phase 2 audit trail: symbolic execution results."""
    summary: str = ""
    counterexample_found: bool = False
    counterexample: Any = None


class Phase2_5ReachabilityAnalysis(BaseModel):
    """Phase 2.5 audit trail: reachability analysis results."""
    summary: str = ""
    entry_points: list[str] = Field(default_factory=list)
    data_flow_path: str = ""
    validation_layers: list[str] = Field(default_factory=list)
    attacker_controlled: bool = False
    classification: str = "unreachable"
    notes: str = ""


class Phase3InvariantProving(BaseModel):
    """Phase 3 audit trail: invariant proving results."""
    summary: str = ""
    proof_successful: bool = False
    guard_identified: Any = None


class Phase3_5ScopeFiltering(BaseModel):
    """Phase 3.5 audit trail: scope filtering results."""
    bug_bounty_eligible: bool = False
    reason: str = ""
    recommendation: str = ""
    notes: str = ""


class AuditTrail(BaseModel):
    """Complete audit trail from the three-phase formal audit."""
    phase1_abstract_interpretation: Phase1AbstractInterpretation = Field(
        default_factory=Phase1AbstractInterpretation
    )
    phase2_symbolic_execution: Phase2SymbolicExecution = Field(
        default_factory=Phase2SymbolicExecution
    )
    phase2_5_reachability_analysis: Phase2_5ReachabilityAnalysis = Field(
        default_factory=Phase2_5ReachabilityAnalysis
    )
    phase3_invariant_proving: Phase3InvariantProving = Field(
        default_factory=Phase3InvariantProving
    )
    phase3_5_scope_filtering: Phase3_5ScopeFiltering = Field(
        default_factory=Phase3_5ScopeFiltering
    )


class AuditMapItem(BaseModel):
    """A single audit result from Phase 03."""
    check_id: str
    property_id: str | None = None
    code_scope: dict[str, Any] = Field(default_factory=dict)
    final_classification: str = ""
    bug_bounty_eligible: bool = False
    summary: str = ""
    audit_trail: AuditTrail = Field(default_factory=AuditTrail)


class Phase03Partial(BaseModel):
    """Output of Phase 03: audit map items."""
    audit_items: list[AuditMapItem] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Phase 04 – Audit Review
# ---------------------------------------------------------------------------

class OriginalFinding(BaseModel):
    """Summary of the original finding from Phase 03."""
    final_classification: str = ""
    summary: str = ""


class ReviewedItem(BaseModel):
    """A single reviewed item from Phase 04."""
    check_id: str
    original_finding: OriginalFinding = Field(default_factory=OriginalFinding)
    review_verdict: str = ""
    adjusted_severity: str = ""
    reviewer_notes: str = ""
    final_recommendation: str = ""


class Phase04Partial(BaseModel):
    """Output of Phase 04: reviewed audit items."""
    reviewed_items: list[ReviewedItem] = Field(default_factory=list)
    source_files: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Queue payload (shared across all phases)
# ---------------------------------------------------------------------------

class QueuePayload(BaseModel):
    """Standard queue payload sent to Claude workers."""
    worker_id: int
    phase: str
    items: list[dict[str, Any]]
    total_items: int


# ---------------------------------------------------------------------------
# Partial output metadata (shared across all phases)
# ---------------------------------------------------------------------------

class PartialMetadata(BaseModel):
    """Metadata attached to every PARTIAL output file."""
    phase: str
    worker_id: int
    batch_index: int
    item_count: int
    timestamp: int
    processed_ids: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Target info (Phase 03 → Phase 04 handoff)
# ---------------------------------------------------------------------------

class TargetInfo(BaseModel):
    """Target repository information saved by Phase 03 for Phase 04."""
    target_repo: str
    target_ref_type: str = ""
    target_ref_label: str = ""
    target_commit: str = ""
    target_commit_short: str = ""


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def validate_checklist_item(data: dict[str, Any]) -> tuple[ChecklistItem | None, list[str]]:
    """
    Validate a raw dict as a ChecklistItem.

    Returns:
        (parsed_item, errors) – parsed_item is None when validation fails.
    """
    errors: list[str] = []
    try:
        item = ChecklistItem.model_validate(data)
        # Additional business-rule checks
        if not item.check_id:
            errors.append("check_id is empty")
        if not item.property_id:
            errors.append("property_id is empty")
        if not item.test_procedure:
            errors.append("test_procedure is empty")
        return item, errors
    except Exception as exc:
        return None, [str(exc)]


def validate_audit_map_item(data: dict[str, Any]) -> tuple[AuditMapItem | None, list[str]]:
    """
    Validate a raw dict as an AuditMapItem.

    Returns:
        (parsed_item, errors) – parsed_item is None when validation fails.
    """
    errors: list[str] = []
    try:
        item = AuditMapItem.model_validate(data)
        if not item.check_id:
            errors.append("check_id is empty")
        if not item.final_classification:
            errors.append("final_classification is empty")
        return item, errors
    except Exception as exc:
        return None, [str(exc)]
