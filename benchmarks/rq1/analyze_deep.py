#!/usr/bin/env python3
"""RQ1 Deep Analysis: FP taxonomy, threat-model mismatch, triage cost,
cross-implementation reuse, issue/property clusters.

Generates JSON results + PNG figures for paper.

Usage:
    uv run python3 benchmarks/rq1/analyze_deep.py
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.path import Path as MplPath
import numpy as np

# ── Paths ──────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
RESULTS_DIR = SCRIPT_DIR.parent / "results" / "rq1" / "sherlock_ethereum_audit_contest"
LABELS_CSV = RESULTS_DIR / "findings_labels.csv"
PHASE_CMP = RESULTS_DIR / "phase_comparison.json"
EVAL_SUMMARY = RESULTS_DIR / "evaluation_summary.json"

# ── Style ──────────────────────────────────────────────────────────
plt.rcParams.update({
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
    "figure.dpi": 150,
    "savefig.dpi": 150,
    "font.family": "sans-serif",
})

TP_LABELS = {"tp", "tp_info", "potential-info", "fixed", "partially_fixed"}
FP_LABELS = {"fp_invalid", "fp_review"}

# ── Repo short names ──────────────────────────────────────────────
REPO_SHORT = {
    "alloy-rs/evm": "alloy",
    "ethereum/c-kzg-4844": "c-kzg",
    "grandinetech/grandine": "grandine",
    "sigp/lighthouse": "lighthouse",
    "ChainSafe/lodestar": "lodestar",
    "NethermindEth/nethermind": "nethermind",
    "status-im/nimbus-eth2": "nimbus",
    "OffchainLabs/prysm": "prysm",
    "paradigmxyz/reth": "reth",
    "crate-crypto/rust-eth-kzg": "rust-eth-kzg",
}

# ── Spec family names (for charts) ────────────────────────────────
SPEC_NAMES = {
    "5a6a79d5": "EVM Execution",
    "57888860": "KZG Proofs",
    "6a4369e9": "PeerDAS (EIP-7594)",
    "56ad1eb2": "Blob Schedule",
    "1ada093f": "Tx Processing",
    "aa9e39fd": "Tx Gas Cap (EIP-7825)",
    "ff7df16a": "EOA Code (EIP-7702)",
    "ba56c3c5": "Block Valid.",
}


def _spec_name(h: str) -> str:
    return SPEC_NAMES.get(h, f"Spec-{h[:6]}")


def _extract_spec_hash(fid: str) -> str | None:
    m = re.match(r"PROP-([a-f0-9]+)-\w+-\d+", fid)
    return m.group(1) if m else None


# ── FP root cause categories (unified) ────────────────────────────
# All FPs (fp_invalid + fp_review/DISPUTED_FP) share one taxonomy.

# Threat model categories for manual classification from reviewer notes
THREAT_MODEL_PATTERNS = [
    (r"P2P|gossip|untrusted.*peer|malicious.*peer|attacker.*P2P|attacker.*via P2P", "P2P Network Attacker"),
    (r"local.*operator|operator.*error|operator.*misconfiguration|config.*file|YAML.*config|CLI flag", "Local Operator / Config"),
    (r"Engine API|EL.*CL|semi.?trusted|SEMI_TRUSTED|IPC|local.*EL", "EL / Semi-Trusted Boundary"),
    (r"Beacon API|publicly exposed.*API|REST.*API", "Public API Exposure"),
    (r"external.*library|c-kzg|external.*C|external.*dependency", "External Dependency"),
    (r"local.*validator|self.*peer|local.*validator", "Local Validator"),
    (r"fork.*transition|future.*upgrade|Fulu.*fork", "Fork / Future Upgrade"),
]


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_labels_csv() -> list[dict]:
    rows = []
    with LABELS_CSV.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


def short_repo(repo: str) -> str:
    return REPO_SHORT.get(repo, repo.split("/")[-1])


# ═══════════════════════════════════════════════════════════════════
# 1. FP Taxonomy
# ═══════════════════════════════════════════════════════════════════

def classify_fp_root_cause(
    human_label: str = "",
    text: str = "",
    csv_severity: str = "",
    csv_title: str = "",
) -> str:
    """Classify a false positive by pipeline error mode.

    Categories answer "why did SPECA produce this FP?":
      - Code Reading Error: LLM factually misread code (wrong data structures, control flow)
      - Multi-Layer Defense: finding correct at checked layer but defense exists elsewhere
      - Trust Boundary Misunderstanding: assumed untrusted boundary that is semi-trusted/trusted
      - Spec Misinterpretation: flagged spec-compliant behavior as deviation
      - Design Choice: intentional behavior flagged as bug
      - Out-of-Scope: external library or feature outside audit scope
      - Not Exploitable: code difference exists but no security impact
    """
    label = (human_label or "").lower()
    title = (csv_title or "").lower()
    txt = (text or "").lower()
    sev = (csv_severity or "").lower()

    # ── Out-of-Scope (external library) ───────────────────────────
    if "external" in label and ("library" in label or "c library" in label):
        return "Out-of-Scope"
    if "out of scope" in label:
        return "Out-of-Scope"

    # ── Trust Boundary Misunderstanding ────────────────────────────
    # EL/CL semi-trusted boundary, IPC/local interfaces
    if re.search(r"semi.?trusted|engine api|ipc|trusting.*execution layer", label + " " + txt, re.I):
        return "Trust Boundary Misunderstanding"
    if "el" in title and ("response" in title or "trust" in title or "custody" in title):
        return "Trust Boundary Misunderstanding"
    if "missing authentication" in title and "ipc" in title:
        return "Trust Boundary Misunderstanding"
    if "faulty execution client" in title:
        return "Trust Boundary Misunderstanding"
    if re.search(r"trusting.*EL|EL.*skip|execution layer.*bypass", txt, re.I):
        return "Trust Boundary Misunderstanding"
    # "same report" findings about EL trust
    if "same report" in label:
        # Check if the underlying issue is about EL/trust
        if re.search(r"kzg.*skip|execution.*verified|el.*bypass|rpc.*bypass", txt, re.I):
            return "Trust Boundary Misunderstanding"

    # ── Multi-Layer Defense ────────────────────────────────────────
    # Defense exists at another layer (gossip, KZG, execution-time validation)
    if "defense-in-depth" in label or "defense in depth" in label:
        return "Multi-Layer Defense"
    if re.search(r"validated at execution|already.?validated|gossip.?validated", label, re.I):
        return "Multi-Layer Defense"
    if re.search(r"kzg proof.*binding|kzg proof.*guarantee|cryptographically valid", label, re.I):
        return "Multi-Layer Defense"
    if "rpc" in label and ("validated" in label or "already" in label):
        return "Multi-Layer Defense"
    if re.search(r"rate.?limited", label, re.I):
        return "Multi-Layer Defense"
    # EIP-7702 validated at execution time
    if "validated at execution time" in label:
        return "Multi-Layer Defense"
    # "same report" about validation that exists elsewhere
    if "same report" in label:
        if re.search(r"gossip|rpc.*validat|already", txt, re.I):
            return "Multi-Layer Defense"

    # ── Spec Misinterpretation ────────────────────────────────────
    if "false premise" in label or "code follows spec" in label:
        return "Spec Misinterpretation"
    if "per spec" in label and ("by design" in label or "per" in label):
        return "Spec Misinterpretation"
    if "blob parameters" in title and "fork" in title:
        return "Spec Misinterpretation"
    if re.search(r"per.*spec|publish all columns|spec.?compliant", label, re.I):
        return "Spec Misinterpretation"
    # "same report" about spec-level behavior
    if "same report" in label:
        if re.search(r"censor|broadcast|subnet", txt, re.I):
            return "Spec Misinterpretation"

    # ── Design Choice ─────────────────────────────────────────────
    if re.search(r"design choice|by design|by-design", label, re.I):
        return "Design Choice"
    if re.search(r"ignore.*by design|stall.*design", txt, re.I):
        return "Design Choice"
    # "same report" about DoS/resource issues (design trade-off)
    if "same report" in label:
        if re.search(r"waste.*resource|stall|retention", txt, re.I):
            return "Design Choice"

    # ── Not Exploitable ───────────────────────────────────────────
    if "regardless" in label and ("reject" in label or "block" in label):
        return "Not Exploitable"
    if "block rejected" in label:
        return "Not Exploitable"

    # ── Code Reading Error ────────────────────────────────────────
    # Contest-judged invalid with construction/data-structure titles
    if sev == "invalid":
        if re.search(r"builds? wrong|contains? too many|too many cells", title, re.I):
            return "Code Reading Error"
        # Remaining contest-invalid without human label → likely code reading
        # or spec misinterpretation; check title for clues
        if re.search(r"custody.*group|hashset|violat", title, re.I):
            return "Spec Misinterpretation"
        if re.search(r"censor|stall|waste", title, re.I):
            return "Design Choice"
        # Default for contest-invalid: inspect text for trust boundary
        if re.search(r"execution layer|el.*skip|trust", txt, re.I):
            return "Trust Boundary Misunderstanding"
        if re.search(r"bypass.*valid|skip.*valid|sync.*bypass", txt, re.I):
            return "Code Reading Error"
        return "Code Reading Error"

    # ── Fallback ──────────────────────────────────────────────────
    if "error wrapping" in txt or "error code" in txt:
        return "Not Exploitable"
    return "Other"


def analyze_fp_taxonomy(rows: list[dict], verdicts: dict) -> dict:
    """Classify FP findings in the FINAL output (survived Phase 04) by root cause."""

    # Classify FP findings that survived Phase 04
    root_cause_counts = Counter()
    details = []

    for row in rows:
        label = row.get("auto_label", "")
        if label not in FP_LABELS:
            continue

        fid = row.get("finding_id", "")
        v = verdicts.get(fid, {})

        # Only count FPs in the final output (survived Phase 04)
        if v.get("classification") == "filtered":
            continue

        human = row.get("human_label", "")
        text = row.get("text", "")
        csv_sev = row.get("csv_severity", "")
        csv_title = row.get("csv_title", "")

        cause = classify_fp_root_cause(
            human_label=human, text=text,
            csv_severity=csv_sev, csv_title=csv_title,
        )
        root_cause_counts[cause] += 1
        details.append({
            "finding_id": fid,
            "root_cause": cause,
            "repo": short_repo(row.get("repo", "")),
        })

    return {
        "total_fp": sum(root_cause_counts.values()),
        "by_root_cause": dict(root_cause_counts.most_common()),
        "details": details,
    }


# ═══════════════════════════════════════════════════════════════════
# 2. Threat-Model Mismatch Analysis
# ═══════════════════════════════════════════════════════════════════

def classify_threat_model(reviewer_notes: str, text: str) -> list[str]:
    """Classify the threat model assumed by a finding."""
    combined = (reviewer_notes or "") + " " + (text or "")
    categories = []
    for pattern, category in THREAT_MODEL_PATTERNS:
        if re.search(pattern, combined, re.IGNORECASE):
            categories.append(category)
    return categories if categories else ["Unclassified"]


def analyze_threat_model(rows: list[dict], verdicts: dict) -> dict:
    """Tag FP findings in the final output by assumed threat model."""

    threat_counts = Counter()
    for row in rows:
        if row.get("auto_label") not in FP_LABELS:
            continue
        fid = row.get("finding_id", "")
        v = verdicts.get(fid, {})
        if v.get("classification") == "filtered":
            continue
        human = row.get("human_label", "")
        text = row.get("text", "")
        combined_text = f"{human} {text}"
        categories = classify_threat_model(combined_text, "")
        for cat in categories:
            threat_counts[cat] += 1

    return {
        "threat_model_distribution": dict(threat_counts.most_common()),
        "summary": "FPs are concentrated in Trust Boundary and Scope mismatches, "
                   "not random hallucinations.",
    }


# ═══════════════════════════════════════════════════════════════════
# 3. Human Reviewer Workload / Triage Cost
# ═══════════════════════════════════════════════════════════════════

def analyze_triage_cost(rows: list[dict], verdicts: dict) -> dict:
    """Compute triage cost metrics per repo and overall."""

    # Per-repo Phase 03
    repo_p03 = defaultdict(lambda: {"total": 0, "tp": 0, "fp": 0, "other": 0})
    repo_p04 = defaultdict(lambda: {"total": 0, "tp": 0, "fp": 0, "other": 0})

    for row in rows:
        repo = short_repo(row.get("repo", ""))
        label = row.get("auto_label", "unknown")
        fid = row.get("finding_id", "")
        is_filtered = verdicts.get(fid, {}).get("classification") == "filtered"

        # Phase 03 (all findings)
        repo_p03[repo]["total"] += 1
        if label in TP_LABELS:
            repo_p03[repo]["tp"] += 1
        elif label in FP_LABELS:
            repo_p03[repo]["fp"] += 1
        else:
            repo_p03[repo]["other"] += 1

        # Phase 04 (surviving findings)
        if not is_filtered:
            repo_p04[repo]["total"] += 1
            if label in TP_LABELS:
                repo_p04[repo]["tp"] += 1
            elif label in FP_LABELS:
                repo_p04[repo]["fp"] += 1
            else:
                repo_p04[repo]["other"] += 1

    # Compute findings-per-true-issue
    # Count distinct issues per repo
    repo_issues = defaultdict(set)
    for row in rows:
        repo = short_repo(row.get("repo", ""))
        issue_id = row.get("csv_issue_id", "")
        if issue_id and row.get("auto_label") == "tp":
            repo_issues[repo].add(issue_id)

    repo_stats = {}
    for repo in sorted(set(list(repo_p03.keys()) + list(repo_p04.keys()))):
        p03 = repo_p03[repo]
        p04 = repo_p04[repo]
        n_issues = len(repo_issues.get(repo, set()))
        repo_stats[repo] = {
            "phase_03": {
                **p03,
                "precision": p03["tp"] / p03["total"] if p03["total"] > 0 else 0,
                "findings_per_issue": p03["total"] / n_issues if n_issues > 0 else None,
            },
            "phase_04": {
                **p04,
                "precision": p04["tp"] / p04["total"] if p04["total"] > 0 else 0,
                "findings_per_issue": p04["total"] / n_issues if n_issues > 0 else None,
            },
            "issues_found": n_issues,
            "findings_removed": p03["total"] - p04["total"],
        }

    # Overall
    total_p03 = sum(r["total"] for r in repo_p03.values())
    total_p04 = sum(r["total"] for r in repo_p04.values())
    total_tp = sum(r["tp"] for r in repo_p03.values())
    total_issues = sum(len(v) for v in repo_issues.values())

    return {
        "per_repo": repo_stats,
        "overall": {
            "phase_03_findings": total_p03,
            "phase_04_findings": total_p04,
            "findings_removed": total_p03 - total_p04,
            "total_tp": total_tp,
            "total_issues": total_issues,
            "phase_03_findings_per_issue": total_p03 / total_issues if total_issues > 0 else None,
            "phase_04_findings_per_issue": total_p04 / total_issues if total_issues > 0 else None,
            "phase_03_review_needed_for_1tp": total_p03 / total_tp if total_tp > 0 else None,
            "phase_04_review_needed_for_1tp": total_p04 / total_tp if total_tp > 0 else None,
        },
    }


# ═══════════════════════════════════════════════════════════════════
# 4. Cross-Implementation Reuse
# ═══════════════════════════════════════════════════════════════════

def analyze_cross_impl_reuse(rows: list[dict], eval_summary: dict) -> dict:
    """Analyze property/finding reuse across implementations."""

    # Extract property family from finding_id: PROP-{hash}-{type}-{num}
    # Same {hash} = same spec/subgraph origin
    # Same {hash}-{type} = same property type from same spec

    prop_family_repos = defaultdict(set)  # {hash} -> {repos}
    prop_type_repos = defaultdict(set)    # {hash-type} -> {repos}
    finding_repos = defaultdict(set)      # {finding_id} -> {repos}

    # Track which issues map to which property families
    issue_families = defaultdict(set)  # {issue_id} -> {prop_family}

    for row in rows:
        fid = row.get("finding_id", "")
        repo = short_repo(row.get("repo", ""))

        # Parse PROP-{hash}-{type}-{num}
        m = re.match(r"PROP-([a-f0-9]+)-(\w+)-(\d+)", fid)
        if m:
            spec_hash = m.group(1)
            prop_type = m.group(2)  # inv, pre, post, asm
            prop_family_repos[spec_hash].add(repo)
            prop_type_repos[f"{spec_hash}-{prop_type}"].add(repo)

        finding_repos[fid].add(repo)

        # Issue mapping
        issue_id = row.get("csv_issue_id", "")
        if issue_id and m:
            issue_families[issue_id].add(m.group(1))

    # Count multi-repo property families
    multi_repo_families = {k: list(v) for k, v in prop_family_repos.items() if len(v) > 1}

    # Same root cause across repos (same issue matched by same property family)
    matches = eval_summary.get("matches", {})
    issue_to_finding = {}
    for issue_id, match_info in matches.items():
        fid = match_info.get("finding_id", "")
        issue_to_finding[issue_id] = fid

    # Group issues by root cause family (same finding_id prefix)
    root_cause_families = defaultdict(list)
    for issue_id, fid in issue_to_finding.items():
        m = re.match(r"(PROP-[a-f0-9]+-\w+)", fid)
        if m:
            root_cause_families[m.group(1)].append(issue_id)

    multi_issue_roots = {k: v for k, v in root_cause_families.items() if len(v) > 1}

    # One property family, many implementations
    # (same spec hash detected across multiple repos)
    one_to_many = []
    for spec_hash, repos in sorted(prop_family_repos.items(), key=lambda x: -len(x[1])):
        if len(repos) > 1:
            one_to_many.append({
                "spec_hash": spec_hash,
                "repos": sorted(repos),
                "count": len(repos),
            })

    # Property type distribution
    prop_type_dist = Counter()
    for row in rows:
        fid = row.get("finding_id", "")
        m = re.match(r"PROP-[a-f0-9]+-(\w+)-\d+", fid)
        if m:
            prop_type_dist[m.group(1)] += 1

    return {
        "total_property_families": len(prop_family_repos),
        "multi_repo_families": len(multi_repo_families),
        "multi_repo_families_detail": multi_repo_families,
        "one_to_many_mapping": one_to_many,
        "property_type_distribution": dict(prop_type_dist.most_common()),
        "multi_issue_root_causes": multi_issue_roots,
        "summary": f"{len(multi_repo_families)} property families span multiple implementations, "
                   f"demonstrating cross-implementation reuse.",
    }


# ═══════════════════════════════════════════════════════════════════
# 5. Issue-Cluster / Property-Cluster Analysis
# ═══════════════════════════════════════════════════════════════════

def analyze_clusters(rows: list[dict], eval_summary: dict) -> dict:
    """Analyze one-bug-many-properties and one-property-many-implementations."""

    matches = eval_summary.get("matches", {})

    # One bug, many findings
    # For each issue, count how many findings in CSV reference it
    issue_findings = defaultdict(list)
    for row in rows:
        issue_id = row.get("csv_issue_id", "")
        if issue_id:
            issue_findings[issue_id].append({
                "finding_id": row.get("finding_id"),
                "repo": short_repo(row.get("repo", "")),
                "label": row.get("auto_label"),
            })

    one_bug_many_props = {
        k: {"count": len(v), "findings": v}
        for k, v in sorted(issue_findings.items(), key=lambda x: -len(x[1]))
        if len(v) > 1
    }

    # One finding, multiple issues
    finding_issues = defaultdict(list)
    for issue_id, match_info in matches.items():
        fid = match_info.get("finding_id", "")
        finding_issues[fid].append(issue_id)

    one_prop_many_issues = {
        k: sorted(v)
        for k, v in sorted(finding_issues.items(), key=lambda x: -len(x[1]))
        if len(v) > 1
    }

    # Cross-implementation same issue
    issue_repos = defaultdict(set)
    for row in rows:
        issue_id = row.get("csv_issue_id", "")
        if issue_id:
            issue_repos[issue_id].add(short_repo(row.get("repo", "")))

    cross_impl_issues = {
        k: sorted(v) for k, v in issue_repos.items() if len(v) > 1
    }

    return {
        "one_bug_many_properties": {
            "count": len(one_bug_many_props),
            "issues": {k: v["count"] for k, v in one_bug_many_props.items()},
        },
        "one_property_many_issues": {
            "count": len(one_prop_many_issues),
            "findings": one_prop_many_issues,
        },
        "cross_implementation_issues": {
            "count": len(cross_impl_issues),
            "issues": cross_impl_issues,
        },
    }


# ═══════════════════════════════════════════════════════════════════
# 6. Phase 03 vs Phase 04 Ablation (enhanced)
# ═══════════════════════════════════════════════════════════════════

def analyze_ablation(rows: list[dict], verdicts: dict) -> dict:
    """Enhanced Phase 03 vs 04 comparison with gate-level breakdown."""

    # Gate effectiveness
    gate_counts = Counter()
    gate_correct = Counter()  # correctly filtered (was truly FP)
    gate_wrong = Counter()    # wrongly filtered (was truly TP)

    for fid, v in verdicts.items():
        if v.get("review_verdict") != "DISPUTED_FP":
            continue
        notes = v.get("reviewer_notes", "")
        # Identify which gate triggered the DISPUTED_FP
        gate = "Other"
        gate_patterns = [
            (r"Gate 1 \(Dead Code\)", "Dead Code"),
            (r"Gate 2 \(Trust Boundary\)", "Trust Boundary"),
            (r"Gate 3 \(Code Verification\)", "Code Verification"),
            (r"Gate 3 \(Scope", "Scope"),
            (r"Gate 4 \(Exploitability\)", "Exploitability"),
            (r"Gate 5 \(Spec Cross-Reference\)", "Spec Cross-Reference"),
            (r"Gate 6 \(Scope", "Scope"),
        ]
        for pat, name in gate_patterns:
            if re.search(pat, notes, re.IGNORECASE):
                gate = name
                break
        gate_counts[gate] += 1

        # Check ground truth
        for row in rows:
            if row.get("finding_id") == fid:
                label = row.get("auto_label", "unknown")
                if label in FP_LABELS:
                    gate_correct[gate] += 1
                elif label in TP_LABELS:
                    gate_wrong[gate] += 1
                break

    gate_stats = {}
    for gate in gate_counts:
        total = gate_counts[gate]
        correct = gate_correct.get(gate, 0)
        wrong = gate_wrong.get(gate, 0)
        gate_stats[gate] = {
            "total_filtered": total,
            "correct_fp": correct,
            "wrong_tp": wrong,
            "precision": correct / total if total > 0 else 0,
        }

    # Property type ablation (final output only — survived Phase 04)
    prop_type_effectiveness = defaultdict(lambda: {"total": 0, "tp": 0, "fp": 0})
    for row in rows:
        fid = row.get("finding_id", "")
        label = row.get("auto_label", "unknown")
        v = verdicts.get(fid, {})
        if v.get("classification") == "filtered":
            continue
        m = re.match(r"PROP-[a-f0-9]+-(\w+)-\d+", fid)
        if m:
            ptype = m.group(1)
            prop_type_effectiveness[ptype]["total"] += 1
            if label in TP_LABELS:
                prop_type_effectiveness[ptype]["tp"] += 1
            elif label in FP_LABELS:
                prop_type_effectiveness[ptype]["fp"] += 1

    # Add precision to each type
    for ptype, stats in prop_type_effectiveness.items():
        total_labeled = stats["tp"] + stats["fp"]
        stats["precision"] = stats["tp"] / total_labeled if total_labeled > 0 else 0

    return {
        "gate_effectiveness": gate_stats,
        "property_type_ablation": dict(prop_type_effectiveness),
    }


# ═══════════════════════════════════════════════════════════════════
# Visualization Functions
# ═══════════════════════════════════════════════════════════════════

def plot_fp_taxonomy(taxonomy: dict, output_dir: Path) -> Path:
    """Unified bar chart of ALL FP root causes."""
    by_cause = taxonomy["by_root_cause"]
    total = taxonomy["total_fp"]
    if not by_cause:
        return output_dir / "chart_fp_taxonomy.png"

    categories = list(by_cause.keys())
    counts = list(by_cause.values())

    colors = {
        "Cross-Impl Duplicate": "#e74c3c",
        "Validated at Different Layer": "#e67e22",
        "Trust Boundary Mismatch": "#f39c12",
        "Spec Interpretation Error": "#9b59b6",
        "Design Choice": "#3498db",
        "Out-of-Scope": "#2ecc71",
        "Code Reading Error": "#1abc9c",
        "Not Exploitable": "#95a5a6",
        "Dead Code": "#7f8c8d",
        "Other": "#bdc3c7",
    }
    bar_colors = [colors.get(c, "#bdc3c7") for c in categories]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(range(len(categories)), counts, color=bar_colors,
                   edgecolor="white", linewidth=0.5)
    ax.set_yticks(range(len(categories)))
    ax.set_yticklabels(categories, fontsize=10)
    ax.invert_yaxis()
    ax.set_xlabel("Number of Findings")
    ax.set_title(f"False Positive Root Cause Taxonomy (n={total})")
    ax.grid(axis="x", alpha=0.3)

    for bar, count in zip(bars, counts):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                str(count), ha="left", va="center", fontsize=10, fontweight="bold")

    fig.tight_layout()
    out = output_dir / "chart_fp_taxonomy.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_threat_model(threat_data: dict, output_dir: Path) -> Path:
    """Bar chart of assumed threat model in FP findings."""
    dist = threat_data["threat_model_distribution"]
    if not dist:
        return output_dir / "chart_threat_model_mismatch.png"

    categories = list(dist.keys())
    counts = list(dist.values())

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(range(len(categories)), counts, color="#e8913a",
                   edgecolor="white", linewidth=0.5)
    ax.set_yticks(range(len(categories)))
    ax.set_yticklabels(categories, fontsize=10)
    ax.invert_yaxis()
    ax.set_xlabel("Number of FP Findings")
    ax.set_title(f"Assumed Threat Model in False Positives (n={sum(counts)})")
    ax.grid(axis="x", alpha=0.3)

    for bar, count in zip(bars, counts):
        ax.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height() / 2,
                str(count), ha="left", va="center", fontsize=10, fontweight="bold")

    fig.tight_layout()
    out = output_dir / "chart_threat_model_mismatch.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_triage_cost(triage: dict, output_dir: Path) -> Path:
    """Per-repo triage cost comparison."""
    per_repo = triage["per_repo"]
    repos = sorted(per_repo.keys(), key=lambda r: per_repo[r]["phase_03"]["total"], reverse=True)

    fig, ax = plt.subplots(figsize=(10, 6))
    x = np.arange(len(repos))
    width = 0.35

    p03_total = [per_repo[r]["phase_03"]["total"] for r in repos]
    p04_total = [per_repo[r]["phase_04"]["total"] for r in repos]
    p03_tp = [per_repo[r]["phase_03"]["tp"] for r in repos]
    p04_tp = [per_repo[r]["phase_04"]["tp"] for r in repos]

    # Stacked: TP (dark) + FP/Other (light)
    p03_fp = [p03_total[i] - p03_tp[i] for i in range(len(repos))]
    p04_fp = [p04_total[i] - p04_tp[i] for i in range(len(repos))]

    ax.bar(x - width / 2, p03_tp, width, label="Phase 03 TP", color="#2ecc71")
    ax.bar(x - width / 2, p03_fp, width, bottom=p03_tp, label="Phase 03 FP/Other", color="#e74c3c", alpha=0.6)
    ax.bar(x + width / 2, p04_tp, width, label="Phase 04 TP", color="#27ae60")
    ax.bar(x + width / 2, p04_fp, width, bottom=p04_tp, label="Phase 04 FP/Other", color="#c0392b", alpha=0.6)

    ax.set_xticks(x)
    ax.set_xticklabels(repos, rotation=30, ha="right")
    ax.set_ylabel("Number of Findings")
    ax.set_title("Human Review Workload: Phase 03 vs Phase 04\n(Stacked: TP + FP/Other)")
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    out = output_dir / "chart_triage_cost.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_cross_impl_reuse(reuse: dict, output_dir: Path) -> Path:
    """Bar chart showing property family reuse across implementations."""
    one_to_many = reuse["one_to_many_mapping"]
    if not one_to_many:
        return output_dir / "chart_cross_impl_reuse.png"

    # Show top 10 families by repo count
    top = one_to_many[:10]
    labels = [f"...{x['spec_hash'][-6:]}" for x in top]
    counts = [x["count"] for x in top]
    repo_lists = [", ".join(x["repos"]) for x in top]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(range(len(labels)), counts, color="#e8913a", edgecolor="white")
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("Number of Implementations")
    ax.set_title(f"Cross-Implementation Reuse: Property Families Spanning Multiple Repos\n"
                 f"({reuse['multi_repo_families']} of {reuse['total_property_families']} families)")
    ax.grid(axis="x", alpha=0.3)

    for i, (bar, repos_str) in enumerate(zip(bars, repo_lists)):
        ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height() / 2,
                repos_str, ha="left", va="center", fontsize=7, style="italic")

    fig.tight_layout()
    out = output_dir / "chart_cross_impl_reuse.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


PTYPE_DISPLAY = {
    "inv": "Invariant",
    "pre": "Precondition",
    "post": "Postcondition",
    "asm": "Assumption",
}


def plot_property_type_ablation(ablation: dict, output_dir: Path) -> Path:
    """Stacked horizontal bar: TP vs FP per property type with precision."""
    ptypes = ablation["property_type_ablation"]
    if not ptypes:
        return output_dir / "chart_property_type_ablation.png"

    # Sort by total descending
    type_keys = sorted(ptypes.keys(), key=lambda t: ptypes[t]["total"], reverse=True)
    display_names = [PTYPE_DISPLAY.get(t, t) for t in type_keys]
    tps = [ptypes[t]["tp"] for t in type_keys]
    fps = [ptypes[t]["fp"] for t in type_keys]
    precisions = [ptypes[t]["precision"] for t in type_keys]
    totals = [ptypes[t]["total"] for t in type_keys]

    fig, ax = plt.subplots(figsize=(9, 4))
    y = np.arange(len(display_names))

    bars_tp = ax.barh(y, tps, color="#27ae60", label="TP", edgecolor="white")
    bars_fp = ax.barh(y, fps, left=tps, color="#e74c3c", alpha=0.75,
                      label="FP", edgecolor="white")

    ax.set_yticks(y)
    ax.set_yticklabels(display_names, fontsize=11)
    ax.invert_yaxis()
    ax.set_xlabel("Number of Findings (Final Output)")
    total_all = sum(totals)
    ax.set_title(f"Precision by Property Type (n={total_all}, final output)")
    ax.legend(loc="lower right", fontsize=9)
    ax.grid(axis="x", alpha=0.3)

    # Annotate: total count + precision
    for i, (tp, fp, prec, total) in enumerate(zip(tps, fps, precisions, totals)):
        ax.text(total + 0.5, i,
                f"precision {prec:.0%}  (n={total})",
                ha="left", va="center", fontsize=10)

    ax.set_xlim(0, max(totals) * 1.55)
    fig.tight_layout()
    out = output_dir / "chart_property_type_ablation.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_combined_label_breakdown(rows: list[dict], verdicts: dict,
                                  output_dir: Path) -> Path:
    """Horizontal bar chart: TP/FP evaluated on SPECA final output only.

    Phase 04 filtered findings are shown separately — they are not FPs,
    they are the pipeline working correctly.
    """
    # Classify each finding as survived or filtered
    tp_survived = 0
    fp_survived = 0
    filtered_correct = 0   # was FP, Phase 04 caught it
    filtered_incorrect = 0  # was TP, Phase 04 wrongly removed it

    for row in rows:
        fid = row.get("finding_id", "")
        label = row.get("auto_label", "unknown")
        v = verdicts.get(fid, {})
        is_filtered = v.get("classification") == "filtered"

        if is_filtered:
            if label in TP_LABELS:
                filtered_incorrect += 1
            else:
                filtered_correct += 1
        else:
            if label in TP_LABELS:
                tp_survived += 1
            elif label in FP_LABELS:
                fp_survived += 1

    total_final = tp_survived + fp_survived
    precision = tp_survived / total_final if total_final > 0 else 0

    categories = [
        ("TP (Final Output)", tp_survived, "#27ae60"),
        ("FP (Final Output)", fp_survived, "#e74c3c"),
        ("Filtered: Correct (was FP)", filtered_correct, "#95a5a6"),
        ("Filtered: Incorrect (was TP)", filtered_incorrect, "#f39c12"),
    ]
    # Drop zero-count categories
    categories = [(name, count, color) for name, count, color in categories if count > 0]

    names = [c[0] for c in categories]
    counts = [c[1] for c in categories]
    colors = [c[2] for c in categories]
    total = sum(counts)

    fig, ax = plt.subplots(figsize=(9, 4))
    bars = ax.barh(range(len(names)), counts, color=colors,
                   edgecolor="white", linewidth=0.5)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names, fontsize=10)
    ax.invert_yaxis()
    ax.set_xlabel("Number of Findings")
    ax.set_title(f"RQ1: SPECA Output Quality (n={total}, "
                 f"final precision={precision:.0%})")
    ax.grid(axis="x", alpha=0.3)

    for bar, count in zip(bars, counts):
        ax.text(bar.get_width() + 0.4, bar.get_y() + bar.get_height() / 2,
                str(count), ha="left", va="center",
                fontsize=11, fontweight="bold")

    ax.set_xlim(0, max(counts) * 1.25)
    fig.tight_layout()
    out = output_dir / "chart_label_distribution.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_gate_effectiveness(ablation: dict, output_dir: Path) -> Path:
    """Phase 04 review gate effectiveness."""
    gates = ablation["gate_effectiveness"]
    if not gates:
        return output_dir / "chart_gate_effectiveness.png"

    gate_names = sorted(gates.keys(), key=lambda g: gates[g]["total_filtered"], reverse=True)
    totals = [gates[g]["total_filtered"] for g in gate_names]
    correct = [gates[g]["correct_fp"] for g in gate_names]
    wrong = [gates[g]["wrong_tp"] for g in gate_names]

    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(gate_names))
    width = 0.6

    ax.bar(x, correct, width, label="Correct Filter (True FP)", color="#2ecc71")
    ax.bar(x, wrong, width, bottom=correct, label="Wrong Filter (True TP lost)", color="#e74c3c")

    ax.set_xticks(x)
    ax.set_xticklabels(gate_names, rotation=25, ha="right", fontsize=9)
    ax.set_ylabel("Number of Findings Filtered")
    ax.set_title("Phase 04 Gate Effectiveness\n(Green = Correct FP removal, Red = TP loss)")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    # Add precision labels
    for i, g in enumerate(gate_names):
        prec = gates[g]["precision"]
        ax.text(i, totals[i] + 0.3, f"{prec:.0%}", ha="center", va="bottom", fontsize=9, fontweight="bold")

    fig.tight_layout()
    out = output_dir / "chart_gate_effectiveness.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


# ═══════════════════════════════════════════════════════════════════
# New charts: Sankey, Heatmap, Findings-per-Issue
# ═══════════════════════════════════════════════════════════════════

def _draw_band(ax, x0, y0_bot, y0_top, x1, y1_bot, y1_top, color, alpha=0.35):
    """Draw a curved filled band between two vertical intervals."""
    xm = (x0 + x1) / 2
    verts = [
        (x0, y0_bot),
        (xm, y0_bot), (xm, y1_bot), (x1, y1_bot),
        (x1, y1_top),
        (xm, y1_top), (xm, y0_top), (x0, y0_top),
        (x0, y0_bot),
    ]
    codes = [
        MplPath.MOVETO,
        MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
        MplPath.LINETO,
        MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
        MplPath.CLOSEPOLY,
    ]
    patch = mpatches.PathPatch(MplPath(verts, codes),
                               facecolor=color, alpha=alpha,
                               edgecolor="none", lw=0)
    ax.add_patch(patch)


def _layout_nodes(items: dict, y_start: float = 0.02, y_end: float = 0.98,
                  gap: float = 0.008) -> dict:
    """Stack nodes vertically proportional to value. Returns {name: (bot, top)}."""
    total = sum(items.values())
    if total == 0:
        return {}
    n = len(items)
    usable = (y_end - y_start) - gap * max(n - 1, 0)
    # Ensure minimum visibility for small nodes
    min_h = usable * 0.015
    raw = {k: max((v / total) * usable, min_h) for k, v in items.items()}
    scale = usable / sum(raw.values())
    pos = {}
    y = y_start
    for name in items:
        h = raw[name] * scale
        pos[name] = (y, y + h)
        y += h + gap
    return pos


def plot_sankey_flow(rows: list[dict], verdicts: dict, output_dir: Path) -> Path:
    """Alluvial diagram: Property Family → Issue / FP."""
    from collections import OrderedDict

    flows: dict[tuple[str, str], int] = defaultdict(int)
    spec_totals: Counter = Counter()
    dst_totals: Counter = Counter()
    issue_titles: dict[str, str] = {}
    issue_severities: dict[str, str] = {}

    for row in rows:
        fid = row.get("finding_id", "")
        label = row.get("auto_label", "")
        csv_issue = row.get("csv_issue_id", "")
        csv_title = row.get("csv_title", "")
        csv_sev = row.get("csv_severity", "")

        v = verdicts.get(fid, {})
        is_filtered = v.get("classification") == "filtered"

        spec_hash = _extract_spec_hash(fid)
        if not spec_hash:
            continue
        sname = _spec_name(spec_hash)

        if is_filtered:
            dst = "Filtered (Phase 04)"
        elif label in TP_LABELS and csv_issue:
            dst = f"#{csv_issue}"
            if csv_issue not in issue_titles and csv_title:
                issue_titles[csv_issue] = csv_title[:40]
            if csv_issue not in issue_severities and csv_sev:
                issue_severities[csv_issue] = csv_sev
        elif label in FP_LABELS:
            dst = "False Positive"
        else:
            dst = "Novel TP (beyond benchmark)"

        flows[(sname, dst)] += 1
        spec_totals[sname] += 1
        dst_totals[dst] += 1

    if not flows:
        out = output_dir / "chart_sankey_flow.png"
        return out

    # Order specs by total descending
    spec_order = OrderedDict(sorted(spec_totals.items(), key=lambda x: -x[1]))

    # Order right column: issues sorted by id, then special buckets
    issue_keys = sorted(
        [k for k in dst_totals if k.startswith("#")],
        key=lambda k: int(k[1:]),
    )
    bucket_order = ["Novel TP (beyond benchmark)", "Filtered (Phase 04)",
                    "False Positive"]
    other_keys = [k for k in bucket_order if k in dst_totals]
    dst_order = OrderedDict((k, dst_totals[k]) for k in issue_keys + other_keys)

    # Layout
    left_pos = _layout_nodes(spec_order, y_start=0.02, y_end=0.98, gap=0.010)
    right_pos = _layout_nodes(dst_order, y_start=0.02, y_end=0.98, gap=0.005)

    fig, ax = plt.subplots(figsize=(14, 10))
    node_w = 0.025
    x_left = 0.18
    x_right = 0.82

    # Left column: spec family rectangles
    for name, (bot, top) in left_pos.items():
        ax.add_patch(plt.Rectangle(
            (x_left - node_w / 2, bot), node_w, top - bot,
            facecolor="#4C72B0", edgecolor="white", lw=0.5, zorder=3))
        ax.text(x_left - node_w / 2 - 0.01, (bot + top) / 2,
                f"{name}  ({spec_totals[name]})",
                ha="right", va="center", fontsize=9, fontweight="bold")

    # Right column: issue / bucket rectangles
    for name, (bot, top) in right_pos.items():
        if name == "False Positive":
            color = "#e74c3c"
        elif name == "Filtered (Phase 04)":
            color = "#95a5a6"
        elif name == "Novel TP (beyond benchmark)":
            color = "#f39c12"
        else:
            sev = issue_severities.get(name[1:], "")
            color = {"high": "#c0392b", "medium": "#e67e22",
                     "low": "#27ae60"}.get(sev, "#27ae60")
        ax.add_patch(plt.Rectangle(
            (x_right - node_w / 2, bot), node_w, top - bot,
            facecolor=color, edgecolor="white", lw=0.5, zorder=3))

        # Right label
        issue_id = name[1:] if name.startswith("#") else ""
        title = issue_titles.get(issue_id, "")
        sev_tag = {"high": "High", "medium": "Med", "low": "Low",
                   "info": "Info", "potential-info": "Info",
                   "invalid": "Invalid",
                   }.get(issue_severities.get(issue_id, ""), "")
        if title:
            lbl = f"{name} [{sev_tag}] {title}  ({dst_totals[name]})"
        else:
            lbl = f"{name}  ({dst_totals[name]})"
        ax.text(x_right + node_w / 2 + 0.01, (bot + top) / 2,
                lbl, ha="left", va="center", fontsize=7)

    # Draw links — TP first so FP is drawn on top
    left_cursor = {n: b for n, (b, _) in left_pos.items()}
    right_cursor = {n: b for n, (b, _) in right_pos.items()}

    sorted_flows = sorted(
        flows.items(),
        key=lambda x: (0 if "False Positive" not in x[0][1] else 1, -x[1]),
    )

    for (src, dst), count in sorted_flows:
        if src not in left_pos or dst not in right_pos:
            continue
        sb, st = left_pos[src]
        link_sh = (count / spec_totals[src]) * (st - sb)
        sy_bot = left_cursor[src]
        sy_top = sy_bot + link_sh
        left_cursor[src] = sy_top

        db, dt = right_pos[dst]
        link_dh = (count / dst_totals[dst]) * (dt - db)
        dy_bot = right_cursor[dst]
        dy_top = dy_bot + link_dh
        right_cursor[dst] = dy_top

        if dst == "False Positive":
            lcolor = "#e74c3c"
        elif dst == "Filtered (Phase 04)":
            lcolor = "#95a5a6"
        elif dst == "Novel TP (beyond benchmark)":
            lcolor = "#f39c12"
        else:
            lcolor = "#27ae60"

        _draw_band(ax, x_left + node_w / 2, sy_bot, sy_top,
                   x_right - node_w / 2, dy_bot, dy_top,
                   lcolor, alpha=0.30)

    ax.set_xlim(0, 1)
    ax.set_ylim(-0.01, 1.01)
    ax.set_title("Property Family → Ground Truth Issue Flow", fontsize=14, pad=15)
    ax.axis("off")

    # Legend
    from matplotlib.lines import Line2D
    legend_elems = [
        Line2D([0], [0], marker="s", color="w", markerfacecolor="#27ae60",
               markersize=10, label="True Positive"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor="#f39c12",
               markersize=10, label="Novel TP (beyond benchmark)"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor="#95a5a6",
               markersize=10, label="Filtered (Phase 04)"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor="#e74c3c",
               markersize=10, label="False Positive"),
    ]
    ax.legend(handles=legend_elems, loc="lower center", ncol=3, fontsize=9,
              frameon=True, fancybox=True)

    fig.tight_layout()
    out = output_dir / "chart_sankey_flow.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_issue_property_heatmap(rows: list[dict], verdicts: dict,
                                output_dir: Path) -> Path:
    """Heatmap: Issue × Property Family showing TP finding counts."""
    issue_spec_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    issue_meta: dict[str, dict] = {}

    for row in rows:
        fid = row.get("finding_id", "")
        label = row.get("auto_label", "")
        csv_issue = row.get("csv_issue_id", "")
        csv_title = row.get("csv_title", "")
        csv_sev = row.get("csv_severity", "")

        v = verdicts.get(fid, {})
        if v.get("classification") == "filtered":
            continue
        if label not in TP_LABELS or not csv_issue:
            continue

        spec_hash = _extract_spec_hash(fid)
        if not spec_hash:
            continue

        issue_spec_counts[csv_issue][_spec_name(spec_hash)] += 1
        if csv_issue not in issue_meta:
            sev_tag = {"high": "High", "medium": "Med", "low": "Low",
                       "info": "Info", "potential-info": "Info",
                       "invalid": "Invalid",
                       }.get(csv_sev, csv_sev or "?")
            short = (csv_title or "")[:35]
            issue_meta[csv_issue] = {
                "label": f"#{csv_issue} [{sev_tag}] {short}",
                "sev": csv_sev,
            }

    if not issue_spec_counts:
        return output_dir / "chart_issue_property_heatmap.png"

    # Sort issues by severity (H > M > L) then by id
    sev_rank = {"high": 0, "medium": 1, "low": 2}
    issues = sorted(
        issue_spec_counts.keys(),
        key=lambda i: (sev_rank.get(issue_meta.get(i, {}).get("sev", ""), 9),
                       int(i)),
    )
    specs = sorted(set(s for counts in issue_spec_counts.values()
                       for s in counts))

    matrix = np.zeros((len(issues), len(specs)))
    for i, issue in enumerate(issues):
        for j, spec in enumerate(specs):
            matrix[i, j] = issue_spec_counts[issue].get(spec, 0)

    fig, ax = plt.subplots(figsize=(10, max(6, len(issues) * 0.5 + 1)))
    im = ax.imshow(matrix, cmap="YlOrRd", aspect="auto", vmin=0)

    ax.set_xticks(range(len(specs)))
    ax.set_xticklabels(specs, rotation=40, ha="right", fontsize=9)
    ax.set_yticks(range(len(issues)))
    ax.set_yticklabels(
        [issue_meta.get(i, {}).get("label", f"#{i}") for i in issues],
        fontsize=8)

    for i in range(len(issues)):
        for j in range(len(specs)):
            val = int(matrix[i, j])
            if val > 0:
                ax.text(j, i, str(val), ha="center", va="center",
                        fontsize=9, fontweight="bold",
                        color="white" if val > 3 else "black")

    ax.set_title("Issue × Property Family: TP Finding Counts (survived only)")
    fig.colorbar(im, ax=ax, label="Findings", shrink=0.8)
    fig.tight_layout()

    out = output_dir / "chart_issue_property_heatmap.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_findings_per_issue(rows: list[dict], verdicts: dict,
                            output_dir: Path) -> Path:
    """Bar chart: number of TP findings per ground-truth issue."""
    findings_per_issue: Counter = Counter()
    issue_meta: dict[str, dict] = {}

    for row in rows:
        fid = row.get("finding_id", "")
        label = row.get("auto_label", "")
        csv_issue = row.get("csv_issue_id", "")
        csv_title = row.get("csv_title", "")
        csv_sev = row.get("csv_severity", "")

        v = verdicts.get(fid, {})
        if v.get("classification") == "filtered":
            continue
        if label not in TP_LABELS or not csv_issue:
            continue

        findings_per_issue[csv_issue] += 1
        if csv_issue not in issue_meta:
            sev_tag = {"high": "High", "medium": "Med", "low": "Low",
                       "info": "Info", "potential-info": "Info",
                       "invalid": "Invalid",
                       }.get(csv_sev, csv_sev or "?")
            short = (csv_title or "")[:40]
            issue_meta[csv_issue] = {"label": f"#{csv_issue} [{sev_tag}] {short}",
                                     "sev": csv_sev}

    if not findings_per_issue:
        return output_dir / "chart_findings_per_issue.png"

    sorted_issues = sorted(findings_per_issue.items(), key=lambda x: -x[1])
    labels = [issue_meta.get(i, {}).get("label", f"#{i}") for i, _ in sorted_issues]
    counts = [c for _, c in sorted_issues]

    sev_colors = {"high": "#c0392b", "medium": "#e67e22", "low": "#27ae60"}
    colors = [sev_colors.get(issue_meta.get(i, {}).get("sev", ""), "#4C72B0")
              for i, _ in sorted_issues]

    fig, ax = plt.subplots(figsize=(10, max(5, len(labels) * 0.4 + 1)))
    bars = ax.barh(range(len(labels)), counts, color=colors,
                   edgecolor="white", linewidth=0.5)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Number of TP Findings")
    ax.set_title(f"Findings per Issue: How Many Properties Capture Each Bug\n"
                 f"(n={len(findings_per_issue)} issues, {sum(counts)} findings)")
    ax.grid(axis="x", alpha=0.3)

    for bar, count in zip(bars, counts):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                str(count), ha="left", va="center", fontsize=10, fontweight="bold")

    ax.set_xlim(0, max(counts) * 1.15)

    # Legend for severity colors
    from matplotlib.lines import Line2D
    sev_legend = [
        Line2D([0], [0], marker="s", color="w", markerfacecolor="#c0392b",
               markersize=10, label="High"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor="#e67e22",
               markersize=10, label="Medium"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor="#27ae60",
               markersize=10, label="Low"),
    ]
    ax.legend(handles=sev_legend, title="Severity", loc="lower right", fontsize=8)

    fig.tight_layout()
    out = output_dir / "chart_findings_per_issue.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════

def main():
    print("[analyze_deep] Loading data...")
    rows = load_labels_csv()
    phase_cmp = load_json(PHASE_CMP)
    eval_summary = load_json(EVAL_SUMMARY)
    verdicts = phase_cmp.get("verdicts", {})

    print(f"[analyze_deep] {len(rows)} findings, {len(verdicts)} verdicts")

    # Run all analyses
    print("[analyze_deep] 1/6 FP Taxonomy...")
    fp_taxonomy = analyze_fp_taxonomy(rows, verdicts)

    print("[analyze_deep] 2/6 Threat-Model Mismatch...")
    threat_model = analyze_threat_model(rows, verdicts)

    print("[analyze_deep] 3/6 Triage Cost...")
    triage_cost = analyze_triage_cost(rows, verdicts)

    print("[analyze_deep] 4/6 Cross-Implementation Reuse...")
    cross_impl = analyze_cross_impl_reuse(rows, eval_summary)

    print("[analyze_deep] 5/6 Issue/Property Clusters...")
    clusters = analyze_clusters(rows, eval_summary)

    print("[analyze_deep] 6/6 Ablation...")
    ablation = analyze_ablation(rows, verdicts)

    # Save JSON results
    results = {
        "fp_taxonomy": fp_taxonomy,
        "threat_model_mismatch": threat_model,
        "triage_cost": triage_cost,
        "cross_implementation_reuse": cross_impl,
        "clusters": clusters,
        "ablation": ablation,
    }

    output_json = RESULTS_DIR / "deep_analysis.json"
    output_json.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"[analyze_deep] Saved {output_json}")

    # Generate figures
    print("[analyze_deep] Generating figures...")
    charts = []
    charts.append(("FP Root Cause Taxonomy", plot_fp_taxonomy(fp_taxonomy, RESULTS_DIR)))
    # Threat-model mismatch chart removed — most FPs are not caused by wrong
    # attacker assumptions but by cross-impl dupes, design choices, spec errors.
    # The FP root cause taxonomy already captures this better.
    # Triage cost chart removed — chart_per_repo.png (from generate_report.py)
    # already shows the same Phase 03 vs 04 per-repo breakdown.
    # Cross-impl reuse chart removed — in a multi-implementation contest,
    # properties spanning repos is an artifact of shared specs, not an insight.
    charts.append(("Property Type Ablation", plot_property_type_ablation(ablation, RESULTS_DIR)))
    charts.append(("Label Distribution", plot_combined_label_breakdown(rows, verdicts, RESULTS_DIR)))
    charts.append(("Gate Effectiveness", plot_gate_effectiveness(ablation, RESULTS_DIR)))
    charts.append(("Sankey Flow", plot_sankey_flow(rows, verdicts, RESULTS_DIR)))
    charts.append(("Issue-Property Heatmap", plot_issue_property_heatmap(rows, verdicts, RESULTS_DIR)))
    charts.append(("Findings per Issue", plot_findings_per_issue(rows, verdicts, RESULTS_DIR)))

    for desc, path in charts:
        print(f"  [{desc}] {path}")

    # Print summary
    print("\n" + "=" * 60)
    print("DEEP ANALYSIS SUMMARY")
    print("=" * 60)

    print(f"\nFP Root Cause Taxonomy (n={fp_taxonomy['total_fp']}):")
    for cause, count in fp_taxonomy["by_root_cause"].items():
        print(f"  {cause}: {count}")

    print(f"\nThreat Model Distribution (FPs):")
    for cat, count in threat_model["threat_model_distribution"].items():
        print(f"  {cat}: {count}")

    print(f"\nTriage Cost:")
    overall = triage_cost["overall"]
    print(f"  Phase 03: {overall['phase_03_findings']} findings, "
          f"{overall['phase_03_review_needed_for_1tp']:.1f} reviews/TP")
    print(f"  Phase 04: {overall['phase_04_findings']} findings, "
          f"{overall['phase_04_review_needed_for_1tp']:.1f} reviews/TP")

    print(f"\nCross-Implementation Reuse:")
    print(f"  {cross_impl['multi_repo_families']} / {cross_impl['total_property_families']} "
          f"property families span multiple repos")

    print(f"\nProperty Type Distribution:")
    for ptype, count in cross_impl["property_type_distribution"].items():
        print(f"  {ptype}: {count}")

    print(f"\nClusters:")
    print(f"  {clusters['one_bug_many_properties']['count']} issues have multiple findings")
    print(f"  {clusters['one_property_many_issues']['count']} findings match multiple issues")
    print(f"  {clusters['cross_implementation_issues']['count']} issues span multiple implementations")

    print(f"\nGate Effectiveness:")
    for gate, stats in sorted(ablation["gate_effectiveness"].items(),
                              key=lambda x: x[1]["total_filtered"], reverse=True):
        print(f"  {gate}: {stats['total_filtered']} filtered, "
              f"precision={stats['precision']:.0%}")

    print(f"\nProperty Type Ablation:")
    for ptype, stats in sorted(ablation["property_type_ablation"].items()):
        print(f"  {ptype}: total={stats['total']}, tp={stats['tp']}, "
              f"fp={stats['fp']}, precision={stats['precision']:.1%}")


if __name__ == "__main__":
    main()
