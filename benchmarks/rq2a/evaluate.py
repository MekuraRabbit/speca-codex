#!/usr/bin/env python3
"""RQ2a: Evaluate SPECA Phase 03 audit results against RepoAudit ground truth.

Uses Claude (via CLI) as a semantic matcher — same approach as RQ1.
For each ground truth bug, asks Claude whether any SPECA finding detects it.
For unmatched findings, asks Claude whether they match any known bug (FP check).

Usage:
    uv run python3 benchmarks/rq2a/evaluate.py
    uv run python3 benchmarks/rq2a/evaluate.py --reparse   # re-parse cached LLM responses
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from collections import defaultdict
from pathlib import Path

import yaml

# ── Paths ──────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
BASELINES_PATH = SCRIPT_DIR / "published_baselines.yaml"
GROUND_TRUTH_PATH = SCRIPT_DIR / "ground_truth_bugs.yaml"
DEFAULT_RESULTS_DIR = SCRIPT_DIR.parent / "results" / "rq2a" / "speca"
DEFAULT_SUMMARY_OUT = DEFAULT_RESULTS_DIR / "speca_summary.json"

# ── Project Mapping ───────────────────────────────────────────────
PROJECT_ID_TO_NAME = {
    "N1": "sofa-pbrpc",
    "N2": "ImageMagick/MagickCore",
    "N3": "coturn/src/server",
    "N4": "libfreenect",
    "N5": "openldap",
    "M1": "libsass",
    "M2": "memcached",
    "M2b": "memcached",
    "M3": "linux/driver/net",
    "M4": "linux/sound",
    "M5": "linux/mm",
    "U1": "Redis",
    "U2": "linux/drivers/peci",
    "U3": "shadowsocks-libev",
    "U4": "wabt-tool",
    "U5": "icu/icu4c/source/i18n",
}

CANONICAL_ID = {"M2b": "M2"}

POSITIVE_CLASSIFICATIONS = {"vulnerability", "potential-vulnerability"}


# ── LLM helpers (same pattern as rq1/matchers.py) ─────────────────

def call_llm(prompt: str) -> str:
    """Call Claude via CLI and return raw text response."""
    env = os.environ.copy()
    for var in ("CLAUDECODE", "CLAUDE_CODE_SESSION_ID"):
        env.pop(var, None)

    model = env.get("RQ2A_MODEL", "haiku")
    command = ["claude", "--output-format", "json", "--model", model, "-p", prompt]

    result = subprocess.run(command, check=False, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        print(f"  [llm] FAIL (rc={result.returncode}): {result.stderr[:200] if result.stderr else ''}")
        return ""
    try:
        envelope = json.loads(result.stdout)
        if isinstance(envelope, dict) and "result" in envelope:
            return str(envelope["result"])
    except (json.JSONDecodeError, TypeError):
        pass
    return result.stdout


def extract_json_from_text(text: str) -> dict | None:
    """Extract a JSON object from LLM output (handles envelopes, markdown, etc.)."""
    if not text:
        return None
    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None


def _parse_response(
    raw: str, candidate_ids: list[str], index_key: str = "finding_index",
) -> tuple[bool, str | None, float]:
    """Parse LLM JSON response → (matched, candidate_id, confidence)."""
    payload = extract_json_from_text(raw) or {}
    matched = bool(payload.get("match"))
    idx = payload.get(index_key)
    if idx is None:
        for fallback in ("finding_index", "issue_index", "bug_index", "candidate_index"):
            if fallback != index_key and fallback in payload:
                idx = payload[fallback]
                break
    try:
        confidence = float(payload.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    if matched and isinstance(idx, int) and 0 <= idx < len(candidate_ids):
        return True, candidate_ids[idx], confidence
    if matched:
        return True, None, confidence
    return False, None, confidence


def _truncate(text: str, max_chars: int = 400) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "..."


def _build_finding_text(f: dict) -> str:
    """Build display text for a Phase 03 finding."""
    parts = [
        f.get("proof_trace", ""),
        f.get("attack_scenario", ""),
        f.get("code_path", ""),
    ]
    return "\n".join(p for p in parts if p).strip()


# ── Loaders ────────────────────────────────────────────────────────

def load_findings(project_dir: Path) -> list[dict]:
    """Load all Phase 03 audit findings for a project directory."""
    findings = []
    for f in sorted(project_dir.glob("03_PARTIAL_*.json")):
        data = json.loads(f.read_text())
        findings.extend(data.get("audit_items", []))
    return findings


# ── Recall matching: bug → findings ────────────────────────────────

def match_bugs(
    bugs: list[dict],
    project_findings: dict[str, list[dict]],
    cache_path: Path | None = None,
) -> tuple[dict[str, dict], int]:
    """For each ground truth bug, ask Claude if any SPECA finding detects it.

    Returns (matches, llm_calls) where matches = {bug_id: {finding_id, confidence}}.
    """
    matches: dict[str, dict] = {}
    llm_calls = 0
    cache_handle = None
    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_handle = cache_path.open("w", encoding="utf-8")

    try:
        for bug in bugs:
            project_name = bug["project"]
            findings = project_findings.get(project_name, [])
            if not findings:
                print(f"  {bug['id']}: SKIP (no findings for {project_name})")
                continue

            # Build findings block
            finding_lines = []
            finding_ids = []
            for idx, f in enumerate(findings):
                text = _truncate(_build_finding_text(f))
                finding_lines.append(f"[{idx}] {f.get('property_id', '?')}: {text}")
                finding_ids.append(f.get("property_id", ""))
            findings_block = "\n".join(finding_lines)

            bug_desc = _truncate(bug.get("description", ""), 500)
            prompt = (
                "Was the following known vulnerability detected by any of the audit findings below?\n"
                'Respond with JSON only: {"match": true|false, "finding_index": number|null, "confidence": 0.0-1.0}\n\n'
                f"KNOWN VULNERABILITY ({bug['id']}, {bug['bug_type']}):\n"
                f"File: {bug.get('file', '?')}\n"
                f"Function: {bug.get('function', '?')}\n"
                f"Line: {bug.get('line', '?')}\n"
                f"Description: {bug_desc}\n\n"
                f"AUDIT FINDINGS ({len(findings)} total):\n{findings_block}\n"
            )

            raw = call_llm(prompt)
            llm_calls += 1

            if cache_handle:
                cache_handle.write(json.dumps({
                    "bug_id": bug["id"],
                    "raw": raw,
                    "finding_ids": finding_ids,
                }, ensure_ascii=False) + "\n")
                cache_handle.flush()

            matched, finding_id, confidence = _parse_response(raw, finding_ids)
            if matched:
                matches[bug["id"]] = {"finding_id": finding_id, "confidence": confidence}
                print(f"  {bug['id']}: MATCHED -> {finding_id} (conf={confidence})")
            else:
                print(f"  {bug['id']}: no match (conf={confidence})")
    finally:
        if cache_handle:
            cache_handle.close()

    return matches, llm_calls


def reparse_recall_cache(cache_path: Path) -> tuple[dict[str, dict], int]:
    """Re-parse cached recall LLM responses without calling LLM."""
    matches: dict[str, dict] = {}
    total = 0
    for line in cache_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        total += 1
        bug_id = record.get("bug_id", "")
        raw = record.get("raw", "")
        finding_ids = record.get("finding_ids", [])
        matched, finding_id, confidence = _parse_response(raw, finding_ids)
        if matched:
            matches[bug_id] = {"finding_id": finding_id, "confidence": confidence}
        print(f"  reparse {bug_id}: matched={matched}, finding={finding_id}, conf={confidence}")
    return matches, total


# ── FP detection: finding → bugs ──────────────────────────────────

def check_findings_fp(
    unmatched_findings: list[dict],
    project_bugs: dict[str, list[dict]],
    cache_path: Path | None = None,
) -> dict[str, dict]:
    """For each unmatched finding, ask Claude if it matches any known bug.

    Returns {property_id: {bug_id, confidence}} for matched findings (→ not FP).
    """
    results: dict[str, dict] = {}
    cache_handle = None
    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_handle = cache_path.open("w", encoding="utf-8")

    try:
        for finding in unmatched_findings:
            project_name = finding.get("_project", "")
            bugs = project_bugs.get(project_name, [])
            if not bugs:
                continue

            # Build bugs block
            bug_lines = []
            bug_ids = []
            for idx, bug in enumerate(bugs):
                bug_lines.append(
                    f"[{idx}] {bug['id']} ({bug['bug_type']}): "
                    f"{bug.get('file', '?')}::{bug.get('function', '?')} — "
                    f"{_truncate(bug.get('description', ''), 200)}"
                )
                bug_ids.append(bug["id"])
            bugs_block = "\n".join(bug_lines)

            text = _truncate(_build_finding_text(finding))
            prompt = (
                "Does the following audit finding describe the same vulnerability as any known bug below?\n"
                'Respond with JSON only: {"match": true|false, "bug_index": number|null, "confidence": 0.0-1.0}\n\n'
                f"AUDIT FINDING ({finding.get('property_id', '?')}):\n"
                f"{text}\n\n"
                f"KNOWN BUGS ({len(bugs)}):\n{bugs_block}\n"
            )

            raw = call_llm(prompt)

            if cache_handle:
                cache_handle.write(json.dumps({
                    "finding_id": finding.get("property_id", ""),
                    "raw": raw,
                    "bug_ids": bug_ids,
                }, ensure_ascii=False) + "\n")
                cache_handle.flush()

            matched, bug_id, confidence = _parse_response(raw, bug_ids, index_key="bug_index")
            if matched and bug_id:
                results[finding.get("property_id", "")] = {
                    "bug_id": bug_id, "confidence": confidence,
                }
                print(f"  fp-check {finding.get('property_id', '?')}: -> {bug_id} (conf={confidence})")
            else:
                print(f"  fp-check {finding.get('property_id', '?')}: FP")
    finally:
        if cache_handle:
            cache_handle.close()

    return results


def reparse_fp_cache(cache_path: Path) -> dict[str, dict]:
    """Re-parse cached FP LLM responses."""
    results: dict[str, dict] = {}
    for line in cache_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        finding_id = record.get("finding_id", "")
        raw = record.get("raw", "")
        bug_ids = record.get("bug_ids", [])
        matched, bug_id, confidence = _parse_response(raw, bug_ids, index_key="bug_index")
        if matched and bug_id:
            results[finding_id] = {"bug_id": bug_id, "confidence": confidence}
    return results


# ── Update helpers (format-preserving) ─────────────────────────────

def update_ground_truth(detected_bugs: set[str]) -> None:
    """Update speca: null → true/false in ground_truth_bugs.yaml."""
    text = GROUND_TRUTH_PATH.read_text()
    lines = text.split("\n")

    current_bug_id = None
    new_lines = []
    for line in lines:
        m = re.match(r"\s*- id:\s*(\S+)", line)
        if m:
            current_bug_id = m.group(1)
        if "speca:" in line and current_bug_id:
            detected = current_bug_id in detected_bugs
            line = re.sub(r"speca:\s*\w+", f"speca: {str(detected).lower()}", line)
        new_lines.append(line)

    GROUND_TRUTH_PATH.write_text("\n".join(new_lines))


def update_baselines(summary: dict) -> None:
    """Update speca TP/FP/precision in published_baselines.yaml."""
    text = BASELINES_PATH.read_text()
    lines = text.split("\n")

    in_speca = False
    new_lines = []
    for line in lines:
        stripped = line.lstrip()
        if re.match(r"speca:", stripped) and not stripped.startswith("bug_bounty"):
            in_speca = True
        elif in_speca and re.match(r"\w+:", stripped) and not re.match(
            r"(display_name|tp|fp|precision|notes|source|inter_procedural_tp|"
            r"avg_hours_per_project|avg_cost_per_project|avg_prompt_rounds|cost_per_bug):",
            stripped,
        ):
            in_speca = False

        if in_speca:
            if re.match(r"\s+tp:", line):
                line = re.sub(r"tp:\s*\S+", f"tp: {summary['tp']}", line)
            elif re.match(r"\s+fp:", line):
                line = re.sub(r"fp:\s*\S+", f"fp: {summary['fp']}", line)
            elif re.match(r"\s+precision:", line):
                line = re.sub(r"precision:\s*\S+", f"precision: {summary['precision']}", line)
            elif re.match(r"\s+notes:", line):
                line = re.sub(r"notes:.*", 'notes: "SPECA automated evaluation"', line)

        new_lines.append(line)

    BASELINES_PATH.write_text("\n".join(new_lines))


# ── Main evaluation ───────────────────────────────────────────────

def evaluate(results_dir: Path, output_path: Path, reparse: bool = False) -> dict:
    # Load ground truth
    gt = yaml.safe_load(GROUND_TRUTH_PATH.read_text())
    bugs = gt["bugs"]
    total_gt = len(bugs)

    # Aggregate positive findings by project name
    project_findings: dict[str, list[dict]] = defaultdict(list)
    all_positive: list[dict] = []

    for project_dir in sorted(results_dir.iterdir()):
        if not project_dir.is_dir():
            continue
        pid = project_dir.name
        if pid not in PROJECT_ID_TO_NAME:
            continue
        pname = PROJECT_ID_TO_NAME[pid]

        findings = load_findings(project_dir)
        positive = [
            f for f in findings
            if f.get("classification") in POSITIVE_CLASSIFICATIONS
        ]
        for f in positive:
            f["_project"] = pname  # tag for FP check
        project_findings[pname].extend(positive)
        all_positive.extend(positive)

        total = len(findings)
        pos = len(positive)
        print(f"  {pid} ({pname}): {total} findings, {pos} positive")

    total_positive = len(all_positive)
    print(f"\nTotal: {total_positive} positive findings across {len(project_findings)} projects\n")

    if total_positive == 0:
        print("No positive findings — skipping LLM matching.")
        summary = _empty_summary(bugs, total_gt, output_path)
        return summary

    # ── Step 1: Recall — bug → findings ───────────────────────────
    cache_recall = results_dir / "llm_cache_recall.jsonl"
    print("=== Step 1: Recall (bug → findings) ===")

    if reparse and cache_recall.exists():
        print(f"Re-parsing cache: {cache_recall}")
        recall_matches, _ = reparse_recall_cache(cache_recall)
    else:
        recall_matches, llm_calls = match_bugs(bugs, project_findings, cache_recall)
        print(f"LLM calls: {llm_calls}")

    # ── Step 2: FP detection — finding → bugs ─────────────────────
    matched_pids = {m["finding_id"] for m in recall_matches.values() if m.get("finding_id")}
    unmatched = [f for f in all_positive if f.get("property_id") not in matched_pids]

    # Group bugs by project for FP check
    bugs_by_project: dict[str, list[dict]] = defaultdict(list)
    for bug in bugs:
        bugs_by_project[bug["project"]].append(bug)

    cache_fp = results_dir / "llm_cache_fp.jsonl"
    print(f"\n=== Step 2: FP detection ({len(unmatched)} unmatched findings) ===")

    if reparse and cache_fp.exists():
        print(f"Re-parsing cache: {cache_fp}")
        fp_matches = reparse_fp_cache(cache_fp)
    else:
        fp_matches = check_findings_fp(unmatched, bugs_by_project, cache_fp)

    # FP matches found in step 2 → also count as TP (the recall step missed them)
    for pid, info in fp_matches.items():
        bug_id = info.get("bug_id")
        if bug_id and bug_id not in recall_matches:
            recall_matches[bug_id] = {"finding_id": pid, "confidence": info.get("confidence", 0.0)}

    # ── Compute metrics ───────────────────────────────────────────
    detected_bugs = set(recall_matches.keys())
    matched_finding_pids = matched_pids | set(fp_matches.keys())
    fp = total_positive - len(matched_finding_pids)
    tp = len(detected_bugs)

    per_project: dict[str, int] = defaultdict(int)
    bug_type_tp: dict[str, int] = defaultdict(int)
    for bug in bugs:
        if bug["id"] in detected_bugs:
            # Map to canonical project ID
            canonical = None
            for pid, pname in PROJECT_ID_TO_NAME.items():
                if pname == bug["project"]:
                    canonical = CANONICAL_ID.get(pid, pid)
                    break
            if canonical:
                per_project[canonical] += 1
            bug_type_tp[bug["bug_type"]] += 1

    precision = round(tp / (tp + fp) * 100, 2) if (tp + fp) > 0 else 0.0
    recall = round(tp / total_gt * 100, 2) if total_gt > 0 else 0.0
    f1 = round(2 * precision * recall / (precision + recall), 2) if (precision + recall) > 0 else 0.0

    summary = {
        "tp": tp,
        "fp": fp,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "total_ground_truth": total_gt,
        "total_positive_findings": total_positive,
        "total_cost": None,
        "bug_type_breakdown": dict(bug_type_tp),
        "per_project": dict(per_project),
        "detected_bugs": sorted(detected_bugs),
        "missed_bugs": sorted(set(b["id"] for b in bugs) - detected_bugs),
        "matches": {k: v for k, v in recall_matches.items()},
        "llm_model": os.environ.get("RQ2A_MODEL", "haiku"),
    }

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2) + "\n")

    _print_report(summary, bugs)
    return summary


def _empty_summary(bugs: list[dict], total_gt: int, output_path: Path) -> dict:
    summary = {
        "tp": 0, "fp": 0, "precision": 0.0, "recall": 0.0, "f1": 0.0,
        "total_ground_truth": total_gt, "total_positive_findings": 0,
        "total_cost": None, "bug_type_breakdown": {}, "per_project": {},
        "detected_bugs": [], "missed_bugs": sorted(b["id"] for b in bugs),
        "matches": {}, "llm_model": os.environ.get("RQ2A_MODEL", "haiku"),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2) + "\n")
    _print_report(summary, bugs)
    return summary


def _print_report(summary: dict, bugs: list[dict]) -> None:
    print(f"\n{'=' * 50}")
    print("SPECA Evaluation — RQ2a RepoAudit Benchmark")
    print(f"{'=' * 50}")
    print(f"  Model             : {summary.get('llm_model', '?')}")
    print(f"  Ground truth bugs : {summary['total_ground_truth']}")
    print(f"  Positive findings : {summary['total_positive_findings']}")
    print(f"  True Positives    : {summary['tp']}")
    print(f"  False Positives   : {summary['fp']}")
    print(f"  Precision         : {summary['precision']:.2f}%")
    print(f"  Recall            : {summary['recall']:.2f}%")
    print(f"  F1                : {summary['f1']:.2f}%")
    print()
    print("  By bug type:")
    for bt in ("NPD", "MLK", "UAF"):
        count = summary["bug_type_breakdown"].get(bt, 0)
        total = sum(1 for b in bugs if b["bug_type"] == bt)
        print(f"    {bt}: {count}/{total}")
    if summary["missed_bugs"]:
        print()
        print(f"  Missed bugs ({len(summary['missed_bugs'])}):")
        for bid in summary["missed_bugs"]:
            bug = next((b for b in bugs if b["id"] == bid), None)
            desc = bug.get("description", "")[:80] if bug else ""
            proj = bug["project"] if bug else "?"
            print(f"    {bid}: {proj} — {desc}")
    print(f"\n  Summary saved to: {summary.get('_output_path', '(see output)')}")


# ── CLI ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="RQ2a: Evaluate SPECA results (LLM-based)")
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR,
                        help="Directory with SPECA results (project subdirs + 02c files)")
    parser.add_argument("--output", type=Path, default=DEFAULT_SUMMARY_OUT,
                        help="Output path for speca_summary.json")
    parser.add_argument("--reparse", action="store_true",
                        help="Re-parse cached LLM responses without calling LLM")
    parser.add_argument("--update-ground-truth", action="store_true",
                        help="Update ground_truth_bugs.yaml with detection results")
    parser.add_argument("--update-baselines", action="store_true",
                        help="Update published_baselines.yaml with SPECA metrics")
    args = parser.parse_args()

    print("RQ2a Evaluation (LLM-based matching)\n")
    summary = evaluate(args.results_dir, args.output, reparse=args.reparse)

    if args.update_ground_truth:
        update_ground_truth(set(summary["detected_bugs"]))
        print(f"\n  Updated: {GROUND_TRUTH_PATH}")

    if args.update_baselines:
        update_baselines(summary)
        print(f"  Updated: {BASELINES_PATH}")


if __name__ == "__main__":
    main()
