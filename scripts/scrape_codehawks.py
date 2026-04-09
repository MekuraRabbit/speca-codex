#!/usr/bin/env python3
"""
Scrape CodeHawks contest findings into a CSV via tRPC API.

Strategy:
1. Fetch contest list from codehawks.cyfrin.io/contests (embedded SvelteKit JSON)
2. For each finalized contest, call the tRPC findings API
3. Extract high/medium findings with title, description, severity
4. Output to CSV

Usage:
    python3 scripts/scrape_codehawks.py [--output PATH] [--severity high,medium] [--max-contests N]
"""

import argparse
import csv
import json
import re
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path


def curl_json(url: str, retries: int = 3):
    for attempt in range(retries):
        try:
            result = subprocess.run(
                ["curl", "-s", "-L", "--max-time", "30", url],
                capture_output=True, timeout=35,
                encoding="utf-8", errors="replace"
            )
            if result.returncode == 0 and result.stdout.strip():
                return json.loads(result.stdout)
        except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
            print(f"  [warn] attempt {attempt+1} failed: {e}", file=sys.stderr)
            time.sleep(2 ** attempt)
    return None


def curl_text(url: str, retries: int = 3) -> str | None:
    for attempt in range(retries):
        try:
            result = subprocess.run(
                ["curl", "-s", "-L", "--max-time", "30", url],
                capture_output=True, timeout=35,
                encoding="utf-8", errors="replace"
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout
        except subprocess.TimeoutExpired:
            time.sleep(2 ** attempt)
    return None


def fetch_contests() -> list[dict]:
    """Fetch all finalized CodeHawks contests from the contests page."""
    html = curl_text("https://codehawks.cyfrin.io/contests")
    if not html:
        return []

    contests = []
    matches = re.findall(r'data-sveltekit-fetched[^>]*>([^<]+)</script>', html)
    for m in matches:
        try:
            wrapper = json.loads(m)
            body = wrapper.get("body")
            if isinstance(body, str):
                data = json.loads(body)
            else:
                data = body
            if isinstance(data, list):
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    result = item.get("result", {})
                    entries = result.get("data", [])
                    if isinstance(entries, list):
                        for c in entries:
                            if isinstance(c, dict) and c.get("finalised"):
                                contests.append(c)
        except (json.JSONDecodeError, TypeError):
            pass

    return contests


def fetch_findings(competition_id: str) -> dict | None:
    """Fetch findings for a contest via tRPC API."""
    input_data = json.dumps({"0": {"competitionId": competition_id}})
    encoded = urllib.parse.quote(input_data)
    url = f"https://codehawks.cyfrin.io/trpc/findings.getFindingOverviewsForCompetition?batch=1&input={encoded}"
    data = curl_json(url)
    if data and isinstance(data, list) and len(data) > 0:
        return data[0].get("result", {}).get("data")
    return None


def main():
    parser = argparse.ArgumentParser(description="Scrape CodeHawks findings to CSV")
    parser.add_argument("--output", default="benchmarks/data/defi_audit_reports/codehawks_all_issues.csv")
    parser.add_argument("--severity", default="high,medium")
    parser.add_argument("--max-contests", type=int, default=0)
    args = parser.parse_args()

    allowed = {s.strip().lower() for s in args.severity.split(",")}

    print("Step 1: Fetching contest list...", file=sys.stderr)
    contests = fetch_contests()
    print(f"  Found {len(contests)} finalized contests", file=sys.stderr)

    if args.max_contests > 0:
        contests = contests[:args.max_contests]

    all_issues = []

    print("\nStep 2: Fetching findings via tRPC...", file=sys.stderr)
    for idx, contest in enumerate(contests):
        cid = contest.get("id", "")
        slug = contest.get("urlSlug", "")
        name = contest.get("name", "")
        company = contest.get("company", "")
        reward = contest.get("reward", 0)
        contest_name = f"{company} - {name}" if company else name

        print(f"  [{idx+1}/{len(contests)}] {slug}...",
              file=sys.stderr, end="", flush=True)

        findings_data = fetch_findings(cid)
        if not findings_data:
            print(" [no data]", file=sys.stderr)
            time.sleep(0.3)
            continue

        count = 0
        # Process highs and mediums (and lows if requested)
        severity_buckets = {
            "high": findings_data.get("highs", []),
            "medium": findings_data.get("mediums", []),
            "low": findings_data.get("lows", []),
        }

        for sev, bucket in severity_buckets.items():
            if sev not in allowed:
                continue
            for finding_group in bucket:
                # Each finding_group has multiple 'issues' (duplicate submissions)
                # We take the selected/primary issue
                selected_id = finding_group.get("selectedIssueId")
                issues = finding_group.get("issues", [])
                finding_id = finding_group.get("id", "")

                # Find the selected issue, or use the first one
                primary = None
                for iss in issues:
                    if iss.get("id") == selected_id:
                        primary = iss
                        break
                if not primary and issues:
                    primary = issues[0]

                if not primary:
                    continue

                all_issues.append({
                    "contest_slug": slug,
                    "contest_name": contest_name,
                    "contest_reward": reward,
                    "finding_id": finding_id,
                    "severity": sev.capitalize(),
                    "title": primary.get("title", ""),
                    "description": (primary.get("description", "") or primary.get("content", ""))[:15000],
                    "source_url": f"https://codehawks.cyfrin.io/c/{slug}/results?lt=contest&sc=reward&sj=reward&page=1&t=report&cn={finding_id}",
                    "submitter": (primary.get("User", {}) or {}).get("username", ""),
                    "num_duplicates": len(issues),
                })
                count += 1

        print(f" {count} issues", file=sys.stderr)
        time.sleep(0.3)

    # Write CSV
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "contest_slug", "contest_name", "contest_reward", "finding_id",
        "severity", "title", "description", "source_url", "submitter", "num_duplicates"
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(all_issues)

    high_count = sum(1 for i in all_issues if i["severity"] == "High")
    med_count = sum(1 for i in all_issues if i["severity"] == "Medium")
    unique_contests = len(set(i["contest_slug"] for i in all_issues))
    print(f"\nDone! Wrote {len(all_issues)} issues to {output_path}", file=sys.stderr)
    print(f"  High: {high_count}, Medium: {med_count}", file=sys.stderr)
    print(f"  From {unique_contests} contests", file=sys.stderr)


if __name__ == "__main__":
    main()
