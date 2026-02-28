#!/usr/bin/env python3
"""Runner for cppcheck against benchmark datasets."""

import argparse
import json
import logging
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from benchmarks.bench_utils import extract_id, guess_extension
from benchmarks.runners.base_runner import CommandSpec, write_metadata

logger = logging.getLogger(__name__)

CODE_KEYS = ["func", "before", "after", "code"]
ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "benchmarks" / "data"
RESULTS_DIR = ROOT_DIR / "benchmarks" / "results"


def default_output_path(dataset_path: Path) -> Path:
    dataset_name = dataset_path.parent.name
    return RESULTS_DIR / "rq2" / dataset_name / "cppcheck_results.json"


def default_metadata_path(dataset_path: Path) -> Path:
    dataset_name = dataset_path.parent.name
    return RESULTS_DIR / "rq2" / dataset_name / "cppcheck_metadata.json"


def parse_cppcheck_xml(stderr: str) -> list[dict]:
    """Parse cppcheck XML output into a list of finding dicts."""
    findings = []
    try:
        root = ET.fromstring(stderr)
        for error in root.iter("error"):
            severity = error.get("severity", "")
            # Skip informational messages
            if severity in ("information", "debug"):
                continue
            finding = {
                "id": error.get("id", ""),
                "severity": severity,
                "msg": error.get("msg", ""),
                "verbose": error.get("verbose", ""),
                "cwe": error.get("cwe", ""),
            }
            loc = error.find("location")
            if loc is not None:
                finding["line"] = loc.get("line", "")
                finding["column"] = loc.get("column", "")
            findings.append(finding)
    except ET.ParseError:
        pass
    return findings


def run_cppcheck_on_primevul(
    dataset_path: Path,
    output_path: Path,
    timeout: int = 30,
) -> None:
    """Run cppcheck on every sample in the dataset."""
    print(f"--> Running cppcheck on {dataset_path}...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(tempfile.mkdtemp(prefix="cppcheck_", dir=output_path.parent))

    results = []
    try:
        with open(dataset_path, "r") as f:
            for idx, line in enumerate(f):
                sample = json.loads(line)
                func_id = extract_id(sample, idx)

                code = None
                for key in CODE_KEYS:
                    code = sample.get(key)
                    if code is not None:
                        break

                if code is None:
                    results.append({"func_id": func_id, "cppcheck_findings": [], "error": "missing_code"})
                    continue

                ext = guess_extension(sample)
                safe_name = func_id.replace("/", "_").replace("..", "_")
                temp_file = tmp_dir / f"{safe_name}.{ext}"
                temp_file.write_text(code)

                try:
                    process = subprocess.run(
                        [
                            "cppcheck",
                            "--enable=all",
                            "--check-level=exhaustive",
                            "--xml",
                            "--suppress=missingInclude",
                            "--suppress=unmatchedSuppression",
                            str(temp_file),
                        ],
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                    )
                except subprocess.TimeoutExpired:
                    results.append({"func_id": func_id, "cppcheck_findings": [], "error": "timeout"})
                    temp_file.unlink(missing_ok=True)
                    continue

                findings = parse_cppcheck_xml(process.stderr)
                results.append({"func_id": func_id, "cppcheck_findings": findings})
                temp_file.unlink(missing_ok=True)

                if (idx + 1) % 100 == 0:
                    print(f"    Processed {idx + 1} samples...")

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    total_findings = sum(len(r.get("cppcheck_findings", [])) for r in results)
    flagged = sum(1 for r in results if r.get("cppcheck_findings"))
    print(f"    cppcheck: {total_findings} findings in {flagged}/{len(results)} samples")

    metadata_path = default_metadata_path(dataset_path)
    write_metadata(
        CommandSpec(
            dataset=dataset_path,
            output=output_path,
            tmp_dir=tmp_dir,
            command="cppcheck --enable=all --check-level=exhaustive --xml",
            version_command="cppcheck --version",
            timeout=timeout,
            use_shell=False,
            limit=0,
            tool_name="cppcheck",
            metadata=metadata_path,
        ),
    )
    print(f"    Results saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Run cppcheck benchmark runner.")
    parser.add_argument("--dataset", type=Path, default=DATA_DIR / "primevul" / "primevul_test_paired.jsonl")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    output_path = args.output or default_output_path(args.dataset)
    run_cppcheck_on_primevul(args.dataset, output_path, timeout=args.timeout)


if __name__ == "__main__":
    main()
