"""Search past audit CSVs for findings similar to M-02, M-07, M-14 patterns.
Then use LLM to analyze top matches and extract new vulnerability patterns for Chainlink V2.

Usage:
    python scripts/find_precedents_and_bugs.py
"""

import csv
import json
import os
import re
import subprocess
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

csv.field_size_limit(sys.maxsize)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "benchmarks", "data", "defi_audit_reports")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
CLAUDE_EXE = r"C:\Users\shieru_k\AppData\Roaming\npm\claude.cmd"

# Define search patterns for each finding
FINDING_PATTERNS = {
    "M-02_shared_staleness": {
        "description": "Single staleness threshold shared between multiple oracle sources (Data Streams + Chainlink feed fallback). Tight threshold kills fallback, loose threshold accepts stale primary.",
        "keywords": [
            # Must match at least 2 of these groups
            {"group": "oracle", "terms": ["oracle", "chainlink", "price feed", "data feed", "aggregator"]},
            {"group": "staleness", "terms": ["stale", "staleness", "threshold", "freshness", "heartbeat", "timeout"]},
            {"group": "fallback", "terms": ["fallback", "backup", "secondary", "dual", "redundan"]},
            {"group": "config", "terms": ["config", "parameter", "shared", "single", "same threshold"]},
        ],
        "min_groups": 2,
    },
    "M-07_future_timestamp": {
        "description": "transmit() accepts future-dated price reports, extending effective staleness window. No upper bound check on observationsTimestamp.",
        "keywords": [
            {"group": "oracle", "terms": ["oracle", "price", "feed", "chainlink", "report"]},
            {"group": "timestamp", "terms": ["timestamp", "future", "clock", "time", "block.timestamp"]},
            {"group": "staleness", "terms": ["stale", "staleness", "validity", "expir", "window"]},
            {"group": "manipulation", "terms": ["manipulat", "bypass", "extend", "defeat", "circumvent"]},
        ],
        "min_groups": 2,
    },
    "M-14_stale_approval": {
        "description": "Migration/upgrade does not revoke residual ERC20 approvals to old contract. Stale allowance persists after state transition.",
        "keywords": [
            {"group": "approval", "terms": ["approv", "allowance", "permit"]},
            {"group": "stale", "terms": ["stale", "residual", "leftover", "persist", "linger", "remain"]},
            {"group": "migration", "terms": ["migrat", "upgrad", "set", "transition", "swap", "replac", "old"]},
            {"group": "revoke", "terms": ["revok", "reset", "clear", "zero", "remov", "clean"]},
        ],
        "min_groups": 2,
    },
}

# Additional broader patterns to find NEW bugs
NEW_BUG_PATTERNS = {
    "auction_price_manipulation": {
        "description": "Price manipulation in Dutch auction / descending price auction contexts",
        "keywords": [
            {"group": "auction", "terms": ["dutch auction", "descending price", "auction"]},
            {"group": "price", "terms": ["price", "manipulat", "front-run", "sandwich", "mev"]},
        ],
        "min_groups": 2,
    },
    "eip1271_signature": {
        "description": "EIP-1271 isValidSignature vulnerabilities - replay, bypass, reentrancy",
        "keywords": [
            {"group": "eip1271", "terms": ["eip-1271", "eip1271", "isvalidsignature", "1271"]},
            {"group": "vuln", "terms": ["replay", "bypass", "reentran", "exploit", "vulnerability"]},
        ],
        "min_groups": 2,
    },
    "cowswap_settlement": {
        "description": "CowSwap/GPv2 settlement vulnerabilities",
        "keywords": [
            {"group": "cow", "terms": ["cowswap", "cow swap", "gpv2", "gnosis protocol", "cow protocol"]},
            {"group": "vuln", "terms": ["settlement", "solver", "order", "exploit", "manipulat", "front-run"]},
        ],
        "min_groups": 2,
    },
    "keeper_automation": {
        "description": "Chainlink Keeper/Automation vulnerabilities - performUpkeep, checkUpkeep manipulation",
        "keywords": [
            {"group": "keeper", "terms": ["keeper", "automation", "upkeep", "performupkeep", "checkupkeep", "gelato"]},
            {"group": "vuln", "terms": ["manipulat", "front-run", "dos", "revert", "grief", "exploit", "bypass"]},
        ],
        "min_groups": 2,
    },
    "access_control_escalation": {
        "description": "Access control escalation through operational roles (not admin)",
        "keywords": [
            {"group": "access", "terms": ["role", "access control", "permission", "privilege"]},
            {"group": "escalation", "terms": ["escalat", "bypass", "unauthorized", "elevat", "trust boundar"]},
        ],
        "min_groups": 2,
    },
}


def search_csv(csv_path, source_name, pattern_config):
    """Search a CSV file for findings matching the pattern."""
    matches = []
    try:
        with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                title = row.get("title", "")
                desc = row.get("description", "")[:2000]
                text = (title + " " + desc).lower()
                severity = row.get("severity", "").strip()

                # Only consider Medium+ findings for precedent value
                if severity.lower() not in ("high", "medium", "3 (high)", "2 (med risk)"):
                    continue

                # Count matching keyword groups
                matched_groups = 0
                for kw_group in pattern_config["keywords"]:
                    if any(term in text for term in kw_group["terms"]):
                        matched_groups += 1

                if matched_groups >= pattern_config["min_groups"]:
                    matches.append({
                        "source": source_name,
                        "contest": row.get("contest_name", row.get("contest_repo", "")),
                        "issue_id": row.get("issue_id", ""),
                        "severity": severity,
                        "title": title,
                        "description": desc[:800],
                        "matched_groups": matched_groups,
                        "url": row.get("source_url", ""),
                    })
    except Exception as e:
        print(f"  Error reading {csv_path}: {e}", flush=True)
    return matches


def search_all_csvs(pattern_config):
    """Search all CSV files for a pattern."""
    all_matches = []
    csv_files = [
        (os.path.join(DATA_DIR, "code4rena_all_issues.csv"), "code4rena"),
        (os.path.join(DATA_DIR, "sherlock_all_issues.csv"), "sherlock"),
        (os.path.join(DATA_DIR, "codehawks_all_issues.csv"), "codehawks"),
    ]
    for csv_path, source in csv_files:
        if os.path.exists(csv_path):
            matches = search_csv(csv_path, source, pattern_config)
            all_matches.extend(matches)
    # Sort by matched_groups desc, then severity
    sev_order = {"high": 0, "3 (high)": 0, "medium": 1, "2 (med risk)": 1}
    all_matches.sort(key=lambda x: (-x["matched_groups"], sev_order.get(x["severity"].lower(), 2)))
    return all_matches


def call_claude_for_analysis(prompt):
    """Call Claude for LLM analysis."""
    try:
        result = subprocess.run(
            [CLAUDE_EXE, "--output-format", "json", "--model", "claude-sonnet-4-20250514", "-p"],
            input=prompt.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=180,
            shell=True,
        )
        stdout_text = result.stdout.decode("utf-8", errors="replace")
        try:
            output = json.loads(stdout_text)
            return output.get("result", stdout_text) if isinstance(output, dict) else stdout_text
        except json.JSONDecodeError:
            return stdout_text
    except subprocess.TimeoutExpired:
        return "[TIMEOUT]"
    except Exception as e:
        return f"[ERROR: {e}]"


def main():
    print("=" * 70, flush=True)
    print("PHASE 1: Searching past audits for similar precedents", flush=True)
    print("=" * 70, flush=True)

    all_results = {}

    # Search for M-02, M-07, M-14 precedents
    for finding_id, config in FINDING_PATTERNS.items():
        print(f"\n--- {finding_id} ---", flush=True)
        print(f"  Pattern: {config['description'][:80]}...", flush=True)
        matches = search_all_csvs(config)
        print(f"  Found: {len(matches)} matches (Medium+ severity)", flush=True)
        all_results[finding_id] = matches[:30]  # Top 30 per pattern

        # Show top 5
        for i, m in enumerate(matches[:5]):
            print(f"  [{i+1}] [{m['severity']}] {m['source']}/{m['contest']} {m['issue_id']}: {m['title'][:80]}", flush=True)

    # Search for new bug patterns
    print(f"\n{'=' * 70}", flush=True)
    print("PHASE 2: Searching for new vulnerability patterns", flush=True)
    print("=" * 70, flush=True)

    for pattern_id, config in NEW_BUG_PATTERNS.items():
        print(f"\n--- {pattern_id} ---", flush=True)
        print(f"  Pattern: {config['description'][:80]}", flush=True)
        matches = search_all_csvs(config)
        print(f"  Found: {len(matches)} matches", flush=True)
        all_results[pattern_id] = matches[:20]  # Top 20

        for i, m in enumerate(matches[:5]):
            print(f"  [{i+1}] [{m['severity']}] {m['source']}/{m['contest']} {m['issue_id']}: {m['title'][:80]}", flush=True)

    # Save raw results
    raw_output = os.path.join(OUTPUT_DIR, "precedent_search_results.json")
    with open(raw_output, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\nRaw results saved to {raw_output}", flush=True)

    # PHASE 3: LLM analysis - extract new bug patterns
    print(f"\n{'=' * 70}", flush=True)
    print("PHASE 3: LLM analysis - extracting new vulnerability patterns", flush=True)
    print("=" * 70, flush=True)

    # Build summaries of top findings per new bug pattern
    for pattern_id in NEW_BUG_PATTERNS:
        matches = all_results.get(pattern_id, [])
        if not matches:
            continue

        print(f"\n--- Analyzing {pattern_id} ({len(matches)} matches) ---", flush=True)

        # Build finding summaries
        summaries = []
        for i, m in enumerate(matches[:15]):
            summaries.append(
                f"[{i+1}] Source: {m['source']} | Contest: {m['contest']} | "
                f"Severity: {m['severity']} | ID: {m['issue_id']}\n"
                f"Title: {m['title']}\n"
                f"Description: {m['description'][:400]}"
            )

        findings_block = "\n\n".join(summaries)

        prompt = f"""You are a smart contract security expert. Analyze these historical audit findings and determine if similar vulnerabilities could exist in the Chainlink Payment Abstraction V2 system.

## TARGET SYSTEM: Chainlink Payment Abstraction V2
Key components:
- **BaseAuction.sol**: Dutch auction for selling protocol-held tokens (USDC, WETH) for LINK. Uses `bid()`, `performUpkeep()`, Chainlink Automation.
- **AuctionBidder.sol**: Wrapper contract with AUCTION_BIDDER_ROLE. Has `_multiCall()` for arbitrary calls after auction callback. Integrates CowSwap/GPv2 settlement.
- **PriceManager.sol**: Dual oracle (Data Streams primary + Chainlink data feed fallback). `transmit()` for price updates, `_getAssetPrice()` for price queries.
- **Caller.sol**: Library for executing arbitrary external calls via `_multiCall`.
- Access control: DEFAULT_ADMIN_ROLE, AUCTION_WORKER_ROLE, AUCTION_BIDDER_ROLE, PRICE_ADMIN_ROLE
- Defenses: ReentrancyGuard, SafeERC20, whenNotPaused, _whenNoLiveAuctions, GPv2 domainSeparator + filledAmount

## KNOWN FINDINGS (already discovered):
- H-01: Unrestricted _multiCall allows AUCTION_BIDDER_ROLE to bypass trust boundary
- M-01: Oracle staleness causes bid/performUpkeep revert (permissionless DoS)
- M-03: Single feed revert in try-catch-less loop causes cross-asset DoS
- M-02: Shared stalenessThreshold undermines dual-oracle fallback (Low)
- M-07: Future-dated timestamps extend staleness window (Low)
- M-14: Stale approval after _setAuction migration (Low)

## HISTORICAL FINDINGS ({pattern_id}):
{findings_block}

## TASK:
1. For each historical finding, briefly note its severity judgment and reasoning
2. Identify NEW vulnerability patterns from these findings that could apply to Chainlink V2 but are NOT already covered by the known findings above
3. For any new pattern found, describe:
   - The specific vulnerability
   - Which Chainlink V2 contract/function it could affect
   - Whether it's permissionless or requires a trusted role
   - Estimated severity (using Code4rena standards)

Be specific about code locations and attack flows. If no new vulnerabilities are found, say so explicitly.

Return your analysis as structured text."""

        response = call_claude_for_analysis(prompt)
        print(response[:3000], flush=True)

        # Save individual analysis
        analysis_file = os.path.join(OUTPUT_DIR, f"precedent_analysis_{pattern_id}.md")
        with open(analysis_file, "w", encoding="utf-8") as f:
            f.write(f"# Precedent Analysis: {pattern_id}\n\n")
            f.write(f"Pattern: {NEW_BUG_PATTERNS[pattern_id]['description']}\n\n")
            f.write(f"Matches found: {len(matches)}\n\n")
            f.write("## LLM Analysis\n\n")
            f.write(response)
        print(f"  Saved to {analysis_file}", flush=True)

    # Also analyze M-02, M-07, M-14 precedents for severity calibration
    print(f"\n{'=' * 70}", flush=True)
    print("PHASE 4: Severity calibration from precedents", flush=True)
    print("=" * 70, flush=True)

    for finding_id in FINDING_PATTERNS:
        matches = all_results.get(finding_id, [])
        if not matches:
            continue

        print(f"\n--- Calibrating {finding_id} ({len(matches)} precedents) ---", flush=True)

        summaries = []
        for i, m in enumerate(matches[:20]):
            summaries.append(
                f"[{i+1}] Source: {m['source']} | Contest: {m['contest']} | "
                f"Severity: {m['severity']} | ID: {m['issue_id']}\n"
                f"Title: {m['title']}\n"
                f"Desc: {m['description'][:300]}"
            )

        findings_block = "\n\n".join(summaries)

        our_finding = FINDING_PATTERNS[finding_id]["description"]

        prompt = f"""You are a Code4rena judge. Compare our finding against historical precedents and calibrate severity.

## OUR FINDING:
{finding_id}: {our_finding}
Current severity: Low

## HISTORICAL PRECEDENTS (Medium+ findings with similar patterns):
{findings_block}

## TASK:
1. List the top 5 most relevant precedents with their severity and how they compare to our finding
2. Note key differences in trust model (permissionless vs trusted role)
3. Based on precedent, is our "Low" severity appropriate? Should it be higher or lower?
4. What's the most common severity for this pattern across contests?

Be concise. Focus on actionable severity calibration."""

        response = call_claude_for_analysis(prompt)
        print(response[:2000], flush=True)

        analysis_file = os.path.join(OUTPUT_DIR, f"severity_calibration_{finding_id}.md")
        with open(analysis_file, "w", encoding="utf-8") as f:
            f.write(f"# Severity Calibration: {finding_id}\n\n")
            f.write(f"Our finding: {our_finding}\n")
            f.write(f"Current severity: Low\n\n")
            f.write(f"## Precedent Analysis ({len(matches)} matches)\n\n")
            f.write(response)
        print(f"  Saved to {analysis_file}", flush=True)

    print(f"\n{'=' * 70}", flush=True)
    print("DONE", flush=True)
    print("=" * 70, flush=True)


if __name__ == "__main__":
    main()
