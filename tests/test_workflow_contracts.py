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


def test_public_audit_workflows_do_not_commit_logs():
    workflow_paths = [
        ROOT / ".github" / "workflows" / "01a-discovery.yml",
        ROOT / ".github" / "workflows" / "01b-subgraph.yml",
        ROOT / ".github" / "workflows" / "01e-properties.yml",
        ROOT / ".github" / "workflows" / "02c-enrich-code.yml",
        ROOT / ".github" / "workflows" / "03-audit-map.yml",
        ROOT / ".github" / "workflows" / "04-audit-review.yml",
        ROOT / ".github" / "workflows" / "full-audit.yml",
    ]

    for path in workflow_paths:
        workflow = path.read_text(encoding="utf-8")
        assert "git add outputs/logs/" not in workflow


def test_public_audit_workflows_upload_logs_only_when_requested():
    workflow_paths = [
        ROOT / ".github" / "workflows" / "01a-discovery.yml",
        ROOT / ".github" / "workflows" / "01b-subgraph.yml",
        ROOT / ".github" / "workflows" / "01e-properties.yml",
        ROOT / ".github" / "workflows" / "02c-enrich-code.yml",
        ROOT / ".github" / "workflows" / "03-audit-map.yml",
        ROOT / ".github" / "workflows" / "04-audit-review.yml",
        ROOT / ".github" / "workflows" / "full-audit.yml",
    ]

    for path in workflow_paths:
        workflow = path.read_text(encoding="utf-8")
        assert "upload_logs:" in workflow
        assert "if: ${{ always() && inputs.upload_logs }}" in workflow


def test_legacy_claude_workflows_require_bypass_acknowledgement():
    workflow_paths = [
        ROOT / ".github" / "workflows" / "01a-discovery.yml",
        ROOT / ".github" / "workflows" / "01b-subgraph.yml",
        ROOT / ".github" / "workflows" / "01e-properties.yml",
        ROOT / ".github" / "workflows" / "02c-enrich-code.yml",
        ROOT / ".github" / "workflows" / "03-audit-map.yml",
        ROOT / ".github" / "workflows" / "04-audit-review.yml",
    ]
    acknowledgement = "I_UNDERSTAND_THIS_RUNS_LEGACY_CLAUDE_WITH_BYPASS_PERMISSIONS"

    for path in workflow_paths:
        workflow = path.read_text(encoding="utf-8")
        assert "CLAUDE_CODE_PERMISSIONS: bypassPermissions" in workflow
        assert "confirm_legacy_claude_bypass:" in workflow
        assert acknowledgement in workflow
        assert "legacy-claude-bypass-guard" in workflow
        assert "This workflow runs the legacy Claude runner with bypassPermissions" in workflow


def test_full_audit_requires_explicit_public_output_acknowledgement():
    workflow = (ROOT / ".github" / "workflows" / "full-audit.yml").read_text(
        encoding="utf-8"
    )

    acknowledgement = "I_UNDERSTAND_THIS_PUSHES_AUDIT_OUTPUTS_TO_PUBLIC_BRANCHES"
    assert acknowledgement in workflow
    assert "public-output-guard" in workflow
    assert "full-audit is disabled by default in this public fork" in workflow
    assert "legacy Claude runner with bypassPermissions" in workflow
    assert "inputs.upload_logs" in workflow
