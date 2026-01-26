#!/usr/bin/env python3
"""
Split a work queue into multiple worker-specific queues for parallel processing.

Usage:
    python3 scripts/split_queue.py --phase 01b --workers 4
    python3 scripts/split_queue.py --phase 02b --workers 4
    python3 scripts/split_queue.py --phase 03 --workers 4
    python3 scripts/split_queue.py --phase 04 --workers 4
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


# Phase configuration: maps phase to state file location and queue key
PHASE_CONFIG = {
    "01b": {
        "state_file": "outputs/01a_STATE.json",
        "queue_key": "work_queue",
        "output_prefix": "outputs/01b_QUEUE",
    },
    "02b": {
        "state_file": "outputs/02b_STATE.json",
        "queue_key": "unprocessed_property_ids",
        "output_prefix": "outputs/02b_QUEUE",
        # For 02b, we need to initialize from 01e_PROP.json and 02a on first run
        "init_from": {
            "all_items": "outputs/01e_PROP.json",
            "all_items_key": "properties",
            "all_items_id_key": "id",
            "exclude": "outputs/02a_CHECKLIST_BOUNDARIES.json",
            "exclude_key": "checklist",
            "exclude_id_key": "property_id",
        },
    },
    "03": {
        "state_file": "outputs/03_STATE.json",
        "queue_key": "unprocessed_checklist_ids",
        "output_prefix": "outputs/03_QUEUE",
        # For 03, we need to initialize from 02a and 02b files
        "init_from_glob": {
            "pattern": "outputs/02*.json",
            "exclude_patterns": ["02s_", "02b_STATE"],
            "item_key": "checklist",
            "id_key": "id",
        },
    },
    "04": {
        "state_file": "outputs/04_STATE.json",
        "queue_key": "unprocessed_audit_items",
        "output_prefix": "outputs/04_QUEUE",
        # For 04, we need to initialize from 03_AUDITMAP files
        "init_from_glob": {
            "pattern": "outputs/03_AUDITMAP_PARTIAL_*.json",
            "item_key": "audit_items",
            "id_key": "check_id",
        },
    },
}


def load_json(path: str) -> dict[str, Any]:
    """Load JSON file, return empty dict if not exists."""
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
        print(f"Error parsing {path}: {e}", file=sys.stderr)
        return {}


def save_json(path: str, data: dict[str, Any]) -> None:
    """Save data to JSON file."""
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Written: {path}")


def get_items_from_state(config: dict[str, Any]) -> list[str]:
    """Get the list of items to process from state file."""
    state_file = config["state_file"]
    queue_key = config["queue_key"]

    state = load_json(state_file)
    if state and queue_key in state:
        return state[queue_key]

    # State file doesn't exist or is empty - need to initialize
    if "init_from" in config:
        return init_from_files(config["init_from"])
    elif "init_from_glob" in config:
        return init_from_glob(config["init_from_glob"])

    return []


def init_from_files(init_config: dict[str, Any]) -> list[str]:
    """Initialize queue from source files (for 02b)."""
    # Get all items
    all_data = load_json(init_config["all_items"])
    all_items = all_data.get(init_config["all_items_key"], [])
    all_ids = [item[init_config["all_items_id_key"]] for item in all_items]

    # Get items to exclude
    exclude_data = load_json(init_config["exclude"])
    exclude_items = exclude_data.get(init_config["exclude_key"], [])
    exclude_ids = set(item[init_config["exclude_id_key"]] for item in exclude_items)

    # Return difference
    return [id for id in all_ids if id not in exclude_ids]


def init_from_glob(init_config: dict[str, Any]) -> list[str]:
    """Initialize queue from glob pattern (for 03, 04)."""
    import glob

    pattern = init_config["pattern"]
    item_key = init_config["item_key"]
    id_key = init_config["id_key"]
    exclude_patterns = init_config.get("exclude_patterns", [])

    all_ids = []
    for filepath in glob.glob(pattern):
        # Check exclusion patterns
        skip = False
        for exc in exclude_patterns:
            if exc in filepath:
                skip = True
                break
        if skip:
            continue

        data = load_json(filepath)
        items = data.get(item_key, [])
        for item in items:
            if isinstance(item, dict) and id_key in item:
                all_ids.append(item[id_key])
            elif isinstance(item, str):
                all_ids.append(item)

    return all_ids


def split_queue(items: list[str], workers: int) -> list[list[str]]:
    """Split items into worker queues using round-robin distribution."""
    queues: list[list[str]] = [[] for _ in range(workers)]

    for i, item in enumerate(items):
        queues[i % workers].append(item)

    return queues


def main():
    parser = argparse.ArgumentParser(
        description="Split work queue into worker-specific queues for parallel processing"
    )
    parser.add_argument(
        "--phase",
        required=True,
        choices=list(PHASE_CONFIG.keys()),
        help="Phase to split (01b, 02b, 03, 04)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of workers (default: 4)",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Output directory (default: outputs)",
    )
    args = parser.parse_args()

    config = PHASE_CONFIG[args.phase]

    print(f"Splitting queue for phase {args.phase} into {args.workers} workers...")

    # Get items to process
    items = get_items_from_state(config)

    if not items:
        print(f"No items to process for phase {args.phase}")
        sys.exit(0)

    print(f"  Total items: {len(items)}")

    # Split into worker queues
    queues = split_queue(items, args.workers)

    # Write worker queue files
    output_prefix = config["output_prefix"]
    for worker_id, queue in enumerate(queues):
        output_path = f"{output_prefix}_{worker_id}.json"
        queue_data = {
            "worker_id": worker_id,
            "phase": args.phase,
            "total_workers": args.workers,
            "items": queue,
            "processed": [],
            "total_items": len(queue),
        }
        save_json(output_path, queue_data)
        print(f"  Worker {worker_id}: {len(queue)} items")

    # Write metadata file for tracking
    metadata_path = f"{output_prefix}_METADATA.json"
    metadata = {
        "phase": args.phase,
        "total_workers": args.workers,
        "total_items": len(items),
        "items_per_worker": [len(q) for q in queues],
        "queue_files": [f"{output_prefix}_{i}.json" for i in range(args.workers)],
    }
    save_json(metadata_path, metadata)

    print(f"Split complete. Run workers with: make {args.phase}-parallel")


if __name__ == "__main__":
    main()
