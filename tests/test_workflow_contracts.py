from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


REMOVED_LEGACY_CLAUDE_WORKFLOWS = [
    ROOT / ".github" / "workflows" / "01a-discovery.yml",
    ROOT / ".github" / "workflows" / "01b-subgraph.yml",
    ROOT / ".github" / "workflows" / "01e-properties.yml",
    ROOT / ".github" / "workflows" / "02c-enrich-code.yml",
    ROOT / ".github" / "workflows" / "03-audit-map.yml",
    ROOT / ".github" / "workflows" / "04-audit-review.yml",
    ROOT / ".github" / "workflows" / "full-audit.yml",
    ROOT / ".github" / "workflows" / "benchmark-rq1-01-setup.yml",
    ROOT / ".github" / "workflows" / "benchmark-rq1-02-eval-recall.yml",
    ROOT / ".github" / "workflows" / "benchmark-rq1-03-eval-fp.yml",
    ROOT / ".github" / "workflows" / "benchmark-rq1-035-collect-phase04.yml",
    ROOT / ".github" / "workflows" / "benchmark-rq1-04-report.yml",
    ROOT / ".github" / "workflows" / "rq2a-01-setup-dataset.yml",
    ROOT / ".github" / "workflows" / "rq2a-02-visualize.yml",
    ROOT / ".github" / "workflows" / "rq2a-03-audit-map.yml",
    ROOT / ".github" / "workflows" / "rq2a-03-audit-map-deepseek-r1.yml",
    ROOT / ".github" / "workflows" / "rq2a-03-audit-map-sonnet4.yml",
    ROOT / ".github" / "workflows" / "rq2a-04-evaluate.yml",
    ROOT / ".github" / "workflows" / "rq2a-04-evaluate-deepseek-r1.yml",
    ROOT / ".github" / "workflows" / "rq2a-04-evaluate-sonnet4.yml",
    ROOT / ".github" / "workflows" / "rq2b-01-setup-dataset.yml",
    ROOT / ".github" / "workflows" / "rq2b-02-visualize.yml",
]


def test_legacy_claude_execution_workflows_are_not_shipped():
    for path in REMOVED_LEGACY_CLAUDE_WORKFLOWS:
        assert not path.exists()


def test_public_workflows_do_not_stage_logs():
    for path in (ROOT / ".github" / "workflows").glob("*.yml"):
        workflow = path.read_text(encoding="utf-8")
        assert "git add outputs/logs/" not in workflow


def test_readme_points_to_local_codex_runs_instead_of_removed_actions():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "does not ship the old Claude phase workflows" in readme
    for path in REMOVED_LEGACY_CLAUDE_WORKFLOWS:
        assert f"`{path.name}`" not in readme
