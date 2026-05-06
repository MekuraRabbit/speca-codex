"""Windows-friendly input JSON loading."""

import json
from pathlib import Path

from scripts.orchestrator.base import Phase02cOrchestrator
from scripts.orchestrator.paths import output_root_context


def test_phase02c_loads_utf8_bom_seed_partials(tmp_path: Path):
    output_dir = tmp_path / "outputs"
    output_dir.mkdir()
    (output_dir / "01b_PARTIAL_seed.json").write_text(
        json.dumps({
            "specs": [{
                "source_url": "https://example.test/spec",
                "title": "Spec",
                "sub_graphs": [{
                    "id": "SG-1",
                    "name": "Withdrawal invariant",
                    "mermaid_file": "outputs/graphs/sg.mmd",
                }],
            }],
        }),
        encoding="utf-8-sig",
    )
    (output_dir / "01e_PARTIAL_seed.json").write_text(
        json.dumps({
            "properties": [{
                "property_id": "PROP-1",
                "text": "Caller balance is cleared before transfer.",
                "type": "invariant",
                "assertion": "balance is cleared before external call",
                "severity": "High",
                "covers": "SG-1",
                "reachability": {"bug_bounty_scope": "in-scope"},
            }],
        }),
        encoding="utf-8-sig",
    )

    with output_root_context(output_dir):
        orch = Phase02cOrchestrator("02c", num_workers=1, max_concurrent=1)
        items = orch.load_items()

    index = json.loads((output_dir / "01b_SUBGRAPH_INDEX.json").read_text())
    assert [item["property_id"] for item in items] == ["PROP-1"]
    assert index[0]["subgraphs"][0]["id"] == "SG-1"
