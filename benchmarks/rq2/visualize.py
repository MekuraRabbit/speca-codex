#!/usr/bin/env python3
"""Generate visualization charts from RQ2 benchmark metrics."""

from __future__ import annotations

import json
import sys
import argparse
from pathlib import Path

# Ensure project root is on sys.path for direct script execution
_PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_METRICS = ROOT_DIR / "benchmarks" / "results" / "rq2" / "metrics.json"
OUTPUT_DIR = ROOT_DIR / "benchmarks" / "results" / "rq2" / "figures"

TOOL_DISPLAY = {
    "semgrep": "Semgrep",
    "cppcheck": "Cppcheck",
    "flawfinder": "Flawfinder",
    "codeql": "CodeQL",
    "security_agent": "Security Agent",
    "llm_baseline": "LLM Baseline",
    "static_baseline": "Static Baseline",
}

TOOL_COLORS = {
    "semgrep": "#4CAF50",
    "cppcheck": "#FF9800",
    "flawfinder": "#00BCD4",
    "codeql": "#2196F3",
    "security_agent": "#FF5722",
    "llm_baseline": "#9C27B0",
    "static_baseline": "#607D8B",
}

# Tools to include in graphs (ordered). Others are excluded from display.
# Security Agent is always shown as a placeholder even when results are missing.
DISPLAY_ORDER = ["semgrep", "cppcheck", "flawfinder", "security_agent"]

STATUS_COLORS = {
    "ok": "#4CAF50",
    "missing_results": "#BDBDBD",
    "pending": "#FFD54F",
    "invalid_results": "#FF9800",
}


def load_metrics(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _display_tools(tools: dict) -> list[str]:
    """Return ordered list of tool keys to display."""
    return [t for t in DISPLAY_ORDER if t in tools or t == "security_agent"]


def fig1_tool_comparison(data: dict, output_dir: Path) -> None:
    """Bar chart comparing tool precision, recall, F1 — includes Security Agent placeholder."""
    tools = data.get("tools", {})
    dataset = data.get("dataset", {})
    dataset_label = dataset.get("name", "unknown").replace("_", " ").title()
    sample_count = dataset.get("sample_count", "?")
    display = _display_tools(tools)

    tool_names = []
    precision_vals = []
    recall_vals = []
    f1_vals = []

    for name in display:
        metrics = tools.get(name, {})
        tool_names.append(TOOL_DISPLAY.get(name, name))
        if metrics.get("status") == "ok":
            precision_vals.append(metrics.get("precision", 0))
            recall_vals.append(metrics.get("recall", 0))
            f1_vals.append(metrics.get("f1", 0))
        else:
            # Placeholder (TBD)
            precision_vals.append(0)
            recall_vals.append(0)
            f1_vals.append(0)

    if not tool_names:
        print("  No tools to plot for fig1")
        return

    x = np.arange(len(tool_names))
    width = 0.25

    fig, ax = plt.subplots(figsize=(10, 6))
    bars1 = ax.bar(x - width, precision_vals, width, label="Precision", color="#2196F3")
    bars2 = ax.bar(x, recall_vals, width, label="Recall", color="#FF5722")
    bars3 = ax.bar(x + width, f1_vals, width, label="F1", color="#4CAF50")

    ax.set_xlabel("Tool")
    ax.set_ylabel("Score")
    ax.set_title(f"RQ2: Tool Performance Comparison ({dataset_label}, n={sample_count})")
    ax.set_xticks(x)
    ax.set_xticklabels(tool_names)
    ax.legend()
    ax.set_ylim(0, 1.1)
    ax.grid(axis="y", alpha=0.3)

    # Add value labels on bars
    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.annotate(f"{height:.2f}", xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=9)

    # Mark Security Agent as TBD
    for i, name in enumerate(display):
        if tools.get(name, {}).get("status") != "ok":
            ax.annotate("TBD", xy=(i, 0.02), ha="center", va="bottom",
                        fontsize=11, fontweight="bold", color="#999", fontstyle="italic")

    fig.tight_layout()
    fig.savefig(output_dir / "fig1_tool_comparison.png", dpi=150)
    plt.close(fig)
    print(f"  Saved fig1_tool_comparison.png")


def fig2_confusion_matrix(data: dict, output_dir: Path) -> None:
    """Stacked bar chart showing confusion matrix breakdown for each tool."""
    tools = data.get("tools", {})
    dataset = data.get("dataset", {})
    dataset_label = dataset.get("name", "unknown").replace("_", " ").title()
    sample_count = dataset.get("sample_count", "?")
    display = _display_tools(tools)

    tool_names = []
    tp_vals = []
    fp_vals = []
    tn_vals = []
    fn_vals = []
    is_placeholder = []

    for name in display:
        metrics = tools.get(name, {})
        tool_names.append(TOOL_DISPLAY.get(name, name))
        if metrics.get("status") == "ok":
            scored = metrics.get("tp", 0) + metrics.get("fp", 0) + metrics.get("tn", 0) + metrics.get("fn", 0)
            if scored == 0:
                tp_vals.append(0); fp_vals.append(0); tn_vals.append(0); fn_vals.append(0)
                is_placeholder.append(True)
            else:
                tp_vals.append(metrics.get("tp", 0))
                fp_vals.append(metrics.get("fp", 0))
                tn_vals.append(metrics.get("tn", 0))
                fn_vals.append(metrics.get("fn", 0))
                is_placeholder.append(False)
        else:
            tp_vals.append(0); fp_vals.append(0); tn_vals.append(0); fn_vals.append(0)
            is_placeholder.append(True)

    if not tool_names:
        print("  No tools with confusion data for fig2")
        return

    x = np.arange(len(tool_names))
    width = 0.5

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.bar(x, tp_vals, width, label="TP (True Positive)", color="#4CAF50")
    ax.bar(x, fp_vals, width, bottom=tp_vals, label="FP (False Positive)", color="#FF9800")
    ax.bar(x, tn_vals, width, bottom=[tp + fp for tp, fp in zip(tp_vals, fp_vals)],
           label="TN (True Negative)", color="#2196F3")
    ax.bar(x, fn_vals, width,
           bottom=[tp + fp + tn for tp, fp, tn in zip(tp_vals, fp_vals, tn_vals)],
           label="FN (False Negative)", color="#F44336")

    ax.set_xlabel("Tool")
    ax.set_ylabel("Number of Samples")
    ax.set_title(f"RQ2: Confusion Matrix Breakdown ({dataset_label}, n={sample_count})")
    ax.set_xticks(x)
    ax.set_xticklabels(tool_names)
    ax.legend(loc="upper right")
    ax.grid(axis="y", alpha=0.3)

    for i, (tp, fp, tn, fn) in enumerate(zip(tp_vals, fp_vals, tn_vals, fn_vals)):
        total = tp + fp + tn + fn
        if is_placeholder[i]:
            ax.annotate("TBD", xy=(i, 50), ha="center", fontsize=11,
                        fontweight="bold", color="#999", fontstyle="italic")
        else:
            ax.annotate(f"n={total}", xy=(i, total), xytext=(0, 5),
                        textcoords="offset points", ha="center", fontsize=9, fontweight="bold")

    fig.tight_layout()
    fig.savefig(output_dir / "fig2_confusion_matrix.png", dpi=150)
    plt.close(fig)
    print(f"  Saved fig2_confusion_matrix.png")


def fig3_cwe_coverage(data: dict, output_dir: Path) -> None:
    """Horizontal bar chart showing CWE coverage for top CWEs."""
    dataset = data.get("dataset", {})
    tools = data.get("tools", {})
    cwe_totals = dataset.get("cwe_totals", {})

    if not cwe_totals:
        print("  No CWE data for fig3")
        return

    top_cwes = sorted(cwe_totals.items(), key=lambda x: x[1], reverse=True)[:15]
    cwe_names = [cwe for cwe, _ in top_cwes]
    cwe_counts = [count for _, count in top_cwes]

    fig, ax = plt.subplots(figsize=(12, 8))

    y = np.arange(len(cwe_names))
    ax.barh(y, cwe_counts, color="#E0E0E0", label="Total Vulnerable")

    # Only overlay tools that have actual results + are in display order
    active_tools = [(name, tools[name]) for name in DISPLAY_ORDER
                    if name in tools and tools[name].get("status") == "ok" and tools[name].get("cwe_coverage")]

    for tool_idx, (tool_name, metrics) in enumerate(active_tools):
        cwe_cov = metrics.get("cwe_coverage", {})
        tp_counts = [cwe_cov.get(cwe, {}).get("tp", 0) for cwe in cwe_names]
        if any(tp > 0 for tp in tp_counts):
            offset = (tool_idx + 1) * 0.15
            ax.barh(y + offset, tp_counts, height=0.15,
                    color=TOOL_COLORS.get(tool_name, "#999"),
                    label=f"{TOOL_DISPLAY.get(tool_name, tool_name)} TP")

    for i, (cwe, count) in enumerate(zip(cwe_names, cwe_counts)):
        ax.text(count + 0.5, i, str(count), va="center", fontsize=9)

    ax.set_yticks(y)
    ax.set_yticklabels(cwe_names)
    ax.set_xlabel("Number of Vulnerable Samples")
    dataset = data.get("dataset", {})
    dataset_label = dataset.get("name", "unknown").replace("_", " ").title()
    ax.set_title(f"RQ2: CWE Distribution & Tool Detection Coverage ({dataset_label})")
    ax.legend(loc="lower right")
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.3)

    fig.tight_layout()
    fig.savefig(output_dir / "fig3_cwe_coverage.png", dpi=150)
    plt.close(fig)
    print(f"  Saved fig3_cwe_coverage.png")


def fig4_tool_status(data: dict, output_dir: Path) -> None:
    """Summary diagram showing tool status and dataset overview."""
    tools = data.get("tools", {})
    dataset = data.get("dataset", {})
    display = _display_tools(tools)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Left: Tool status (only display-order tools)
    ax1 = axes[0]
    display_names = [TOOL_DISPLAY.get(t, t) for t in display]
    statuses = []
    for t in display:
        s = tools.get(t, {}).get("status", "missing_results")
        if s == "missing_results":
            statuses.append("pending")
        else:
            statuses.append(s)
    colors = [STATUS_COLORS.get(s, "#999") for s in statuses]

    y_idx = np.arange(len(display))
    ax1.barh(y_idx, [1] * len(display), color=colors, height=0.6)
    for i, (name, status) in enumerate(zip(display_names, statuses)):
        if status == "ok":
            label = "Ready"
            text_color = "white"
        elif status == "pending":
            label = "Pending"
            text_color = "#333"
        else:
            label = status.replace("_", " ").title()
            text_color = "black"
        ax1.text(0.5, i, f"{name}\n({label})", ha="center", va="center",
                fontsize=11, fontweight="bold", color=text_color)
    ax1.set_xlim(0, 1)
    ax1.set_yticks([])
    ax1.set_xticks([])
    ax1.set_title("Tool Status")
    ax1.invert_yaxis()

    # Right: Dataset composition
    ax2 = axes[1]
    total = dataset.get("sample_count", 0)

    # Get vuln/clean from any ok tool
    vuln_count = clean_count = 0
    for t in display:
        m = tools.get(t, {})
        if m.get("status") == "ok":
            vuln_count = m.get("tp", 0) + m.get("fn", 0)
            clean_count = m.get("fp", 0) + m.get("tn", 0)
            if vuln_count + clean_count > 0:
                break

    if vuln_count + clean_count > 0:
        sizes = [vuln_count, clean_count]
        labels = [f"Vulnerable\n({vuln_count})", f"Clean\n({clean_count})"]
        pie_colors = ["#F44336", "#4CAF50"]
        explode = (0.05, 0)
        ax2.pie(sizes, labels=labels, colors=pie_colors, autopct="%1.1f%%",
                explode=explode, startangle=90, textprops={"fontsize": 11})
        ax2.set_title(f"Dataset Composition (n={total})")
    else:
        gt_count = dataset.get("ground_truth_count", 0)
        ax2.text(0.5, 0.5, f"Total: {total} samples\nGround truth: {gt_count}",
                ha="center", va="center", fontsize=14, transform=ax2.transAxes)
        ax2.set_title("Dataset Overview")

    dataset_label = dataset.get("name", "unknown").replace("_", " ").title()
    fig.suptitle(f"RQ2 Benchmark Overview: {dataset_label} Dataset", fontsize=14, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(output_dir / "fig4_overview.png", dpi=150)
    plt.close(fig)
    print(f"  Saved fig4_overview.png")


def fig5_cwe_treemap(data: dict, output_dir: Path) -> None:
    """Bubble chart showing CWE distribution by count."""
    cwe_totals = data.get("dataset", {}).get("cwe_totals", {})
    if not cwe_totals:
        print("  No CWE data for fig5")
        return

    sorted_cwes = sorted(cwe_totals.items(), key=lambda x: x[1], reverse=True)
    cwes = [c for c, _ in sorted_cwes[:20]]
    counts = [n for _, n in sorted_cwes[:20]]

    fig, ax = plt.subplots(figsize=(14, 8))

    n = len(cwes)
    cols = 5
    rows = (n + cols - 1) // cols
    x_pos = [(i % cols) * 3 for i in range(n)]
    y_pos = [(i // cols) * 3 for i in range(n)]

    max_count = max(counts)
    sizes = [(c / max_count) * 3000 + 200 for c in counts]

    colors = plt.cm.RdYlGn_r(np.array(counts) / max_count)

    ax.scatter(x_pos, y_pos, s=sizes, c=colors, alpha=0.7, edgecolors="black", linewidth=0.5)

    for i, (cwe, count) in enumerate(zip(cwes, counts)):
        ax.annotate(f"{cwe}\n({count})", (x_pos[i], y_pos[i]),
                    ha="center", va="center", fontsize=8, fontweight="bold")

    ax.set_xlim(-2, cols * 3)
    ax.set_ylim(-2, rows * 3)
    ax.set_aspect("equal")
    ax.axis("off")
    dataset_label = data.get("dataset", {}).get("name", "unknown").replace("_", " ").title()
    ax.set_title(f"RQ2: CWE Distribution in {dataset_label} (Top 20)", fontsize=14, fontweight="bold")

    fig.tight_layout()
    fig.savefig(output_dir / "fig5_cwe_distribution.png", dpi=150)
    plt.close(fig)
    print(f"  Saved fig5_cwe_distribution.png")


# Alias for consistent naming
fig5_cwe_distribution = fig5_cwe_treemap


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate RQ2 visualization charts.")
    parser.add_argument("--metrics", type=Path, default=DEFAULT_METRICS)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()

    if not args.metrics.exists():
        print(f"Metrics file not found: {args.metrics}")
        return 1

    args.output_dir.mkdir(parents=True, exist_ok=True)
    data = load_metrics(args.metrics)
    print(f"Loaded metrics from {args.metrics}")

    print("Generating figures...")
    fig1_tool_comparison(data, args.output_dir)
    fig2_confusion_matrix(data, args.output_dir)
    fig3_cwe_coverage(data, args.output_dir)
    fig4_tool_status(data, args.output_dir)
    fig5_cwe_distribution(data, args.output_dir)

    print(f"\nAll figures saved to {args.output_dir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
