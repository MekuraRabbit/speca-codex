from pathlib import Path


def test_phase04_prompt_anchors_output_root_and_target_checkout():
    prompt = Path("prompts/04_review_worker.md").read_text(encoding="utf-8")

    assert "Derive `OUTPUT_ROOT` from the directory containing the absolute" in prompt
    assert "do not probe repository-root `outputs/` as a fallback" in prompt
    assert "Then read and cache these files from `OUTPUT_ROOT`" in prompt
    assert "Treat `TARGET_INFO.local_checkout` as the exact target code root" in prompt
    assert "Do not list or search the" in prompt
