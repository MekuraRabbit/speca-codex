#!/usr/bin/env python3
"""Generate human review CSVs from Phase 03 positive findings.

Extracts vulnerability/potential-vulnerability findings from 03_PARTIAL_*.json
and writes per-project CSVs for human TP/FP annotation.

Usage:
    uv run python3 benchmarks/rq2a/generate_human_review.py \
      --results-dir benchmarks/results/rq2a/speca
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

# ── Paths & constants ─────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_RESULTS_DIR = SCRIPT_DIR.parent / "results" / "rq2a" / "speca"

PROJECT_ID_TO_NAME = {
    "N1": "baidu/sofa-pbrpc",
    "N2": "ImageMagick/ImageMagick",
    "N3": "coturn/coturn",
    "N4": "OpenKinect/libfreenect",
    "N5": "openldap/openldap",
    "M1": "sass/libsass",
    "M2": "memcached/memcached",
    "M2b": "memcached/memcached",
    "M3": "torvalds/linux",
    "M4": "torvalds/linux",
    "M5": "torvalds/linux",
    "U1": "redis/redis",
    "U2": "torvalds/linux",
    "U3": "shadowsocks/shadowsocks-libev",
    "U4": "WebAssembly/wabt",
    "U5": "unicode-org/icu",
}

# Commit mapping used by the historical RQ2a benchmark dataset.
PROJECT_ID_TO_COMMIT = {
    "N1": "d5ba564a2e62da1fd71bf763e0cfd6ba5b45245b",
    "N2": "6e167ed083e252cb318b4db3316854be80de1693",
    "N3": "47008229cefaff6bfc4b231642d342f99712a5ad",
    "N4": "d913755a25d09fbe2869a0d2acea78f589bfe6bf",
    "N5": "519e0c94c9f3804813f691de487283ad7586f510",
    "M1": "4da7c4bd13b8e9e5cd034f358dceda0bbba917d2",
    "M2": "e15e1d6b967eed53ddcfd61c0c90c38d0b017996",
    "M2b": "dfe439d4cba3748bad5b0c8adaf1b7fb0c98ea40",
    "M3": "4cd8371a234d051f9c9557fcbb1f8c523b1c0d10",
    "M4": "1c4f29ec878bbf1cc0a1eb54ae7da5ff98e19641",
    "M5": "73b73bac90d97400e29e585c678c4d0ebfd2680d",
    "U1": "8fadebfcca0d514fd6949eaa72599ab5e163bd4c",
    "U2": "e79b548b7202bb3accdfe64f113129a4340bc2f9",
    "U3": "8e52029d311df3880ffb1c5bea922f6e0e3cecdd",
    "U4": "b2194657c4b9b90599ae02b36a02a10dbedc32c4",
    "U5": "maint/maint-54",
}

POSITIVE_CLASSIFICATIONS = {"vulnerability", "potential-vulnerability"}

CSV_COLUMNS = [
    "project_id",
    "repo",
    "commit",
    "property_id",
    "classification",
    "code_path",
    "proof_trace",
    "attack_scenario",
    "result",
    "reason",
]


def load_existing_annotations(csv_path: Path) -> dict[str, dict[str, str]]:
    """Load existing human annotations (result/reason) keyed by property_id."""
    annotations: dict[str, dict[str, str]] = {}
    if not csv_path.exists():
        return annotations
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row.get("property_id", "")
            if pid:
                result = row.get("result", "").strip()
                reason = row.get("reason", "").strip()
                if result or reason:
                    annotations[pid] = {"result": result, "reason": reason}
    return annotations


def generate_csv(results_dir: Path) -> None:
    """Generate human_review.csv for each project with positive findings."""
    total_findings = 0
    total_projects = 0

    for project_dir in sorted(results_dir.iterdir()):
        if not project_dir.is_dir():
            continue
        pid = project_dir.name
        if pid not in PROJECT_ID_TO_NAME:
            continue

        # Load Phase 03 findings
        findings: list[dict] = []
        for f in sorted(project_dir.glob("03_PARTIAL_*.json")):
            data = json.loads(f.read_text())
            findings.extend(data.get("audit_items", []))

        # Filter positive only
        positive = [
            f for f in findings
            if f.get("classification") in POSITIVE_CLASSIFICATIONS
        ]
        if not positive:
            continue

        csv_path = project_dir / "human_review.csv"

        # Preserve existing annotations
        annotations = load_existing_annotations(csv_path)
        preserved = sum(1 for a in annotations.values() if a.get("result"))

        repo = PROJECT_ID_TO_NAME.get(pid, "")
        commit = PROJECT_ID_TO_COMMIT.get(pid, "")

        rows = []
        for finding in positive:
            prop_id = finding.get("property_id", "")
            existing = annotations.get(prop_id, {})
            rows.append({
                "project_id": pid,
                "repo": repo,
                "commit": commit,
                "property_id": prop_id,
                "classification": finding.get("classification", ""),
                "code_path": finding.get("code_path", ""),
                "proof_trace": finding.get("proof_trace", ""),
                "attack_scenario": finding.get("attack_scenario", ""),
                "result": existing.get("result", ""),
                "reason": existing.get("reason", ""),
            })

        with csv_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)

        total_findings += len(rows)
        total_projects += 1
        print(f"  {pid}: {len(rows)} findings -> {csv_path}"
              + (f" ({preserved} annotations preserved)" if preserved else ""))

    print(f"\nTotal: {total_findings} positive findings across {total_projects} projects")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate human review CSVs from Phase 03 positive findings"
    )
    parser.add_argument(
        "--results-dir", type=Path, default=DEFAULT_RESULTS_DIR,
        help="Directory with SPECA results (project subdirs)",
    )
    args = parser.parse_args()

    print("Generating human review CSVs...\n")
    generate_csv(args.results_dir)


if __name__ == "__main__":
    main()
