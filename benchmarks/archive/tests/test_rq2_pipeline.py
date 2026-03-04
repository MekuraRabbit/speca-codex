#!/usr/bin/env python3
"""Tests for the RQ2 benchmark evaluation pipeline.

Verifies that evaluate.py, generate_report.py, and visualize.py work
correctly with mock data — including the case where only some tools
(e.g. semgrep only) have results.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Ensure project root is importable
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.rq2.evaluate import evaluate_dataset
from benchmarks.metrics.classification import compute_confusion, compute_confusion_subset
from benchmarks.metrics.stats import (
    bootstrap_metric_diffs,
    bootstrap_rate,
    effect_size_cliffs_delta,
    mcnemar_exact,
)
from benchmarks.tools.loaders import load_semgrep_results, load_jsonl_predictions
from benchmarks.bench_utils import extract_id, extract_label, normalize_bool, guess_extension


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_dataset(tmp_path: Path) -> Path:
    """Create a minimal PrimeVul-like JSONL dataset."""
    samples = [
        # Vulnerable samples
        {"id": "v1", "func": "void vuln1() { gets(buf); }", "vul_type": "CWE-120", "cwe_id": "CWE-120", "pair_id": "p1", "language": "c"},
        {"id": "c1", "func": "void clean1() { fgets(buf, n, stdin); }", "vul_type": "clean", "cwe_id": "CWE-120", "pair_id": "p1", "language": "c"},
        {"id": "v2", "func": "void vuln2() { sprintf(buf, fmt); }", "vul_type": "CWE-134", "cwe_id": "CWE-134", "pair_id": "p2", "language": "c"},
        {"id": "c2", "func": "void clean2() { snprintf(buf, n, fmt); }", "vul_type": "clean", "cwe_id": "CWE-134", "pair_id": "p2", "language": "c"},
        {"id": "v3", "func": "void vuln3() { strcpy(dst, src); }", "vul_type": "CWE-120", "cwe_id": "CWE-120", "pair_id": "p3", "language": "c"},
        {"id": "c3", "func": "void clean3() { strncpy(dst, src, n); }", "vul_type": "clean", "cwe_id": "CWE-120", "pair_id": "p3", "language": "c"},
        {"id": "v4", "func": "void vuln4() { system(cmd); }", "vul_type": "CWE-78", "cwe_id": "CWE-78", "pair_id": "p4", "language": "c"},
        {"id": "c4", "func": "void clean4() { execvp(cmd, args); }", "vul_type": "clean", "cwe_id": "CWE-78", "pair_id": "p4", "language": "c"},
    ]
    dataset_dir = tmp_path / "mock_dataset"
    dataset_dir.mkdir()
    dataset_path = dataset_dir / "mock_test_paired.jsonl"
    with dataset_path.open("w") as f:
        for sample in samples:
            f.write(json.dumps(sample) + "\n")
    return dataset_path


@pytest.fixture
def mock_semgrep_results(tmp_path: Path) -> Path:
    """Create mock semgrep results (JSON list format)."""
    results = [
        {"func_id": "v1", "semgrep_findings": [{"check_id": "c-gets-dangerous", "severity": "ERROR"}]},
        {"func_id": "c1", "semgrep_findings": []},
        {"func_id": "v2", "semgrep_findings": []},  # missed
        {"func_id": "c2", "semgrep_findings": []},
        {"func_id": "v3", "semgrep_findings": [{"check_id": "c-strcpy-overflow", "severity": "WARNING"}]},
        {"func_id": "c3", "semgrep_findings": []},
        {"func_id": "v4", "semgrep_findings": [{"check_id": "c-system-injection", "severity": "ERROR"}]},
        {"func_id": "c4", "semgrep_findings": [{"check_id": "c-exec-taint", "severity": "WARNING"}]},  # FP
    ]
    results_dir = tmp_path / "results" / "rq2" / "mock_dataset"
    results_dir.mkdir(parents=True)
    path = results_dir / "semgrep_results.json"
    path.write_text(json.dumps(results, indent=2))
    return path


@pytest.fixture
def mock_codeql_results(tmp_path: Path) -> Path:
    """Create mock CodeQL results (JSONL format)."""
    results = [
        {"id": "v1", "predicted_vulnerable": True, "confidence": 0.9},
        {"id": "c1", "predicted_vulnerable": False, "confidence": 0.8},
        {"id": "v2", "predicted_vulnerable": True, "confidence": 0.7},
        {"id": "c2", "predicted_vulnerable": False, "confidence": 0.9},
        {"id": "v3", "predicted_vulnerable": False, "confidence": 0.6},  # missed
        {"id": "c3", "predicted_vulnerable": False, "confidence": 0.9},
        {"id": "v4", "predicted_vulnerable": True, "confidence": 0.8},
        {"id": "c4", "predicted_vulnerable": False, "confidence": 0.7},
    ]
    results_dir = tmp_path / "results" / "rq2" / "mock_dataset"
    results_dir.mkdir(parents=True, exist_ok=True)
    path = results_dir / "codeql_results.jsonl"
    with path.open("w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")
    return path


# ---------------------------------------------------------------------------
# Unit tests: bench_utils
# ---------------------------------------------------------------------------

class TestBenchUtils:
    def test_normalize_bool(self):
        assert normalize_bool(True) is True
        assert normalize_bool(False) is False
        assert normalize_bool(1) is True
        assert normalize_bool(0) is False
        assert normalize_bool("true") is True
        assert normalize_bool("false") is False
        assert normalize_bool("vulnerable") is True
        assert normalize_bool("clean") is False
        assert normalize_bool(None) is None
        assert normalize_bool("maybe") is None

    def test_extract_id(self):
        assert extract_id({"id": "abc"}, 0) == "abc"
        assert extract_id({"func_hash": "h123"}, 0) == "h123"
        assert extract_id({}, 5) == "sample-5"

    def test_extract_label(self):
        assert extract_label({"label": True}) is True
        assert extract_label({"is_vulnerable": 1}) is True
        assert extract_label({"vulnerable": "false"}) is False
        assert extract_label({}) is None

    def test_guess_extension(self):
        assert guess_extension({"language": "c"}) == "c"
        assert guess_extension({"language": "python"}) == "py"
        assert guess_extension({"filename": "foo.java"}) == "java"
        assert guess_extension({}) == "txt"


# ---------------------------------------------------------------------------
# Unit tests: classification
# ---------------------------------------------------------------------------

class TestClassification:
    def test_compute_confusion_basic(self):
        predictions = {"a": True, "b": False, "c": True, "d": False}
        ground_truth = {"a": True, "b": False, "c": False, "d": True}
        result = compute_confusion(predictions, ground_truth)
        assert result["tp"] == 1  # a
        assert result["tn"] == 1  # b
        assert result["fp"] == 1  # c
        assert result["fn"] == 1  # d
        assert result["accuracy"] == 0.5
        assert result["precision"] == 0.5
        assert result["recall"] == 0.5

    def test_compute_confusion_all_correct(self):
        predictions = {"a": True, "b": False}
        ground_truth = {"a": True, "b": False}
        result = compute_confusion(predictions, ground_truth)
        assert result["tp"] == 1
        assert result["tn"] == 1
        assert result["fp"] == 0
        assert result["fn"] == 0
        assert result["accuracy"] == 1.0

    def test_compute_confusion_missing_predictions(self):
        predictions = {"a": True}
        ground_truth = {"a": True, "b": False}
        result = compute_confusion(predictions, ground_truth)
        assert result["skipped_missing_pred"] == 1

    def test_compute_confusion_subset(self):
        predictions = {"a": True, "b": False, "c": True}
        ground_truth = {"a": True, "b": False, "c": False}
        result = compute_confusion_subset(predictions, ground_truth, ["a", "b"])
        assert result["tp"] == 1
        assert result["tn"] == 1
        assert result["fp"] == 0


# ---------------------------------------------------------------------------
# Unit tests: stats
# ---------------------------------------------------------------------------

class TestStats:
    def test_mcnemar_exact_symmetric(self):
        assert mcnemar_exact(0, 0) == 1.0
        assert mcnemar_exact(5, 5) == pytest.approx(1.0, abs=0.01)

    def test_mcnemar_exact_asymmetric(self):
        p = mcnemar_exact(10, 2)
        assert 0.0 < p < 0.05

    def test_effect_size_zero(self):
        delta, label = effect_size_cliffs_delta(0, 0, 0)
        assert delta == 0.0
        assert label == "none"

    def test_effect_size_large(self):
        delta, label = effect_size_cliffs_delta(50, 0, 100)
        assert delta == 0.5
        assert label == "large"

    def test_bootstrap_rate_empty(self):
        result = bootstrap_rate([], 100, 42, 0.95)
        assert result["mean"] == 0.0
        assert result["ci"] == [0.0, 0.0]

    def test_bootstrap_rate_all_true(self):
        result = bootstrap_rate([True] * 100, 1000, 42, 0.95)
        assert result["mean"] == pytest.approx(1.0, abs=0.01)

    def test_bootstrap_metric_diffs(self):
        tool_a = {"a": True, "b": False, "c": True, "d": True}
        tool_b = {"a": True, "b": True, "c": False, "d": False}
        gt = {"a": True, "b": False, "c": True, "d": True}
        case_ids = ["a", "b", "c", "d"]
        result = bootstrap_metric_diffs(tool_a, tool_b, gt, case_ids, samples=100, seed=42, ci_level=0.95)
        assert "accuracy" in result
        assert "f1" in result
        assert "ci" in result["accuracy"]

    def test_bootstrap_metric_diffs_empty(self):
        result = bootstrap_metric_diffs({}, {}, {}, [], samples=100, seed=42, ci_level=0.95)
        assert result["accuracy"]["mean"] == 0.0


# ---------------------------------------------------------------------------
# Unit tests: loaders
# ---------------------------------------------------------------------------

class TestLoaders:
    def test_load_semgrep_results(self, mock_semgrep_results: Path):
        result = load_semgrep_results(mock_semgrep_results)
        assert result is not None
        predictions, error_count, extras = result
        assert predictions["v1"] is True   # has findings
        assert predictions["c1"] is False  # no findings
        assert predictions["v2"] is False  # missed (no findings)
        assert error_count == 0

    def test_load_semgrep_results_missing_file(self, tmp_path: Path):
        result = load_semgrep_results(tmp_path / "nonexistent.json")
        assert result is None

    def test_load_jsonl_predictions(self, mock_codeql_results: Path):
        result = load_jsonl_predictions(mock_codeql_results)
        assert result is not None
        predictions, error_count, extras = result
        assert predictions["v1"] is True
        assert predictions["c1"] is False
        assert error_count == 0


# ---------------------------------------------------------------------------
# Integration test: evaluate_dataset
# ---------------------------------------------------------------------------

class TestEvaluateDataset:
    def test_evaluate_with_semgrep_only(self, mock_dataset: Path, mock_semgrep_results: Path, tmp_path: Path, monkeypatch):
        """Evaluate should work with only semgrep results (no security_agent, no LLM)."""
        monkeypatch.setattr("benchmarks.rq2.evaluate.RESULTS_DIR", tmp_path / "results" / "rq2")
        metrics = evaluate_dataset("mock_dataset", mock_dataset)

        assert metrics["dataset"]["name"] == "mock_dataset"
        assert metrics["dataset"]["sample_count"] == 8
        assert metrics["dataset"]["ground_truth_count"] == 8

        # Semgrep should have results
        semgrep = metrics["tools"]["semgrep"]
        assert semgrep["status"] == "ok"
        assert semgrep["tp"] == 3  # v1, v3, v4 detected
        assert semgrep["fp"] == 1  # c4 false positive
        assert semgrep["fn"] == 1  # v2 missed
        assert semgrep["tn"] == 3  # c1, c2, c3

        # Other tools should be missing
        assert metrics["tools"]["security_agent"]["status"] == "missing_results"
        assert metrics["tools"]["llm_baseline"]["status"] == "missing_results"

        # CWE coverage
        assert "cwe_coverage" in semgrep
        cwe120 = semgrep["cwe_coverage"].get("CWE-120", {})
        assert cwe120["tp"] == 2  # v1, v3
        assert cwe120["total"] == 2

        # Pairwise correctness
        assert "pairwise" in semgrep
        # p1: v1=True, c1=False -> correct
        # p2: v2=False, c2=False -> wrong (missed vuln)
        # p3: v3=True, c3=False -> correct
        # p4: v4=True, c4=True -> wrong (FP on clean)
        assert semgrep["pairwise"]["correct"] == 2
        assert semgrep["pairwise"]["scored"] == 4

        # No pairwise stats (security_agent missing)
        assert metrics["comparisons"]["pairwise_stats"] == {}

    def test_evaluate_with_semgrep_and_codeql(self, mock_dataset: Path, mock_semgrep_results: Path, mock_codeql_results: Path, tmp_path: Path, monkeypatch):
        """Evaluate should work with semgrep + codeql results."""
        monkeypatch.setattr("benchmarks.rq2.evaluate.RESULTS_DIR", tmp_path / "results" / "rq2")
        metrics = evaluate_dataset("mock_dataset", mock_dataset)

        semgrep = metrics["tools"]["semgrep"]
        codeql = metrics["tools"]["codeql"]
        assert semgrep["status"] == "ok"
        assert codeql["status"] == "ok"

        # CodeQL metrics
        assert codeql["tp"] == 3  # v1, v2, v4
        assert codeql["fn"] == 1  # v3 missed
        assert codeql["fp"] == 0
        assert codeql["tn"] == 4

    def test_evaluate_no_dataset(self, tmp_path: Path, monkeypatch):
        """Evaluate should handle missing dataset gracefully."""
        monkeypatch.setattr("benchmarks.rq2.evaluate.RESULTS_DIR", tmp_path / "results" / "rq2")
        metrics = evaluate_dataset("missing", tmp_path / "nonexistent.jsonl")
        assert metrics["dataset"]["ground_truth_count"] == 0


# ---------------------------------------------------------------------------
# Integration test: generate_report
# ---------------------------------------------------------------------------

class TestGenerateReport:
    def test_report_generation(self, mock_dataset: Path, mock_semgrep_results: Path, tmp_path: Path, monkeypatch):
        """Generate report should produce valid markdown with semgrep-only results."""
        monkeypatch.setattr("benchmarks.rq2.evaluate.RESULTS_DIR", tmp_path / "results" / "rq2")
        metrics = evaluate_dataset("mock_dataset", mock_dataset)

        metrics_path = tmp_path / "metrics.json"
        metrics_path.write_text(json.dumps(metrics, indent=2))
        report_path = tmp_path / "report.md"

        from benchmarks.rq2.generate_report import main as generate_main
        monkeypatch.setattr("sys.argv", [
            "generate_report.py",
            "--metrics", str(metrics_path),
            "--output", str(report_path),
        ])
        ret = generate_main()
        assert ret == 0
        assert report_path.exists()

        content = report_path.read_text()
        assert "# Benchmark Report" in content
        assert "## Tool Metrics" in content
        assert "semgrep" in content
        # CWE coverage table should dynamically include only semgrep
        assert "Semgrep Recall" in content
        # Should NOT have hardcoded columns for tools without results
        assert "Security Agent Recall" not in content


# ---------------------------------------------------------------------------
# Integration test: visualize (if matplotlib available)
# ---------------------------------------------------------------------------

class TestVisualize:
    def test_visualize_charts(self, mock_dataset: Path, mock_semgrep_results: Path, tmp_path: Path, monkeypatch):
        """Visualize should produce PNG figures from metrics."""
        pytest.importorskip("matplotlib")
        pytest.importorskip("numpy")

        monkeypatch.setattr("benchmarks.rq2.evaluate.RESULTS_DIR", tmp_path / "results" / "rq2")
        metrics = evaluate_dataset("mock_dataset", mock_dataset)

        metrics_path = tmp_path / "metrics.json"
        metrics_path.write_text(json.dumps(metrics, indent=2))
        output_dir = tmp_path / "figures"

        from benchmarks.rq2.visualize import main as visualize_main
        monkeypatch.setattr("sys.argv", [
            "visualize.py",
            "--metrics", str(metrics_path),
            "--output-dir", str(output_dir),
        ])
        ret = visualize_main()
        assert ret == 0
        assert output_dir.exists()
        # At least fig1 and fig4 should be created (fig3/5 depend on CWE data)
        assert (output_dir / "fig1_tool_comparison.png").exists()
        assert (output_dir / "fig4_overview.png").exists()
