#!/usr/bin/env python3
"""
Keyword-based fast pattern matching: matches known DeFi vulnerability patterns
from past_defi_patterns.csv against Phase 03 audit findings.

No LLM calls — pure keyword/regex matching using only stdlib + csv.
"""

import csv
import json
import os
import re
import sys
from pathlib import Path

# Ensure stdout handles unicode on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
PATTERNS_CSV = ROOT / "outputs" / "past_defi_patterns.csv"
FINDINGS_DIR = ROOT / "benchmarks" / "results" / "rq1" / "sherlock_ethereum_audit_contest"


def load_patterns(csv_path: Path) -> list[dict]:
    """Load patterns from CSV. Each pattern has source info and parsed keyword groups.

    keyword_matched examples:
        "dutch+auction"                          -> one group: [["dutch"], ["auction"]]
        "reentrancy+callback/hook"               -> one group: [["reentrancy"], ["callback", "hook"]]
        "balance+stale/race; price+oracle+swap"  -> two groups (either can match)
        "EIP-1271/isValidSignature"              -> one group: [["eip-1271", "isvalidsignature"]] (alternatives)

    A *group* matches when ALL its terms match (AND logic across `+`).
    Each term is a set of alternatives (OR logic across `/`).
    A *pattern* matches when ANY of its groups matches (OR logic across `;`).
    """
    patterns = []
    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw = row.get("keyword_matched", "").strip()
            if not raw:
                continue

            groups = []
            for group_str in raw.split(";"):
                group_str = group_str.strip()
                if not group_str:
                    continue
                terms = []
                for term_str in group_str.split("+"):
                    alternatives = [alt.strip().lower() for alt in term_str.split("/") if alt.strip()]
                    if alternatives:
                        terms.append(alternatives)
                if terms:
                    groups.append(terms)

            if groups:
                patterns.append({
                    "source": row.get("source", ""),
                    "contest": row.get("contest", ""),
                    "severity": row.get("severity", ""),
                    "title": row.get("title", "")[:80],
                    "keyword_raw": raw,
                    "groups": groups,
                })
    return patterns


def _build_alt_matcher(alt: str):
    """Build a matcher for a single alternative string.

    For underscore-joined terms like 'sig_replay', we match both the literal
    string AND the case where sub-words appear independently in the text.
    For identifiers like 'isValidSignature' or 'EIP-1271', match as literal substring.

    Returns a function text -> bool.
    """
    # Always try literal match first
    literal_re = re.compile(re.escape(alt), re.IGNORECASE)

    # For underscore-joined terms, also match sub-words independently
    sub_words = [w for w in alt.split("_") if w]
    if len(sub_words) > 1:
        sub_res = [re.compile(re.escape(w), re.IGNORECASE) for w in sub_words]

        def matcher(text: str) -> bool:
            if literal_re.search(text):
                return True
            return all(r.search(text) for r in sub_res)
    else:
        # Also handle hyphen-joined (e.g. "EIP-1271") — match literal or parts
        hyph_parts = [w for w in alt.split("-") if w]
        if len(hyph_parts) > 1:
            hyph_res = [re.compile(re.escape(w), re.IGNORECASE) for w in hyph_parts]

            def matcher(text: str) -> bool:
                if literal_re.search(text):
                    return True
                return all(r.search(text) for r in hyph_res)
        else:
            def matcher(text: str) -> bool:
                return bool(literal_re.search(text))

    return matcher


def compile_pattern_matchers(patterns: list[dict]) -> list[dict]:
    """Pre-compile matchers for each term alternative for speed."""
    for pat in patterns:
        compiled_groups = []
        for group in pat["groups"]:
            compiled_terms = []
            for alternatives in group:
                # A term matches if ANY alternative matches (OR across `/`)
                alt_matchers = [_build_alt_matcher(alt) for alt in alternatives]
                compiled_terms.append(alt_matchers)
            compiled_groups.append(compiled_terms)
        pat["compiled_groups"] = compiled_groups
    return patterns


def matches_pattern(text: str, pat: dict) -> str | None:
    """Check if text matches any group in the pattern. Returns matched keyword group string or None.

    A group matches when ALL its terms match (AND across `+`).
    A term matches when ANY of its alternatives matches (OR across `/`).
    """
    for gi, compiled_group in enumerate(pat["compiled_groups"]):
        all_terms_match = True
        for alt_matchers in compiled_group:
            if not any(m(text) for m in alt_matchers):
                all_terms_match = False
                break
        if all_terms_match:
            group = pat["groups"][gi]
            return "+".join("/".join(alts) for alts in group)
    return None


def load_findings(findings_dir: Path) -> list[dict]:
    """Load all Phase 03 findings from all branch directories."""
    findings = []
    if not findings_dir.is_dir():
        print(f"WARNING: Findings directory not found: {findings_dir}", file=sys.stderr)
        return findings

    for branch_dir in sorted(findings_dir.iterdir()):
        if not branch_dir.is_dir():
            continue
        for json_file in sorted(branch_dir.glob("03_*.json")):
            try:
                with open(json_file, encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                print(f"WARNING: Skipping {json_file}: {e}", file=sys.stderr)
                continue

            audit_items = data.get("audit_items", [])
            for item in audit_items:
                findings.append({
                    "branch": branch_dir.name,
                    "file": json_file.name,
                    "property_id": item.get("property_id", ""),
                    "classification": item.get("classification", ""),
                    "proof_trace": item.get("proof_trace", ""),
                    "attack_scenario": item.get("attack_scenario", ""),
                    "code_path": item.get("code_path", ""),
                })
    return findings


def main():
    print("=" * 72)
    print("  Keyword Pattern Matcher — DeFi Patterns vs Phase 03 Findings")
    print("=" * 72)

    # 1. Load patterns
    print(f"\nLoading patterns from {PATTERNS_CSV} ...")
    patterns = load_patterns(PATTERNS_CSV)
    patterns = compile_pattern_matchers(patterns)

    # Deduplicate by keyword_raw to get unique keyword patterns
    seen_keywords = {}
    unique_patterns = []
    for p in patterns:
        if p["keyword_raw"] not in seen_keywords:
            seen_keywords[p["keyword_raw"]] = p
            unique_patterns.append(p)

    print(f"  Loaded {len(patterns)} pattern rows, {len(unique_patterns)} unique keyword patterns")

    # 2. Load findings
    print(f"\nLoading Phase 03 findings from {FINDINGS_DIR} ...")
    findings = load_findings(FINDINGS_DIR)
    print(f"  Loaded {len(findings)} findings across branches")

    if not findings:
        print("\nNo findings to match against. Exiting.")
        return

    # 3. Match
    print("\nMatching patterns against findings ...")
    matches = []
    matched_finding_ids = set()
    matched_pattern_keys = set()

    for finding in findings:
        # Combine searchable text
        search_text = " ".join([
            finding["proof_trace"],
            finding["attack_scenario"],
            finding["code_path"],
        ])
        if not search_text.strip():
            continue

        for pat in unique_patterns:
            matched_kw = matches_pattern(search_text, pat)
            if matched_kw:
                matches.append({
                    "finding_branch": finding["branch"],
                    "finding_property_id": finding["property_id"],
                    "finding_classification": finding["classification"],
                    "pattern_keyword": pat["keyword_raw"],
                    "matched_group": matched_kw,
                    "pattern_title": pat["title"],
                })
                matched_finding_ids.add((finding["branch"], finding["property_id"]))
                matched_pattern_keys.add(pat["keyword_raw"])

    # 4. Report matches
    print(f"\n{'─' * 72}")
    print(f"  MATCHES ({len(matches)} total)")
    print(f"{'─' * 72}")

    if matches:
        # Group by pattern keyword for readability
        by_keyword: dict[str, list[dict]] = {}
        for m in matches:
            by_keyword.setdefault(m["pattern_keyword"], []).append(m)

        for kw in sorted(by_keyword.keys()):
            kw_matches = by_keyword[kw]
            print(f"\n  Pattern: {kw}")
            print(f"  Matches: {len(kw_matches)} findings")
            for m in kw_matches[:10]:  # Show up to 10 per pattern
                print(f"    - [{m['finding_branch']}] {m['finding_property_id']}"
                      f" ({m['finding_classification']}) via \"{m['matched_group']}\"")
            if len(kw_matches) > 10:
                print(f"    ... and {len(kw_matches) - 10} more")
    else:
        print("  No matches found.")

    # 5. Summary
    print(f"\n{'=' * 72}")
    print("  SUMMARY")
    print(f"{'=' * 72}")
    print(f"  Total unique keyword patterns : {len(unique_patterns)}")
    print(f"  Total Phase 03 findings       : {len(findings)}")
    print(f"  Total matches                 : {len(matches)}")
    print(f"  Unique findings matched       : {len(matched_finding_ids)}")
    print(f"  Unique patterns matched       : {len(matched_pattern_keys)}")
    finding_match_rate = len(matched_finding_ids) / len(findings) * 100 if findings else 0
    pattern_match_rate = len(matched_pattern_keys) / len(unique_patterns) * 100 if unique_patterns else 0
    print(f"  Finding match rate            : {finding_match_rate:.1f}%"
          f" ({len(matched_finding_ids)}/{len(findings)})")
    print(f"  Pattern match rate            : {pattern_match_rate:.1f}%"
          f" ({len(matched_pattern_keys)}/{len(unique_patterns)})")
    print(f"{'=' * 72}")


if __name__ == "__main__":
    main()
