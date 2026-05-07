#!/usr/bin/env python3
"""Build Phase 05 representative PoC candidates from Phase 04 partials."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))

from orchestrator.phase05_candidates import write_poc_candidate_index


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build outputs/05_POC_CANDIDATES.json from Phase 03/04 partials.",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs",
        help="SPECA output directory containing TARGET_INFO.json and 03/04 partials.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional explicit output JSON path. Defaults to <output-dir>/05_POC_CANDIDATES.json.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_path = Path(args.output) if args.output else None
    index = write_poc_candidate_index(output_dir, output_path)

    metadata = index["metadata"]
    print(
        json.dumps(
            {
                "output": (output_path or (output_dir / "05_POC_CANDIDATES.json")).as_posix(),
                "reviewed_candidate_items": metadata["reviewed_candidate_items"],
                "candidate_count": metadata["candidate_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
