#!/usr/bin/env python3
"""Convert DeFi audit CSV files to RQ1 matcher format.

Renames columns to match the expected schema:
  severity -> submitted_severity
  issue_id / finding_id -> number
"""

import csv
import sys
from pathlib import Path

csv.field_size_limit(sys.maxsize)

DATA_DIR = Path(__file__).resolve().parents[1] / "benchmarks" / "data" / "defi_audit_reports"

# (source file, id column name)
SOURCES = [
    ("sherlock_all_issues.csv", "issue_id"),
    ("code4rena_all_issues.csv", "issue_id"),
    ("codehawks_all_issues.csv", "finding_id"),
]


def convert(src_path: Path, id_col: str) -> Path:
    dst_path = src_path.with_name(src_path.stem + "_rq1.csv")

    with src_path.open("r", encoding="utf-8", newline="") as fin:
        reader = csv.DictReader(fin)
        fieldnames = []
        for col in reader.fieldnames:
            if col == "severity":
                fieldnames.append("submitted_severity")
            elif col == id_col:
                fieldnames.append("number")
            else:
                fieldnames.append(col)

        with dst_path.open("w", encoding="utf-8", newline="") as fout:
            writer = csv.DictWriter(fout, fieldnames=fieldnames)
            writer.writeheader()
            for row in reader:
                new_row = {}
                for old_key, value in row.items():
                    if old_key == "severity":
                        new_row["submitted_severity"] = value
                    elif old_key == id_col:
                        new_row["number"] = value
                    else:
                        new_row[old_key] = value
                writer.writerow(new_row)

    print(f"  {src_path.name} -> {dst_path.name}")
    return dst_path


def main():
    print("Converting DeFi CSVs to RQ1 format...")
    for filename, id_col in SOURCES:
        src = DATA_DIR / filename
        if not src.exists():
            print(f"  SKIP: {filename} not found")
            continue
        convert(src, id_col)
    print("Done.")


if __name__ == "__main__":
    main()
