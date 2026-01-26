#!/usr/bin/env python3
"""
Orchestrate parallel execution of multiple workers.

This script splits the queue, runs workers in parallel, and merges results.

Usage:
    python3 scripts/run_parallel.py --phase 01b --workers 4
    python3 scripts/run_parallel.py --phase 02b --workers 4 --max-iterations 50
"""

import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def run_split(phase: str, workers: int) -> bool:
    """Run the split_queue.py script."""
    print(f"\n{'='*60}")
    print(f"Phase 1: Splitting queue for {workers} workers")
    print(f"{'='*60}")

    result = subprocess.run(
        ["python3", "scripts/split_queue.py", "--phase", phase, "--workers", str(workers)],
        capture_output=True,
        text=True,
    )

    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        return False

    return True


def run_worker(phase: str, worker_id: int, max_iterations: int) -> tuple[int, bool, str]:
    """Run a single worker and return (worker_id, success, output)."""
    print(f"Starting worker {worker_id}...")

    result = subprocess.run(
        [
            "python3", "scripts/run_worker.py",
            "--phase", phase,
            "--worker-id", str(worker_id),
            "--max-iterations", str(max_iterations),
        ],
        capture_output=True,
        text=True,
    )

    output = result.stdout + result.stderr
    return worker_id, result.returncode == 0, output


def run_workers_parallel(phase: str, workers: int, max_iterations: int) -> bool:
    """Run all workers in parallel."""
    print(f"\n{'='*60}")
    print(f"Phase 2: Running {workers} workers in parallel")
    print(f"{'='*60}")

    start_time = time.time()

    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(run_worker, phase, i, max_iterations): i
            for i in range(workers)
        }

        results = {}
        for future in concurrent.futures.as_completed(futures):
            worker_id = futures[future]
            try:
                wid, success, output = future.result()
                results[wid] = (success, output)
                status = "OK" if success else "FAILED"
                print(f"Worker {wid}: {status}")
            except Exception as e:
                results[worker_id] = (False, str(e))
                print(f"Worker {worker_id}: EXCEPTION - {e}")

    duration = time.time() - start_time
    print(f"\nAll workers completed in {duration:.1f}s")

    # Print worker outputs
    for wid in sorted(results.keys()):
        success, output = results[wid]
        print(f"\n--- Worker {wid} output ---")
        print(output[:2000])  # Truncate long outputs
        if len(output) > 2000:
            print("... (truncated)")

    # Check if all succeeded
    all_success = all(success for success, _ in results.values())
    return all_success


def run_merge(phase: str, output_file: str) -> bool:
    """Run the merge_results.py script."""
    print(f"\n{'='*60}")
    print(f"Phase 3: Merging results")
    print(f"{'='*60}")

    result = subprocess.run(
        ["python3", "scripts/merge_results.py", "--phase", phase, "--output", output_file],
        capture_output=True,
        text=True,
    )

    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        return False

    return True


# Output file mapping
OUTPUT_FILES = {
    "01b": "outputs/01_SPEC.json",
    "02b": "outputs/02b_CHECKLIST_MERGED.json",
    "03": "outputs/03_AUDITMAP_MERGED.json",
    "04": "outputs/04_REVIEW_MERGED.json",
}


def main():
    parser = argparse.ArgumentParser(
        description="Orchestrate parallel execution of workers"
    )
    parser.add_argument(
        "--phase",
        required=True,
        choices=["01b", "02b", "03", "04"],
        help="Phase to run",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of parallel workers (default: 4)",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=100,
        help="Max iterations per worker (default: 100)",
    )
    parser.add_argument(
        "--skip-split",
        action="store_true",
        help="Skip queue splitting (use existing queue files)",
    )
    parser.add_argument(
        "--skip-merge",
        action="store_true",
        help="Skip result merging",
    )
    parser.add_argument(
        "--output",
        help="Override output file for merge",
    )
    args = parser.parse_args()

    print(f"Parallel execution for phase {args.phase}")
    print(f"  Workers: {args.workers}")
    print(f"  Max iterations per worker: {args.max_iterations}")

    start_time = time.time()

    # Step 1: Split queue
    if not args.skip_split:
        if not run_split(args.phase, args.workers):
            print("ERROR: Queue splitting failed", file=sys.stderr)
            sys.exit(1)
    else:
        print("\nSkipping queue split (--skip-split)")

    # Step 2: Run workers in parallel
    if not run_workers_parallel(args.phase, args.workers, args.max_iterations):
        print("WARNING: Some workers failed", file=sys.stderr)
        # Continue to merge anyway

    # Step 3: Merge results
    if not args.skip_merge:
        output_file = args.output or OUTPUT_FILES[args.phase]
        if not run_merge(args.phase, output_file):
            print("ERROR: Result merging failed", file=sys.stderr)
            sys.exit(1)
    else:
        print("\nSkipping merge (--skip-merge)")

    total_time = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"Parallel execution complete in {total_time:.1f}s")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
