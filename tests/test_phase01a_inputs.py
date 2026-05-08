from scripts.orchestrator.factory import create_orchestrator
from scripts.orchestrator.config import get_phase_config
from scripts.orchestrator.paths import output_root_context
from scripts.orchestrator.resume import ResumeManager


def test_phase01a_loads_seed_urls_from_runtime_env(tmp_path):
    with output_root_context(tmp_path):
        orch = create_orchestrator("01a", num_workers=1, max_concurrent=1)
        orch.config.runtime_env["SPEC_URLS"] = (
            "https://example.com/a, https://example.com/b\n"
            "https://example.com/c"
        )

        items = orch.load_items()

    assert [item["url"] for item in items] == [
        "https://example.com/a",
        "https://example.com/b",
        "https://example.com/c",
    ]
    assert [item["id"] for item in items] == ["seed-0", "seed-1", "seed-2"]


def test_phase01a_merges_batch_results_into_state_file(tmp_path):
    with output_root_context(tmp_path):
        orch = create_orchestrator("01a", num_workers=1, max_concurrent=1)
        orch.results = [
            {
                "start_url": "https://example.com/a",
                "found_specs": [
                    {"url": "https://example.com/a", "title": "A"},
                    {"url": "https://example.com/shared", "title": "Shared"},
                ],
                "metadata": {"urls_visited": ["https://example.com/a"]},
            },
            {
                "start_url": "https://example.com/b",
                "found_specs": [
                    {"url": "https://example.com/shared", "title": "Shared duplicate"},
                    {"url": "https://example.com/b", "title": "B"},
                ],
                "metadata": {"urls_visited": ["https://example.com/b"]},
            },
        ]

        orch._after_batches_completed()

        state = (tmp_path / "01a_STATE.json").read_text(encoding="utf-8")

    assert "https://example.com/a" in state
    assert "https://example.com/b" in state
    assert state.count("https://example.com/shared") == 1


def test_phase01a_does_not_write_state_file_for_partial_failure(tmp_path):
    with output_root_context(tmp_path):
        orch = create_orchestrator("01a", num_workers=1, max_concurrent=1)
        orch.results = [
            {
                "start_url": "https://example.com/a",
                "found_specs": [{"url": "https://example.com/a", "title": "A"}],
            }
        ]
        orch.failed_batches.append((0, 1))

        orch._after_batches_completed()

    assert not (tmp_path / "01a_STATE.json").exists()


def test_phase01a_force_cleanup_deletes_canonical_state(tmp_path):
    state_path = tmp_path / "01a_STATE.json"
    partial_path = tmp_path / "01a_PARTIAL_W0B0_123.json"
    state_path.write_text('{"found_specs":[]}', encoding="utf-8")
    partial_path.write_text('{"found_specs":[]}', encoding="utf-8")

    with output_root_context(tmp_path):
        deleted = ResumeManager(get_phase_config("01a")).cleanup_all_outputs(dry_run=False)

    assert deleted == 2
    assert not state_path.exists()
    assert not partial_path.exists()
