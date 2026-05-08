from pathlib import Path


def test_phase06_report_prompt_uses_current_run_artifacts():
    prompt = Path("prompts/06_report.md").read_text(encoding="utf-8")

    assert "$OUTPUT_DIR" in prompt
    assert "03_PARTIAL_*.json" in prompt
    assert "04_PARTIAL_*.json" in prompt
    assert "05_POC_CANDIDATES.json" in prompt
    assert "05_POC_RESULT_<candidate_id>.json" in prompt
    assert "source_items[].original_property_id" in prompt
    assert "source_items[].property_id" in prompt
    assert "TARGET_INFO.local_checkout" in prompt
    assert "docs/report_templates/<report_type_lower>.md" in prompt
    assert "security-agent/" not in prompt
    assert "03_AUDITMAP.json" not in prompt
    assert "01_BOUNTY_GUIDELINE" not in prompt


def test_phase06b_audit_report_prompt_uses_current_partial_schema():
    prompt = Path("prompts/06b_audit_report.md").read_text(encoding="utf-8")

    assert "$OUTPUT_DIR" in prompt
    assert "01b_PARTIAL_*.json" in prompt
    assert "01e_PARTIAL_*.json" in prompt
    assert "02c_PARTIAL_*.json" in prompt
    assert "03_PARTIAL_*.json" in prompt
    assert "04_PARTIAL_*.json" in prompt
    assert "05_POC_CANDIDATES.json" in prompt
    assert "source_items[].original_property_id" in prompt
    assert "source_items[].property_id" in prompt
    assert "review_verdict" in prompt
    assert "Do not read repository-root `outputs/` as a fallback" in prompt
    assert "security-agent/" not in prompt
    assert "03_AUDITMAP.json" not in prompt
    assert "01_SPEC.json" not in prompt
    assert "03b_FUZZING_RESULTS.json" not in prompt
