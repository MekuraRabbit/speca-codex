"""Expanded pattern search: broader vulnerability patterns from past contests.
Focuses on attack surfaces NOT covered by previous searches.
"""

import csv
import json
import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

csv.field_size_limit(sys.maxsize)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "benchmarks", "data", "defi_audit_reports")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

PATTERNS = {
    # --- Auction-specific ---
    "dutch_auction_rounding": {
        "desc": "Rounding errors in Dutch auction price calculation allowing free/cheap acquisition",
        "keywords": [
            {"group": "auction", "terms": ["dutch auction", "auction price", "descending"]},
            {"group": "math", "terms": ["round", "truncat", "precision", "division", "zero price", "underflow", "overflow"]},
        ],
        "min_groups": 2,
    },
    "auction_timing_griefing": {
        "desc": "Griefing/DoS by manipulating auction start/end timing or block.timestamp",
        "keywords": [
            {"group": "auction", "terms": ["auction"]},
            {"group": "timing", "terms": ["block.timestamp", "timing", "front-run", "frontrun", "grief", "dos", "delay", "expire"]},
        ],
        "min_groups": 2,
    },
    "auction_settlement_reentrancy": {
        "desc": "Reentrancy during auction settlement or callback",
        "keywords": [
            {"group": "auction", "terms": ["auction", "settlement", "bid"]},
            {"group": "reentrancy", "terms": ["reentran", "re-entran", "callback", "cross-function"]},
        ],
        "min_groups": 2,
    },

    # --- Token handling ---
    "fee_on_transfer": {
        "desc": "Fee-on-transfer or rebasing tokens breaking balance assumptions",
        "keywords": [
            {"group": "token", "terms": ["fee-on-transfer", "fee on transfer", "deflationary", "rebas", "tax token"]},
            {"group": "impact", "terms": ["balance", "amount", "less than", "shortfall", "mismatch", "incorrect"]},
        ],
        "min_groups": 2,
    },
    "token_donation_inflation": {
        "desc": "Token donation or direct transfer to inflate balances and manipulate logic",
        "keywords": [
            {"group": "donation", "terms": ["donat", "direct transfer", "inflate", "inflation attack"]},
            {"group": "impact", "terms": ["balance", "manipulat", "accounting", "share", "first deposit"]},
        ],
        "min_groups": 2,
    },

    # --- Oracle-specific (deeper) ---
    "oracle_decimal_mismatch": {
        "desc": "Decimal mismatch between oracle price and token decimals",
        "keywords": [
            {"group": "oracle", "terms": ["oracle", "chainlink", "price feed", "price"]},
            {"group": "decimals", "terms": ["decimal", "precision", "scaling", "normali", "1e18", "1e8", "1e6"]},
        ],
        "min_groups": 2,
    },
    "oracle_manipulation_flash": {
        "desc": "Oracle manipulation via flash loans or large trades",
        "keywords": [
            {"group": "oracle", "terms": ["oracle", "price", "twap"]},
            {"group": "flash", "terms": ["flash loan", "flashloan", "manipulat", "sandwich", "large trade"]},
        ],
        "min_groups": 2,
    },

    # --- EIP-1271 / signature ---
    "eip1271_reentrancy": {
        "desc": "Reentrancy or state manipulation during isValidSignature callback",
        "keywords": [
            {"group": "sig", "terms": ["isvalidsignature", "eip-1271", "eip1271", "signature valid"]},
            {"group": "vuln", "terms": ["reentran", "state", "view", "external call", "callback"]},
        ],
        "min_groups": 2,
    },
    "order_replay_invalidation": {
        "desc": "Order replay attacks or insufficient order invalidation",
        "keywords": [
            {"group": "order", "terms": ["order", "nonce", "replay"]},
            {"group": "vuln", "terms": ["replay", "invalidat", "reuse", "duplicate", "double", "filledamount"]},
        ],
        "min_groups": 2,
    },

    # --- Access control (deeper) ---
    "role_renounce_brick": {
        "desc": "Renouncing admin role bricks the contract permanently",
        "keywords": [
            {"group": "role", "terms": ["renounce", "admin", "role", "owner"]},
            {"group": "impact", "terms": ["brick", "permanent", "irrecoverable", "lock", "stuck", "cannot"]},
        ],
        "min_groups": 2,
    },
    "pause_bypass": {
        "desc": "Bypassing pause mechanism through specific code paths",
        "keywords": [
            {"group": "pause", "terms": ["pause", "whennotpaused", "unpause", "emergency"]},
            {"group": "bypass", "terms": ["bypass", "circumvent", "still callable", "not protected", "missing"]},
        ],
        "min_groups": 2,
    },

    # --- Chainlink Automation specific ---
    "performupkeep_manipulation": {
        "desc": "performUpkeep data manipulation or validation bypass",
        "keywords": [
            {"group": "keeper", "terms": ["performupkeep", "checkupkeep", "keeper", "automation", "upkeep"]},
            {"group": "vuln", "terms": ["manipulat", "data", "bypass", "arbitrary", "unchecked", "calldata", "performdata"]},
        ],
        "min_groups": 2,
    },

    # --- Fund recovery / stuck ---
    "stuck_funds_no_recovery": {
        "desc": "Funds stuck in contract with no recovery mechanism",
        "keywords": [
            {"group": "stuck", "terms": ["stuck", "locked", "trapped", "stranded", "irrecoverable"]},
            {"group": "funds", "terms": ["fund", "token", "eth", "balance", "withdraw", "rescue"]},
        ],
        "min_groups": 2,
    },

    # --- Frontrunning ---
    "frontrun_initialization": {
        "desc": "Frontrunning contract initialization or first action",
        "keywords": [
            {"group": "frontrun", "terms": ["front-run", "frontrun", "front run", "race condition"]},
            {"group": "init", "terms": ["initializ", "constructor", "first", "deploy", "setup", "config"]},
        ],
        "min_groups": 2,
    },
}


def search_csv(csv_path, source_name, config):
    matches = []
    try:
        with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                title = row.get("title", "")
                desc = row.get("description", "")[:2000]
                text = (title + " " + desc).lower()
                severity = row.get("severity", "").strip().lower()

                if severity not in ("high", "medium", "3 (high)", "2 (med risk)"):
                    continue

                matched = sum(
                    1 for kg in config["keywords"]
                    if any(t in text for t in kg["terms"])
                )
                if matched >= config["min_groups"]:
                    matches.append({
                        "source": source_name,
                        "contest": row.get("contest_name", row.get("contest_repo", "")),
                        "issue_id": row.get("issue_id", ""),
                        "severity": row.get("severity", "").strip(),
                        "title": title,
                        "description": desc[:600],
                        "matched_groups": matched,
                    })
    except Exception as e:
        print(f"  Error: {e}", flush=True)
    return matches


def main():
    csv_files = [
        (os.path.join(DATA_DIR, "code4rena_all_issues.csv"), "code4rena"),
        (os.path.join(DATA_DIR, "sherlock_all_issues.csv"), "sherlock"),
        (os.path.join(DATA_DIR, "codehawks_all_issues.csv"), "codehawks"),
    ]

    all_results = {}

    for pat_id, config in PATTERNS.items():
        print(f"\n--- {pat_id} ---", flush=True)
        print(f"  {config['desc'][:80]}", flush=True)

        matches = []
        for csv_path, source in csv_files:
            if os.path.exists(csv_path):
                matches.extend(search_csv(csv_path, source, config))

        sev_order = {"high": 0, "3 (high)": 0, "medium": 1, "2 (med risk)": 1}
        matches.sort(key=lambda x: (-x["matched_groups"], sev_order.get(x["severity"].lower(), 2)))

        print(f"  Found: {len(matches)} matches", flush=True)
        all_results[pat_id] = {"count": len(matches), "top": matches[:10]}

        for i, m in enumerate(matches[:5]):
            print(f"  [{i+1}] [{m['severity']}] {m['source']}/{m['contest']} {m['issue_id']}: {m['title'][:80]}", flush=True)

    # Save
    out_file = os.path.join(OUTPUT_DIR, "expanded_pattern_search.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to {out_file}", flush=True)

    # Summary
    print(f"\n{'='*60}", flush=True)
    print("SUMMARY", flush=True)
    print(f"{'='*60}", flush=True)
    for pat_id, data in sorted(all_results.items(), key=lambda x: -x[1]["count"]):
        print(f"  {pat_id}: {data['count']} matches", flush=True)


if __name__ == "__main__":
    main()
