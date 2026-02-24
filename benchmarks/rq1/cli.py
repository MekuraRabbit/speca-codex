#!/usr/bin/env python3
"""Compare audit map findings against Sherlock CSV dataset (CLI wrapper)."""
from __future__ import annotations

import argparse
from pathlib import Path

from benchmarks.rq1.evaluate import evaluate_branches, parse_branches

ROOT_DIR = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare Sherlock dataset vs audit map outputs")
    parser.add_argument("--branches", required=True, help="Comma-separated branch names")
    parser.add_argument(
        "--csv",
        default=str(
            ROOT_DIR
            / "benchmarks"
            / "data"
            / "rq1"
            / "sherlock_contest_1140_issues_1766639267091.csv"
        ),
    )
    parser.add_argument(
        "--results-dir",
        default=str(ROOT_DIR / "benchmarks" / "results" / "rq1" / "sherlock_ethereum_audit_contest"),
    )
    parser.add_argument("--llm-max", type=int, default=200)
    parser.add_argument("--baseline-results", type=str, default="", help="Baseline results dir with evaluation_*.json")
    parser.add_argument("--bootstrap-samples", type=int, default=2000)
    parser.add_argument("--bootstrap-seed", type=int, default=42)
    parser.add_argument("--ci-level", type=float, default=0.95)
    parser.add_argument("--human-scope", type=str, default="new_only", choices=["new_only", "all"])
    parser.add_argument("--human-sample-size", type=int, default=0)
    parser.add_argument("--human-sample-out", type=str, default="", help="Output path for human evaluation sample JSONL")
    parser.add_argument("--human-labels", type=str, default="", help="Human labels JSONL path")
    parser.add_argument("--human-labels-report", type=str, default="", help="Validation report output path (JSON)")
    parser.add_argument("--metadata", type=str, default="", help="Run metadata JSON to include in summary")
    parser.add_argument(
        "--audit-classifications",
        type=str,
        default="vulnerability,potential-vulnerability",
        help="Comma-separated audit classifications to include",
    )
    parser.add_argument(
        "--client-filter",
        type=str,
        default="none",
        choices=["none", "auto", "keywords"],
        help="Filter issues to client-specific subset (auto infers from branch/target info)",
    )
    parser.add_argument(
        "--client-keywords",
        type=str,
        default="",
        help="Comma-separated keywords for issue filtering (used when client-filter=keywords or to override auto)",
    )
    parser.add_argument(
        "--reparse",
        action="store_true",
        default=False,
        help="Re-parse cached LLM responses without calling the LLM again",
    )
    args = parser.parse_args()
    results_dir = Path(args.results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    audit_classifications = {
        item.strip().lower()
        for item in args.audit_classifications.split(",")
        if item.strip()
    }
    if not audit_classifications:
        audit_classifications = None
    client_keywords = [item.strip() for item in args.client_keywords.split(",") if item.strip()]
    client_filter = args.client_filter
    if client_filter == "keywords" and not client_keywords:
        client_filter = "none"

    evaluate_branches(
        branches=parse_branches(args.branches),
        csv_path=Path(args.csv),
        results_dir=results_dir,
        llm_max=args.llm_max,
        baseline_dir=Path(args.baseline_results) if args.baseline_results else None,
        bootstrap_samples=args.bootstrap_samples,
        bootstrap_seed=args.bootstrap_seed,
        ci_level=args.ci_level,
        human_scope=args.human_scope,
        human_sample_size=args.human_sample_size,
        human_sample_out=Path(args.human_sample_out) if args.human_sample_out else None,
        human_labels=Path(args.human_labels) if args.human_labels else None,
        human_labels_report=Path(args.human_labels_report) if args.human_labels_report else None,
        metadata_path=Path(args.metadata) if args.metadata else None,
        audit_classifications=audit_classifications,
        client_filter=client_filter,
        client_keywords=client_keywords,
        reparse=args.reparse,
    )


if __name__ == "__main__":
    main()
