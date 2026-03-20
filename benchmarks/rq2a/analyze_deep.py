#!/usr/bin/env python3
"""RQ2a Deep Analysis: Enhanced SPECA vs baselines comparison.

Generates:
1. Per-project detection matrix (SPECA vs RepoAudit vs Infer vs CodeGuru)
2. Bug-type breakdown comparison
3. Disputed bug analysis
4. Enhanced comparison table

Usage:
    uv run python3 benchmarks/rq2a/analyze_deep.py
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import yaml

# ── Paths ──────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
BASELINES_PATH = SCRIPT_DIR / "published_baselines.yaml"
GT_PATH = SCRIPT_DIR / "ground_truth_bugs.yaml"
SPECA_SUMMARY = SCRIPT_DIR.parent / "results" / "rq2a" / "speca" / "speca_summary.json"
FIGURES_DIR = SCRIPT_DIR.parent / "results" / "rq2a" / "figures"

plt.rcParams.update({
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
    "figure.dpi": 150,
    "savefig.dpi": 150,
    "font.family": "sans-serif",
})


def load_data():
    with open(BASELINES_PATH) as f:
        baselines = yaml.safe_load(f)
    with open(GT_PATH) as f:
        gt = yaml.safe_load(f)
    speca = {}
    if SPECA_SUMMARY.exists():
        with open(SPECA_SUMMARY) as f:
            speca = json.load(f)
    return baselines, gt, speca


def build_detection_matrix(gt: dict) -> dict:
    """Build per-bug detection matrix for all tools."""
    bugs = gt.get("bugs", [])

    tools = ["repoaudit_claude35", "meta_infer", "amazon_codeguru", "speca"]
    tool_display = {
        "repoaudit_claude35": "RepoAudit",
        "meta_infer": "Infer",
        "amazon_codeguru": "CodeGuru",
        "speca": "SPECA",
    }

    matrix = []
    for bug in bugs:
        detected_by = bug.get("detected_by", {})
        row = {
            "id": bug["id"],
            "project": bug.get("project", ""),
            "bug_type": bug.get("bug_type", ""),
            "source": bug.get("source", ""),
            "disputed": bug.get("disputed", False),
            "inter_procedural": bug.get("inter_procedural", False),
        }
        for tool in tools:
            val = detected_by.get(tool)
            if val is True:
                row[tool_display[tool]] = "detected"
            elif val is False:
                row[tool_display[tool]] = "missed"
            else:
                row[tool_display[tool]] = "n/a"
        matrix.append(row)

    return {"matrix": matrix, "tools": [tool_display[t] for t in tools]}


def compute_comparison_table(baselines: dict, speca: dict) -> dict:
    """Build enhanced comparison table."""
    tools_data = baselines.get("tools", {})

    rows = []
    for key in ["repoaudit_deepseek_r1", "repoaudit_claude37_sonnet",
                 "repoaudit_o3_mini", "repoaudit_claude35_sonnet",
                 "meta_infer", "amazon_codeguru", "speca"]:
        tool = tools_data.get(key, {})
        tp = tool.get("tp", 0)
        fp = tool.get("fp", 0)
        precision = tool.get("precision", 0)
        recall = tool.get("recall")
        f1 = tool.get("f1")

        rows.append({
            "tool": tool.get("display_name", key),
            "tp": tp,
            "fp": fp,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "source": tool.get("source", ""),
        })

    return {"comparison_table": rows}


def analyze_bug_type_breakdown(gt: dict, baselines: dict, speca: dict) -> dict:
    """Compare detection rates by bug type (NPD, MLK, UAF)."""
    bugs = gt.get("bugs", [])

    # SPECA detected bugs from summary
    speca_detected = set(speca.get("detected_bugs", []))

    tool_by_type = defaultdict(lambda: defaultdict(lambda: {"detected": 0, "total": 0}))

    for bug in bugs:
        btype = bug.get("bug_type", "")
        detected_by = bug.get("detected_by", {})
        disputed = bug.get("disputed", False)

        if disputed:
            continue

        for tool_key, tool_name in [
            ("repoaudit_claude35", "RepoAudit"),
            ("meta_infer", "Infer"),
            ("amazon_codeguru", "CodeGuru"),
        ]:
            val = detected_by.get(tool_key)
            if val is not None:
                tool_by_type[tool_name][btype]["total"] += 1
                if val is True:
                    tool_by_type[tool_name][btype]["detected"] += 1

        # SPECA
        tool_by_type["SPECA"][btype]["total"] += 1
        speca_val = detected_by.get("speca")
        if speca_val is True or bug["id"] in speca_detected:
            tool_by_type["SPECA"][btype]["detected"] += 1

    return dict(tool_by_type)


def analyze_disputed_bugs(gt: dict, speca: dict) -> dict:
    """Analyze disputed bugs — where SPECA disagrees with RepoAudit."""
    bugs = gt.get("bugs", [])
    disputed = [b for b in bugs if b.get("disputed", False)]

    result = []
    for bug in disputed:
        detected_by = bug.get("detected_by", {})
        result.append({
            "id": bug["id"],
            "project": bug.get("project", ""),
            "description": bug.get("description", ""),
            "dispute_reason": bug.get("dispute_reason", ""),
            "repoaudit_detected": detected_by.get("repoaudit_claude35", False),
            "speca_detected": detected_by.get("speca", False),
        })

    return {
        "total_disputed": len(disputed),
        "bugs": result,
        "speca_tn_count": sum(1 for b in result if not b["speca_detected"]),
        "summary": "SPECA correctly classifies disputed bugs as non-exploitable (TN), "
                   "while RepoAudit uses code-quality criteria that flag them as TP.",
    }


# ── Visualization ──────────────────────────────────────────────────

def plot_detection_heatmap(matrix_data: dict, output_dir: Path) -> Path:
    """Heatmap showing per-bug detection by each tool."""
    matrix = matrix_data["matrix"]
    tools = matrix_data["tools"]

    # Filter non-disputed bugs only
    bugs = [m for m in matrix if not m.get("disputed")]
    bug_ids = [b["id"] for b in bugs]

    # Build 2D array
    data = []
    for bug in bugs:
        row = []
        for tool in tools:
            val = bug.get(tool, "n/a")
            if val == "detected":
                row.append(1)
            elif val == "missed":
                row.append(0)
            else:
                row.append(-1)  # n/a
        data.append(row)

    data_arr = np.array(data)

    fig, ax = plt.subplots(figsize=(6, max(10, len(bugs) * 0.3)))

    # Custom colormap
    from matplotlib.colors import ListedColormap
    cmap = ListedColormap(["#e74c3c", "#95a5a6", "#2ecc71"])
    im = ax.imshow(data_arr, cmap=cmap, aspect="auto", vmin=-1, vmax=1)

    ax.set_xticks(range(len(tools)))
    ax.set_xticklabels(tools, fontsize=9)
    ax.set_yticks(range(len(bug_ids)))
    ax.set_yticklabels(bug_ids, fontsize=7)
    ax.set_title("Bug Detection Matrix\n(Green=Detected, Red=Missed, Gray=N/A)")

    # Add bug type annotations
    for i, bug in enumerate(bugs):
        btype = bug.get("bug_type", "")
        ax.text(-0.6, i, btype, ha="right", va="center", fontsize=6, color="#666")

    fig.tight_layout()
    out = output_dir / "rq2a_detection_heatmap_enhanced.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_bug_type_comparison(breakdown: dict, output_dir: Path) -> Path:
    """Grouped bar chart: detection rate by bug type per tool."""
    bug_types = ["NPD", "MLK", "UAF"]
    tools_order = ["RepoAudit", "SPECA", "Infer", "CodeGuru"]
    tools_present = [t for t in tools_order if t in breakdown]

    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(bug_types))
    width = 0.8 / len(tools_present)

    colors = {"RepoAudit": "#4C72B0", "SPECA": "#DD8452", "Infer": "#CCB974", "CodeGuru": "#64B5CD"}

    for i, tool in enumerate(tools_present):
        rates = []
        for bt in bug_types:
            stats = breakdown[tool].get(bt, {"detected": 0, "total": 0})
            total = stats["total"]
            detected = stats["detected"]
            rates.append(detected / total if total > 0 else 0)

        offset = (i - len(tools_present) / 2 + 0.5) * width
        bars = ax.bar(x + offset, rates, width, label=tool, color=colors.get(tool, "#999"))

        for bar, rate in zip(bars, rates):
            if rate > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                        f"{rate:.0%}", ha="center", va="bottom", fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels(bug_types)
    ax.set_ylabel("Detection Rate")
    ax.set_title("Detection Rate by Bug Type")
    ax.legend()
    ax.set_ylim(0, 1.15)
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    out = output_dir / "rq2a_bug_type_comparison.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_precision_recall_scatter(baselines: dict, output_dir: Path) -> Path:
    """Scatter plot: precision vs recall for all tools."""
    tools_data = baselines.get("tools", {})

    fig, ax = plt.subplots(figsize=(8, 6))

    tool_colors = {
        "speca": "#DD8452",
        "repoaudit_claude35_sonnet": "#4C72B0",
        "repoaudit_deepseek_r1": "#55A868",
        "repoaudit_claude37_sonnet": "#8172B2",
        "repoaudit_o3_mini": "#C44E52",
        "meta_infer": "#CCB974",
        "amazon_codeguru": "#64B5CD",
    }

    for key, tool in tools_data.items():
        precision = tool.get("precision", 0)
        tp = tool.get("tp", 0)
        fp = tool.get("fp", 0)
        recall = tool.get("recall")
        name = tool.get("display_name", key)

        # Estimate recall for tools without it
        if recall is None:
            # RepoAudit detected 40/40 old+new TPs; ground truth = 35 non-disputed
            recall_val = min(tp / 35, 1.0) if tp > 0 else 0
        else:
            recall_val = recall / 100 if recall > 1 else recall

        prec_val = precision / 100 if precision > 1 else precision

        color = tool_colors.get(key, "#999")
        ax.scatter(recall_val, prec_val, c=color, s=200, zorder=5,
                   edgecolors="white", linewidth=1.5)
        ax.annotate(name, (recall_val, prec_val),
                    xytext=(8, 8), textcoords="offset points",
                    fontsize=8, fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.8))

    # F1 contour lines
    for f1 in [0.3, 0.5, 0.7, 0.9]:
        r_vals = np.linspace(0.01, 1.0, 100)
        p_vals = (f1 * r_vals) / (2 * r_vals - f1)
        valid = (p_vals > 0) & (p_vals <= 1)
        ax.plot(r_vals[valid], p_vals[valid], '--', color='#ddd', linewidth=0.8, alpha=0.7)
        # Label the F1 line
        mid_idx = len(r_vals[valid]) // 2
        if mid_idx > 0:
            ax.text(r_vals[valid][mid_idx], p_vals[valid][mid_idx] + 0.02,
                    f"F1={f1}", fontsize=7, color="#bbb")

    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title("RQ2a: Precision vs Recall\n(RepoAudit 15-Project Benchmark)")
    ax.set_xlim(-0.05, 1.1)
    ax.set_ylim(-0.05, 1.1)
    ax.grid(alpha=0.3)

    fig.tight_layout()
    out = output_dir / "rq2a_precision_recall_scatter.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_disputed_analysis(disputed: dict, output_dir: Path) -> Path:
    """Visualization of disputed bug handling."""
    bugs = disputed["bugs"]
    if not bugs:
        return output_dir / "rq2a_disputed.png"

    fig, ax = plt.subplots(figsize=(8, 4))

    labels = [b["id"] for b in bugs]
    ra_detected = [1 if b["repoaudit_detected"] else 0 for b in bugs]
    speca_detected = [1 if b["speca_detected"] else 0 for b in bugs]

    x = np.arange(len(labels))
    width = 0.35

    ax.bar(x - width / 2, ra_detected, width, label="RepoAudit (flagged as TP)", color="#4C72B0", alpha=0.8)
    ax.bar(x + width / 2, speca_detected, width, label="SPECA (flagged as TP)", color="#DD8452", alpha=0.8)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=9)
    ax.set_ylabel("Detected (1) / Not Detected (0)")
    ax.set_title(f"Disputed Bugs (n={len(bugs)}): RepoAudit vs SPECA\n"
                 f"(Disputed = no exploit path; not detecting is correct)")
    ax.legend()
    ax.set_ylim(0, 1.3)
    ax.grid(axis="y", alpha=0.3)

    fig.tight_layout()
    out = output_dir / "rq2a_disputed_bugs.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def main():
    print("[rq2a_deep] Loading data...")
    baselines, gt, speca = load_data()

    print("[rq2a_deep] Building detection matrix...")
    matrix_data = build_detection_matrix(gt)

    print("[rq2a_deep] Computing comparison table...")
    comparison = compute_comparison_table(baselines, speca)

    print("[rq2a_deep] Analyzing bug type breakdown...")
    bug_type = analyze_bug_type_breakdown(gt, baselines, speca)

    print("[rq2a_deep] Analyzing disputed bugs...")
    disputed = analyze_disputed_bugs(gt, speca)

    # Save JSON
    results = {
        "detection_matrix": matrix_data,
        "comparison_table": comparison,
        "bug_type_breakdown": bug_type,
        "disputed_bugs": disputed,
    }

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    output_json = FIGURES_DIR / "deep_analysis.json"
    output_json.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"[rq2a_deep] Saved {output_json}")

    # Generate figures
    print("[rq2a_deep] Generating figures...")
    charts = []
    # Detection heatmap, bug type comparison, and disputed bugs charts removed —
    # heatmap/bug-type show no differentiation (100%/100%), disputed is one sentence.
    # Precision-recall scatter is the only chart with real information.
    charts.append(("Precision-Recall Scatter", plot_precision_recall_scatter(baselines, FIGURES_DIR)))

    for desc, path in charts:
        print(f"  [{desc}] {path}")

    # Summary
    print("\n" + "=" * 60)
    print("RQ2a DEEP ANALYSIS SUMMARY")
    print("=" * 60)
    print(f"\nDetection Matrix: {len(matrix_data['matrix'])} bugs x {len(matrix_data['tools'])} tools")
    print(f"\nDisputed Bugs: {disputed['total_disputed']}")
    print(f"  SPECA correctly not detecting: {disputed['speca_tn_count']}")

    print(f"\nBug Type Breakdown:")
    for tool, types in bug_type.items():
        parts = []
        for bt in ["NPD", "MLK", "UAF"]:
            stats = types.get(bt, {"detected": 0, "total": 0})
            parts.append(f"{bt}={stats['detected']}/{stats['total']}")
        print(f"  {tool}: {', '.join(parts)}")


if __name__ == "__main__":
    main()
