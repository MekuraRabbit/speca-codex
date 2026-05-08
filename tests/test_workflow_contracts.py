from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_target_info_workflows_write_local_checkout_contract():
    workflow_paths = [
        ROOT / ".github" / "workflows" / "02c-enrich-code.yml",
        ROOT / ".github" / "workflows" / "full-audit.yml",
        ROOT / ".github" / "workflows" / "rq2a-03-audit-map.yml",
        ROOT / ".github" / "workflows" / "rq2a-03-audit-map-sonnet4.yml",
        ROOT / ".github" / "workflows" / "rq2a-03-audit-map-deepseek-r1.yml",
    ]

    for path in workflow_paths:
        workflow = path.read_text(encoding="utf-8")
        assert '"local_checkout": "target_workspace"' in workflow
        assert '"language": ""' in workflow
