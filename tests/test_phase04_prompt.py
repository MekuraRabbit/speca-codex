from pathlib import Path


def test_phase04_prompt_anchors_output_root_and_target_checkout():
    prompt = Path("prompts/04_review_worker.md").read_text(encoding="utf-8")

    assert "Derive `OUTPUT_ROOT` from the directory containing the absolute" in prompt
    assert "do not probe repository-root `outputs/` as a fallback" in prompt
    assert "Then read and cache these files from `OUTPUT_ROOT`" in prompt
    assert "Resolve the target checkout root from `TARGET_INFO.local_checkout`" in prompt
    assert "resolve it relative to the worker's current" in prompt
    assert "not relative to `OUTPUT_ROOT`" in prompt
    assert "Never construct `OUTPUT_ROOT/local_checkout`" in prompt
    assert "`outputs/rehearsal_dvd/target_workspace`" in prompt
    assert "Treat the resolved checkout as the exact target code root" in prompt
    assert "Do not list or search the" in prompt
    assert 'fails with "Access is denied" on Windows' in prompt
    assert "PowerShell `Get-ChildItem` plus" in prompt


def test_phase02c_prompt_anchors_output_root_and_target_checkout():
    prompt = Path("prompts/02c_codelocation_worker.md").read_text(encoding="utf-8")

    assert "Derive `OUTPUT_ROOT` from the directory containing the absolute" in prompt
    assert "do not probe repository-root `outputs/` as a fallback" in prompt
    assert "Read `TARGET_INFO.json` from `OUTPUT_ROOT`" in prompt
    assert "Resolve the target checkout root from `TARGET_INFO.local_checkout`" in prompt
    assert "not relative to `OUTPUT_ROOT`" in prompt
    assert "Treat the resolved checkout as the exact target code root" in prompt
    assert "Register only this" in prompt
    assert "Grep only under the resolved target checkout" in prompt


def test_phase04_prompt_reads_phase03_fields_from_audit_result():
    prompt = Path("prompts/04_review_worker.md").read_text(encoding="utf-8")

    assert "`audit_result`: the Phase 03 finding" in prompt
    assert "read it from the item's `audit_result`" in prompt
    assert "Items with `audit_result.classification`" in prompt
    assert "audit_result.attack_scenario" in prompt
