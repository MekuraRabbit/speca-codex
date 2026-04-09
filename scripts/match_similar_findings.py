"""Match Phase 03 findings against filtered similar audit findings using Claude LLM.

Two-pass approach:
  Pass 1: Keyword pre-filter to narrow CSV findings to those most relevant to each Phase 03 finding
  Pass 2: LLM comparison in batches of 10
"""

import csv
import json
import glob
import os
import re
import subprocess
import sys
import tempfile

# Force UTF-8 output on Windows and unbuffered
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def fprint(*args, **kwargs):
    """Print with flush."""
    print(*args, **kwargs, flush=True)

csv.field_size_limit(sys.maxsize)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
FILTERED_CSV = os.path.join(OUTPUT_DIR, "similar_audit_findings.csv")
MATCH_OUTPUT = os.path.join(OUTPUT_DIR, "similar_audit_matches.json")
CLAUDE_EXE = r"C:\Users\shieru_k\AppData\Roaming\npm\claude.cmd"

BATCH_SIZE = 10


def load_filtered_findings():
    """Load the filtered CSV findings."""
    findings = []
    with open(FILTERED_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            findings.append(row)
    return findings


def load_phase03_findings():
    """Load Phase 03 findings that are not classified as safe."""
    pattern = os.path.join(OUTPUT_DIR, "03_PARTIAL_*.json")
    files = sorted(glob.glob(pattern))
    findings = []
    for fpath in files:
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        for item in data.get("audit_items", []):
            classification = item.get("classification", "").lower()
            verdict = item.get("verdict", "")
            include = False
            # Check verdict field if present
            if verdict and verdict.upper() != "SAFE":
                include = True
            # Check classification - exclude "not-a-vulnerability" explicitly
            if classification == "not-a-vulnerability":
                pass  # skip safe items
            elif "finding" in classification or "vulnerability" in classification or "potential" in classification:
                include = True
            if include:
                findings.append(item)
    return findings


def keyword_prefilter(phase03_finding, csv_findings):
    """Pre-filter CSV findings by keywords extracted from the Phase 03 finding.

    Uses a scoring approach: findings must match at least 2 keyword categories
    to be included, ensuring tight relevance.
    """
    finding_text = " ".join([
        phase03_finding.get("proof_trace", ""),
        phase03_finding.get("attack_scenario", ""),
        phase03_finding.get("code_path", ""),
        phase03_finding.get("property_id", ""),
    ]).lower()

    # Define keyword categories with weights
    categories = []
    if "approv" in finding_text or "allowance" in finding_text:
        categories.append(("approval", ["approv", "allowance"]))
    if "multicall" in finding_text or "callback" in finding_text:
        categories.append(("multicall", ["multicall", "callback", "delegatecall", "arbitrary call"]))
    if "auction" in finding_text or "bid" in finding_text:
        categories.append(("auction", ["auction", " bid"]))  # space before bid to avoid false matches
    if "drain" in finding_text or "transferfrom" in finding_text or "steal" in finding_text:
        categories.append(("drain", ["drain", "transferfrom", "steal", "siphon", "fund"]))
    if "persist" in finding_text or "residual" in finding_text or "stale" in finding_text:
        categories.append(("stale", ["persist", "residual", "stale", "leftover", "linger"]))

    if not categories:
        categories.append(("generic", ["approv", "allowance", "multicall", "callback"]))

    # Score each CSV finding: must match at least 2 categories (or 1 if few categories)
    min_matches = min(2, len(categories))
    relevant = []
    for row in csv_findings:
        text = (row.get("title", "") + " " + row.get("description", "")[:1000]).lower()
        score = sum(1 for _, kws in categories if any(kw in text for kw in kws))
        if score >= min_matches:
            relevant.append(row)

    return relevant


def truncate_description(desc, max_len=500):
    """Truncate description to keep prompts manageable."""
    if len(desc) <= max_len:
        return desc
    return desc[:max_len] + "..."


def build_prompt(phase03_finding, csv_batch, batch_idx):
    """Build a prompt for Claude to compare a Phase 03 finding against a batch of CSV findings."""
    finding_summary = (
        f"Property: {phase03_finding.get('property_id', 'N/A')}\n"
        f"Classification: {phase03_finding.get('classification', 'N/A')}\n"
        f"Code Path: {phase03_finding.get('code_path', 'N/A')}\n"
        f"Proof: {phase03_finding.get('proof_trace', 'N/A')}\n"
        f"Attack Scenario: {phase03_finding.get('attack_scenario', 'N/A')}"
    )

    csv_summaries = []
    for i, row in enumerate(csv_batch):
        desc = truncate_description(row.get("description", ""), 400)
        csv_summaries.append(
            f"[{i+1}] Source: {row['source']} | Contest: {row['contest']} | "
            f"ID: {row['issue_id']} | Severity: {row['severity']}\n"
            f"Title: {row['title']}\n"
            f"Description: {desc}"
        )

    csv_block = "\n\n".join(csv_summaries)

    prompt = f"""You are a smart contract security expert. Compare the following audit finding from the Chainlink V2 Phase 03 audit against historical audit findings from public contests.

## TARGET FINDING (Chainlink V2 Phase 03):
{finding_summary}

## HISTORICAL FINDINGS (Batch {batch_idx+1}):
{csv_block}

## TASK:
For each historical finding, determine if it is RELEVANT to the target finding. A finding is relevant if:
1. It describes a similar vulnerability pattern (e.g., stale approvals, callback abuse, multicall risks)
2. It targets a similar mechanism (e.g., auction bidding, token approvals, access control)
3. The attack vector or root cause is analogous

Return a JSON array of matches. Each match should have:
- "csv_index": the number [1-{len(csv_batch)}] of the historical finding
- "relevance": "high", "medium", or "low"
- "reason": brief explanation of why it's relevant

If no findings are relevant, return an empty array: []

Return ONLY the JSON array, no other text."""

    return prompt


def call_claude(prompt):
    """Call Claude CLI with the given prompt via stdin."""
    try:
        result = subprocess.run(
            [CLAUDE_EXE, "--output-format", "json", "--model", "claude-sonnet-4-20250514", "-p"],
            input=prompt.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
        )
        stdout_text = result.stdout.decode("utf-8", errors="replace")
        stderr_text = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""

        if result.returncode != 0:
            fprint(f"  Claude error (rc={result.returncode}): {stderr_text[:300]}")
            return None

        # Parse the JSON output from Claude CLI
        try:
            output = json.loads(stdout_text)
            text = output.get("result", "") if isinstance(output, dict) else stdout_text
        except json.JSONDecodeError:
            text = stdout_text

        # Extract JSON array from the response text
        if isinstance(text, str):
            start = text.find("[")
            end = text.rfind("]")
            if start != -1 and end != -1:
                try:
                    return json.loads(text[start : end + 1])
                except json.JSONDecodeError:
                    pass
        return []
    except subprocess.TimeoutExpired:
        fprint("  Claude call timed out")
        return None


def main():
    fprint("Loading filtered CSV findings...")
    csv_findings = load_filtered_findings()
    fprint(f"  Loaded {len(csv_findings)} filtered findings")

    fprint("Loading Phase 03 findings...")
    phase03_findings = load_phase03_findings()
    fprint(f"  Found {len(phase03_findings)} non-safe Phase 03 findings")

    if not phase03_findings:
        fprint("No non-safe Phase 03 findings to match against. Exiting.")
        with open(MATCH_OUTPUT, "w", encoding="utf-8") as f:
            json.dump({"matches": [], "summary": "No non-safe findings in Phase 03"}, f, indent=2)
        fprint(f"Wrote empty results to {MATCH_OUTPUT}")
        return

    if not csv_findings:
        fprint("No filtered CSV findings to compare against. Exiting.")
        return

    all_matches = []

    for fi, finding in enumerate(phase03_findings):
        prop_id = finding.get("property_id", "N/A")
        fprint(f"\nProcessing Phase 03 finding {fi+1}/{len(phase03_findings)}: {prop_id}")

        # Pass 1: keyword pre-filter
        relevant_csv = keyword_prefilter(finding, csv_findings)
        fprint(f"  Keyword pre-filter: {len(relevant_csv)} of {len(csv_findings)} findings relevant")

        if not relevant_csv:
            fprint("  No keyword-relevant findings, skipping LLM matching.")
            all_matches.append({
                "phase03_property_id": prop_id,
                "phase03_classification": finding.get("classification", ""),
                "phase03_code_path": finding.get("code_path", ""),
                "phase03_attack_scenario": finding.get("attack_scenario", ""),
                "matches": [],
                "total_matches": 0,
            })
            continue

        finding_matches = []

        # Pass 2: LLM comparison in batches
        num_batches = (len(relevant_csv) + BATCH_SIZE - 1) // BATCH_SIZE
        for batch_idx in range(num_batches):
            start = batch_idx * BATCH_SIZE
            end = min(start + BATCH_SIZE, len(relevant_csv))
            batch = relevant_csv[start:end]

            fprint(f"  Batch {batch_idx+1}/{num_batches} (findings {start+1}-{end})...")

            prompt = build_prompt(finding, batch, batch_idx)
            matches = call_claude(prompt)

            if matches:
                for m in matches:
                    csv_idx = m.get("csv_index", 0) - 1 + start
                    if 0 <= csv_idx < len(relevant_csv):
                        row = relevant_csv[csv_idx]
                        finding_matches.append({
                            "csv_source": row["source"],
                            "csv_contest": row["contest"],
                            "csv_issue_id": row["issue_id"],
                            "csv_title": row["title"],
                            "csv_severity": row["severity"],
                            "relevance": m.get("relevance", "unknown"),
                            "reason": m.get("reason", ""),
                        })

        all_matches.append({
            "phase03_property_id": finding.get("property_id", ""),
            "phase03_classification": finding.get("classification", ""),
            "phase03_code_path": finding.get("code_path", ""),
            "phase03_attack_scenario": finding.get("attack_scenario", ""),
            "matches": finding_matches,
            "total_matches": len(finding_matches),
        })

    # Summary
    total = sum(m["total_matches"] for m in all_matches)
    high_rel = sum(
        1 for m in all_matches for match in m["matches"]
        if match.get("relevance") == "high"
    )
    med_rel = sum(
        1 for m in all_matches for match in m["matches"]
        if match.get("relevance") == "medium"
    )

    result = {
        "summary": {
            "phase03_findings_processed": len(phase03_findings),
            "total_csv_findings_compared": len(csv_findings),
            "total_matches_found": total,
            "high_relevance": high_rel,
            "medium_relevance": med_rel,
        },
        "matches": all_matches,
    }

    with open(MATCH_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    fprint(f"\n{'='*60}")
    fprint("RESULTS SUMMARY")
    fprint(f"{'='*60}")
    fprint(f"Phase 03 findings processed: {len(phase03_findings)}")
    fprint(f"CSV findings compared: {len(csv_findings)}")
    fprint(f"Total matches found: {total}")
    fprint(f"  High relevance: {high_rel}")
    fprint(f"  Medium relevance: {med_rel}")
    fprint(f"\nResults written to {MATCH_OUTPUT}")


if __name__ == "__main__":
    main()
