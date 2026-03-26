"""Filter audit CSV findings that are relevant to the Chainlink V2 Phase 03 audit."""

import csv
import os
import re
import sys

csv.field_size_limit(sys.maxsize)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "benchmarks", "data", "defi_audit_reports")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "similar_audit_findings.csv")

EXACT_CONTEST_PATTERNS = re.compile(
    r"reserve|backed|escher|credit-guild|ethereum-credit-guild", re.IGNORECASE
)


def matches_patterns(title: str, description: str) -> bool:
    """Check if title+description matches any of the defined patterns."""
    text = (title + " " + description).lower()

    # "dutch" AND "auction"
    if "dutch" in text and "auction" in text:
        return True

    # "cowswap" OR "gpv2" OR "cow protocol"
    if "cowswap" in text or "gpv2" in text or "cow protocol" in text:
        return True

    # "multicall" OR ("callback" AND ("arbitrary" OR "unrestricted"))
    if "multicall" in text:
        return True
    if "callback" in text and ("arbitrary" in text or "unrestricted" in text):
        return True

    # "oracle" AND ("staleness" OR "stale" OR "revert")
    if "oracle" in text and ("staleness" in text or "stale" in text or "revert" in text):
        return True

    # "approval" AND ("stale" OR "residual" OR "migration" OR "revoke")
    if "approval" in text and (
        "stale" in text
        or "residual" in text
        or "migration" in text
        or "revoke" in text
    ):
        return True

    # "fee" AND ("aggregat" OR "conversion" OR "swap") AND "auction"
    if "fee" in text and "auction" in text:
        if "aggregat" in text or "conversion" in text or "swap" in text:
            return True

    return False


def matches_contest(contest: str) -> bool:
    """Check if contest name matches exact contest patterns."""
    return bool(EXACT_CONTEST_PATTERNS.search(contest))


def load_code4rena():
    path = os.path.join(DATA_DIR, "code4rena_all_issues.csv")
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sev = row.get("severity", "")
            if sev not in ("High", "Medium"):
                continue
            title = row.get("title", "")
            desc = row.get("description", "")
            contest = row.get("contest_repo", "") or row.get("contest_name", "")
            issue_id = row.get("issue_id", "")
            if matches_patterns(title, desc) or matches_contest(contest):
                rows.append({
                    "source": "code4rena",
                    "contest": contest,
                    "issue_id": issue_id,
                    "severity": sev,
                    "title": title,
                    "description": desc,
                })
    return rows


def load_sherlock():
    path = os.path.join(DATA_DIR, "sherlock_all_issues.csv")
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sev = row.get("severity", "")
            if sev not in ("High", "Medium"):
                continue
            title = row.get("title", "")
            desc = row.get("description", "")
            contest = row.get("contest_title", "")
            issue_id = row.get("issue_id", "")
            if matches_patterns(title, desc) or matches_contest(contest):
                rows.append({
                    "source": "sherlock",
                    "contest": contest,
                    "issue_id": issue_id,
                    "severity": sev,
                    "title": title,
                    "description": desc,
                })
    return rows


def load_codehawks():
    path = os.path.join(DATA_DIR, "codehawks_all_issues.csv")
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sev = row.get("severity", "")
            if sev not in ("High", "Medium"):
                continue
            title = row.get("title", "")
            desc = row.get("description", "")
            contest = row.get("contest_name", "")
            issue_id = row.get("finding_id", "")
            if matches_patterns(title, desc) or matches_contest(contest):
                rows.append({
                    "source": "codehawks",
                    "contest": contest,
                    "issue_id": issue_id,
                    "severity": sev,
                    "title": title,
                    "description": desc,
                })
    return rows


def deduplicate(rows):
    """Deduplicate by exact title match."""
    seen = set()
    deduped = []
    for row in rows:
        t = row["title"].strip()
        if t not in seen:
            seen.add(t)
            deduped.append(row)
    return deduped


def main():
    print("Loading Code4rena...")
    c4 = load_code4rena()
    print(f"  Code4rena: {len(c4)} matching issues")

    print("Loading Sherlock...")
    sh = load_sherlock()
    print(f"  Sherlock: {len(sh)} matching issues")

    print("Loading Codehawks...")
    ch = load_codehawks()
    print(f"  Codehawks: {len(ch)} matching issues")

    all_rows = c4 + sh + ch
    print(f"\nTotal before dedup: {len(all_rows)}")

    deduped = deduplicate(all_rows)
    print(f"Total after dedup: {len(deduped)}")

    # Stats
    by_source = {}
    by_severity = {}
    for r in deduped:
        by_source[r["source"]] = by_source.get(r["source"], 0) + 1
        by_severity[r["severity"]] = by_severity.get(r["severity"], 0) + 1

    print("\nBy source:")
    for k, v in sorted(by_source.items()):
        print(f"  {k}: {v}")
    print("By severity:")
    for k, v in sorted(by_severity.items()):
        print(f"  {k}: {v}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    fieldnames = ["source", "contest", "issue_id", "severity", "title", "description"]
    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(deduped)

    print(f"\nWrote {len(deduped)} findings to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
