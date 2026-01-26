#!/usr/bin/env python3
"""
Check if a worker's queue has remaining items to process.

Usage:
    python3 scripts/has_remaining.py outputs/01b_QUEUE_0.json

Exit codes:
    0 - Has remaining items (continue processing)
    1 - No remaining items (stop processing)
"""

import json
import sys
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print("Usage: has_remaining.py <queue_file>", file=sys.stderr)
        sys.exit(1)

    queue_file = sys.argv[1]

    try:
        with open(queue_file) as f:
            data = json.load(f)
    except FileNotFoundError:
        # No queue file means nothing to process
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {queue_file}", file=sys.stderr)
        sys.exit(1)

    items = data.get("items", [])
    processed = data.get("processed", [])

    # Calculate remaining
    remaining = len(items) - len(processed)

    if remaining > 0:
        print(f"{remaining} items remaining")
        sys.exit(0)  # Has remaining items
    else:
        print("Queue complete")
        sys.exit(1)  # No remaining items


if __name__ == "__main__":
    main()
