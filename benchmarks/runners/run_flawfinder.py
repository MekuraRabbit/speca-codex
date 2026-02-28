#!/usr/bin/env python3
"""Runner for flawfinder against benchmark datasets."""

import argparse
import csv
import io
import json
import logging
import shutil
import subprocess
import sys
import tempfile
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
    return RESULTS_DIR / "rq2" / dataset_name / "flawfinder_results.json"


def default_metadata_path(dataset_path: Path) -> Path:
    dataset_name = dataset_path.parent.name
    return RESULTS_DIR / "rq2" / dataset_name / "flawfinder_metadata.json"


def parse_flawfinder_csv(stdout: str) -> list[dict]:
    """Parse flawfinder CSV output into a list of finding dicts."""
    findings = []
    if not stdout.strip():
        return findings
    reader = csv.DictReader(io.StringIO(stdout))
    for row in reader:
        level = int(row.get("Level", row.get("DefaultLevel", "0")) or "0")
        # flawfinder levels: 0=no risk, 1-2=low, 3=medium, 4-5=high
        # Only count level >= 1 as findings
        if level < 1:
            continue
        findings.append({
            "line": row.get("Line", ""),
            "level": level,
            "category": row.get("Category", ""),
            "name": row.get("Name", ""),
            "warning": row.get("Warning", ""),
            "cwes": row.get("CWEs", ""),
        })
    return findings


def run_flawfinder_on_primevul(
    dataset_path: Path,
    output_path: Path,
    min_level: int = 1,
    timeout: int = 30,
) -> None:
    """Run flawfinder on every sample in the dataset."""
    print(f"--> Running flawfinder on {dataset_path}...")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_dir = Path(tempfile.mkdtemp(prefix="flawfinder_", dir=output_path.parent))

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
                    results.append({"func_id": func_id, "flawfinder_findings": [], "error": "missing_code"})
                    continue

                ext = guess_extension(sample)
                safe_name = func_id.replace("/", "_").replace("..", "_")
                temp_file = tmp_dir / f"{safe_name}.{ext}"
                temp_file.write_text(code)

                try:
                    process = subprocess.run(
                        [
                            "flawfinder",
                            "--csv",
                            f"--minlevel={min_level}",
                            str(temp_file),
                        ],
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                    )
                except subprocess.TimeoutExpired:
                    results.append({"func_id": func_id, "flawfinder_findings": [], "error": "timeout"})
                    temp_file.unlink(missing_ok=True)
                    continue

                findings = parse_flawfinder_csv(process.stdout)
                results.append({"func_id": func_id, "flawfinder_findings": findings})
                temp_file.unlink(missing_ok=True)

                if (idx + 1) % 100 == 0:
                    print(f"    Processed {idx + 1} samples...")

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    total_findings = sum(len(r.get("flawfinder_findings", [])) for r in results)
    flagged = sum(1 for r in results if r.get("flawfinder_findings"))
    print(f"    flawfinder: {total_findings} findings in {flagged}/{len(results)} samples")

    metadata_path = default_metadata_path(dataset_path)
    write_metadata(
        CommandSpec(
            dataset=dataset_path,
            output=output_path,
            tmp_dir=tmp_dir,
            command=f"flawfinder --csv --minlevel={min_level}",
            version_command="flawfinder --version",
            timeout=timeout,
            use_shell=False,
            limit=0,
            tool_name="flawfinder",
            metadata=metadata_path,
        ),
    )
    print(f"    Results saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Run flawfinder benchmark runner.")
    parser.add_argument("--dataset", type=Path, default=DATA_DIR / "primevul" / "primevul_test_paired.jsonl")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--min-level", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    output_path = args.output or default_output_path(args.dataset)
    run_flawfinder_on_primevul(args.dataset, output_path, min_level=args.min_level, timeout=args.timeout)


if __name__ == "__main__":
    main()
