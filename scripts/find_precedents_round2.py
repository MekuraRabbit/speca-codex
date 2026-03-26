"""Round 2: Expanded precedent search targeting specific code patterns in Chainlink V2.

Focuses on patterns NOT covered by existing findings (H-01, M-01 through M-14).
"""

import csv
import json
import os
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

# New patterns derived from code reading
PATTERNS = {
    "fee_on_transfer_balance": {
        "desc": "Fee-on-transfer token breaks balance accounting (balanceOf vs actual received)",
        "keywords": [
            {"group": "fot", "terms": ["fee-on-transfer", "fee on transfer", "deflationary", "transfer fee", "tax token", "rebase"]},
            {"group": "balance", "terms": ["balance", "balanceof", "amount", "accounting"]},
        ],
        "min_groups": 2,
    },
    "negative_oracle_price_dos": {
        "desc": "Negative oracle price causes SafeCast/uint256 revert → DoS",
        "keywords": [
            {"group": "oracle", "terms": ["oracle", "chainlink", "price feed", "latestrounddata"]},
            {"group": "negative", "terms": ["negative", "revert", "safecast", "tou", "int256", "int192", "underflow"]},
            {"group": "dos", "terms": ["dos", "denial", "revert", "brick", "freeze", "lock"]},
        ],
        "min_groups": 2,
    },
    "dutch_auction_frontrun": {
        "desc": "Dutch auction price curve frontrunning / MEV / timing manipulation",
        "keywords": [
            {"group": "dutch", "terms": ["dutch auction", "descending", "price curve", "decay", "discount"]},
            {"group": "timing", "terms": ["front-run", "frontrun", "mev", "sandwich", "timing", "manipulation", "race"]},
        ],
        "min_groups": 2,
    },
    "checkupkeep_performupkeep_mismatch": {
        "desc": "State change between checkUpkeep and performUpkeep causes issues",
        "keywords": [
            {"group": "keeper", "terms": ["checkupkeep", "performupkeep", "keeper", "automation", "upkeep"]},
            {"group": "state", "terms": ["stale", "mismatch", "race", "front-run", "revert", "state change", "between"]},
        ],
        "min_groups": 2,
    },
    "rounding_precision_mulDiv": {
        "desc": "Integer division / mulDiv rounding causes value extraction or loss",
        "keywords": [
            {"group": "rounding", "terms": ["rounding", "precision", "truncat", "round down", "round up", "muldiv", "wad", "ray"]},
            {"group": "exploit", "terms": ["extract", "profit", "loss", "steal", "arbitrage", "dust", "zero", "favor"]},
        ],
        "min_groups": 2,
    },
    "approval_full_balance_relayer": {
        "desc": "Approving full balance to relayer/router allows draining more than intended",
        "keywords": [
            {"group": "approval", "terms": ["approv", "allowance", "forceapprov"]},
            {"group": "full", "terms": ["full balance", "entire balance", "max amount", "type(uint256).max", "all tokens", "unlimited"]},
            {"group": "drain", "terms": ["drain", "steal", "excess", "unintended", "more than"]},
        ],
        "min_groups": 2,
    },
    "feeAggregator_pull_pattern": {
        "desc": "External contract pull (transferForSwap) fails/returns less, breaking assumptions",
        "keywords": [
            {"group": "pull", "terms": ["transferfrom", "pull", "transferforswap", "external call", "callback"]},
            {"group": "fail", "terms": ["fail", "revert", "insufficient", "less than", "partial", "return value"]},
            {"group": "auction", "terms": ["auction", "swap", "liquidat", "settlement"]},
        ],
        "min_groups": 2,
    },
    "delete_mapping_state_leak": {
        "desc": "delete mapping entry leaves stale state / doesn't clean up cross-references",
        "keywords": [
            {"group": "delete", "terms": ["delete", "remove", "clear", "cleanup", "clean up"]},
            {"group": "state", "terms": ["mapping", "state", "storage", "stale", "residual", "orphan", "leftover"]},
            {"group": "issue", "terms": ["inconsisten", "leak", "corrupt", "broken", "invalid", "dangling"]},
        ],
        "min_groups": 2,
    },
    "auction_dust_griefing": {
        "desc": "Dust amount attack to grief auction lifecycle (prevent ending/starting)",
        "keywords": [
            {"group": "dust", "terms": ["dust", "small amount", "minimum", "wei", "tiny", "negligible"]},
            {"group": "grief", "terms": ["grief", "dos", "block", "prevent", "stuck", "lock", "freeze"]},
            {"group": "auction", "terms": ["auction", "liquidat", "bid"]},
        ],
        "min_groups": 2,
    },
    "safeTransfer_before_state_update": {
        "desc": "Token transfer before state update enables cross-function reentrancy",
        "keywords": [
            {"group": "transfer", "terms": ["safetransfer", "transfer", "send"]},
            {"group": "reentrancy", "terms": ["reentran", "cross-function", "cross function", "read-only", "callback"]},
            {"group": "state", "terms": ["state", "before", "check-effect", "cei", "interaction"]},
        ],
        "min_groups": 2,
    },
    "erc20_decimal_mismatch": {
        "desc": "Token decimal mismatch in price/amount calculations causing over/underpayment",
        "keywords": [
            {"group": "decimal", "terms": ["decimal", "precision", "scale", "18 decimal", "6 decimal", "8 decimal"]},
            {"group": "mismatch", "terms": ["mismatch", "wrong", "incorrect", "different", "inconsisten"]},
            {"group": "price", "terms": ["price", "amount", "value", "calculat", "conver"]},
        ],
        "min_groups": 2,
    },
    "enumerable_set_dos": {
        "desc": "EnumerableSet iteration gas limit DoS when set grows large",
        "keywords": [
            {"group": "enumerable", "terms": ["enumerableset", "enumerable", "set.values", "array", "loop"]},
            {"group": "gas", "terms": ["gas", "out of gas", "oog", "limit", "dos", "block gas"]},
        ],
        "min_groups": 2,
    },
}


def search_csv(csv_path, source_name, pattern_config):
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

                matched_groups = 0
                for kw_group in pattern_config["keywords"]:
                    if any(term in text for term in kw_group["terms"]):
                        matched_groups += 1

                if matched_groups >= pattern_config["min_groups"]:
                    matches.append({
                        "source": source_name,
                        "contest": row.get("contest_name", row.get("contest_repo", "")),
                        "issue_id": row.get("issue_id", ""),
                        "severity": row.get("severity", ""),
                        "title": title,
                        "description": desc[:600],
                        "matched_groups": matched_groups,
                    })
    except Exception as e:
        print(f"  Error: {e}", flush=True)
    return matches


def search_all_csvs(pattern_config):
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
    sev_order = {"high": 0, "3 (high)": 0, "medium": 1, "2 (med risk)": 1}
    all_matches.sort(key=lambda x: (-x["matched_groups"], sev_order.get(x["severity"].lower(), 2)))
    return all_matches


def call_claude(prompt):
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
    print("ROUND 2: Expanded precedent search", flush=True)
    print("=" * 70, flush=True)

    all_results = {}
    promising = []  # Patterns with enough matches to analyze

    for pattern_id, config in PATTERNS.items():
        print(f"\n--- {pattern_id} ---", flush=True)
        print(f"  {config['desc'][:80]}", flush=True)
        matches = search_all_csvs(config)
        print(f"  Found: {len(matches)} matches", flush=True)
        all_results[pattern_id] = matches[:25]

        for i, m in enumerate(matches[:3]):
            print(f"  [{i+1}] [{m['severity']}] {m['source']}/{m['contest']} {m['issue_id']}: {m['title'][:70]}", flush=True)

        if len(matches) >= 3:
            promising.append(pattern_id)

    # Save raw results
    raw_output = os.path.join(OUTPUT_DIR, "precedent_round2_results.json")
    with open(raw_output, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\nRaw results: {raw_output}", flush=True)

    # LLM analysis on promising patterns
    print(f"\n{'=' * 70}", flush=True)
    print(f"LLM ANALYSIS on {len(promising)} promising patterns", flush=True)
    print(f"{'=' * 70}", flush=True)

    target_code = """## TARGET: Chainlink Payment Abstraction V2

### BaseAuction.sol key code:
- `bid()`: L410-458. s_entered reentrancy guard. Gets price via _getAssetPrice(asset, true).
  Calculates assetOutAmount via _getAssetOutAmount. safeTransfer(asset→bidder) BEFORE callback.
  Then IAuctionCallback(msg.sender).auctionCallback(...). Then safeTransferFrom(assetOut←bidder).
- `_getAssetOutAmount()`: L777-803. Uses FixedPointMathLib.mulDiv/mulDivUp/mulWadUp.
  priceMultiplier = startingPriceMultiplier - (startingPriceMultiplier-endingPriceMultiplier)*elapsed/duration.
  auctionUsdValue = amountIn.mulDivUp(assetInUsdPrice, 10**decimals).mulWadUp(priceMultiplier).
  return auctionUsdValue.mulDivUp(10**assetOutDecimals, assetOutUsdPrice).
- `performUpkeep()`: L305-370. AUCTION_WORKER_ROLE. Calls feeAggregator.transferForSwap() externally.
  Starts/ends auctions. _onAuctionEnd transfers remaining balance back to feeAggregator.
- `checkUpkeep()`: L216-294. view. Iterates s_allowlistedAssets (EnumerableSet).

### PriceManager.sol key code:
- `_getAssetPrice()`: L372-419. Prioritizes Data Streams price. Falls back to Chainlink data feed.
  Uses SafeCast: answer.toUint256() (reverts on negative). Same stalenessThreshold for both.
- `transmit()`: L133-183. PRICE_ADMIN_ROLE. Checks observationsTimestamp >= block.timestamp - stalenessThreshold.
  No upper bound check on future timestamps. Uses int192→uint256 SafeCast.

### GPV2CompatibleAuction.sol key code:
- `_onAuctionStart()`: forceApprove(vaultRelayer, FULL balanceOf) — approves entire contract balance.
- `_onAuctionEnd()`: forceApprove(vaultRelayer, 0) — revokes.
- `isValidSignature()`: validates order at settlement time with current prices.

### AuctionBidder.sol key code:
- `bid()`: AUCTION_BIDDER_ROLE. If solution.length > 0, encodes as callback data.
  Else forceApprove(auction, getAssetOutAmount). After bid, transfers leftover to receiver.
- `auctionCallback()`: Only callable by auction contract. Decodes calls, executes _multiCall(calls).
  Then forceApprove(assetOut, amountOut).
- `_setAuction()`: No approval revocation of old auction.

### Key facts:
- Tokens: USDC (6 dec), WETH (18 dec), LINK (18 dec) → assetOut is LINK
- SafeERC20 used everywhere
- ReentrancyGuard via s_entered flag in bid()
- Access roles: DEFAULT_ADMIN_ROLE, AUCTION_WORKER_ROLE, AUCTION_BIDDER_ROLE, PRICE_ADMIN_ROLE, ASSET_ADMIN_ROLE

### KNOWN findings:
- H-01: Unrestricted _multiCall in auctionCallback (AUCTION_BIDDER_ROLE escalation)
- M-01: Oracle staleness DoS (permissionless, bid/performUpkeep revert)
- M-03: Single feed revert in loop causes cross-asset DoS
- M-02: Shared stalenessThreshold (Low)
- M-07: Future timestamps in transmit (Low)
- M-14: Stale approval after _setAuction (Low)
- M-04: QA (AUCTION_WORKER_ROLE)
- M-05: QA (non-economic)
- M-06: QA (exact approve self-protection)"""

    for pattern_id in promising:
        matches = all_results.get(pattern_id, [])
        if not matches:
            continue

        print(f"\n--- Analyzing: {pattern_id} ({len(matches)} matches) ---", flush=True)

        summaries = []
        for i, m in enumerate(matches[:15]):
            summaries.append(
                f"[{i+1}] {m['source']}/{m['contest']} {m['issue_id']} ({m['severity']})\n"
                f"Title: {m['title']}\n"
                f"Desc: {m['description'][:350]}"
            )
        findings_block = "\n\n".join(summaries)

        prompt = f"""You are a smart contract security auditor analyzing Chainlink Payment Abstraction V2 for a Code4rena contest.

{target_code}

## Pattern being analyzed: {pattern_id}
{PATTERNS[pattern_id]['desc']}

## Historical findings with this pattern:
{findings_block}

## TASK:
Analyze whether this vulnerability pattern exists in the Chainlink V2 code described above.

For each potential new vulnerability:
1. Cite the EXACT function and line range
2. Describe the attack flow step-by-step
3. State if permissionless or requires trusted role
4. Explain why it's NOT already covered by known findings
5. Estimate severity (Code4rena: High/Medium/Low/QA)

If the pattern doesn't apply or is already covered, say so clearly and explain why.

Be rigorous. Do NOT report vulnerabilities that require DEFAULT_ADMIN_ROLE as that's trusted/OOS.
AUCTION_WORKER_ROLE and PRICE_ADMIN_ROLE are trusted/OOS.
Only AUCTION_BIDDER_ROLE and permissionless attacks are in scope.

Return structured analysis."""

        response = call_claude(prompt)
        print(response[:2500], flush=True)

        analysis_file = os.path.join(OUTPUT_DIR, f"round2_analysis_{pattern_id}.md")
        with open(analysis_file, "w", encoding="utf-8") as f:
            f.write(f"# Round 2 Analysis: {pattern_id}\n\n")
            f.write(f"Pattern: {PATTERNS[pattern_id]['desc']}\n")
            f.write(f"Matches: {len(matches)}\n\n")
            f.write("## LLM Analysis\n\n")
            f.write(response)
        print(f"  → {analysis_file}", flush=True)

    print(f"\n{'=' * 70}", flush=True)
    print("ROUND 2 COMPLETE", flush=True)
    print(f"{'=' * 70}", flush=True)


if __name__ == "__main__":
    main()
