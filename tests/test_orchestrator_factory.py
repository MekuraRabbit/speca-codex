import pytest

from scripts.orchestrator.base import (
    BaseOrchestrator,
    Phase01Orchestrator,
    Phase02cOrchestrator,
    Phase03Orchestrator,
    Phase04Orchestrator,
)
from scripts.orchestrator.factory import create_orchestrator


@pytest.mark.parametrize(
    ("phase_id", "expected_type"),
    [
        ("01a", Phase01Orchestrator),
        ("02c", Phase02cOrchestrator),
        ("03", Phase03Orchestrator),
        ("04", Phase04Orchestrator),
        ("05", BaseOrchestrator),
    ],
)
def test_create_orchestrator_selects_phase_specific_classes(phase_id, expected_type):
    orchestrator = create_orchestrator(phase_id, num_workers=2, max_concurrent=3)

    assert isinstance(orchestrator, expected_type)
    assert orchestrator.num_workers == 2
    assert orchestrator.max_concurrent == 3


def test_create_orchestrator_rejects_unknown_phase():
    with pytest.raises(ValueError, match="Unknown phase"):
        create_orchestrator("99")
