#!/usr/bin/env python3
"""RQ2b: ChatAFL ProFuzzBench — Visualization

Generates comparison figures from published baseline data.
SPECA results are optionally overlaid when available.

Usage:
    uv run python3 benchmarks/rq2b/visualize.py
    uv run python3 benchmarks/rq2b/visualize.py --speca-results path/to/speca_rq2b.json
"""

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import yaml

# ── Paths ──────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
BASELINES_PATH = SCRIPT_DIR / "published_baselines.yaml"
BUGS_PATH = SCRIPT_DIR / "ground_truth_bugs.yaml"
FIGURES_DIR = SCRIPT_DIR.parent / "results" / "rq2b" / "figures"

# ── Style ──────────────────────────────────────────────────────────
COLORS = {
    "ChatAFL": "#4C72B0",
    "AFLNet": "#55A868",
    "NSFuzz": "#C44E52",
    "SPECA": "#DD8452",
}

plt.rcParams.update({
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
    "figure.dpi": 150,
    "savefig.dpi": 150,
})

SUBJECTS_ORDER = ["Live555", "ProFTPD", "PureFTPD", "Kamailio", "Exim", "forked-daapd"]


def load_baselines() -> dict:
    with open(BASELINES_PATH) as f:
        return yaml.safe_load(f)


def load_bugs() -> dict:
    with open(BUGS_PATH) as f:
        return yaml.safe_load(f)


def load_speca(path: str | None) -> dict | None:
    if path is None:
        return None
    p = Path(path)
    if not p.exists():
        print(f"[WARN] SPECA results not found: {p}")
        return None
    with open(p) as f:
        return json.load(f)


# ── Figure 1: Tool Characteristics Comparison ──────────────────────
def fig1_complementarity(data: dict, speca: dict | None):
    """Table-style figure comparing tool characteristics."""
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.axis("off")

    headers = ["", "ChatAFL", "AFLNet", "NSFuzz", "SPECA"]
    rows = [
        ["Approach", "LLM-guided fuzzing", "Coverage-guided\nfuzzing", "State-aware\nfuzzing", "Spec-driven\nstatic analysis"],
        ["Input", "Protocol grammar\n(GPT-3.5 generated)", "Network traffic\nseeds", "Network traffic\nseeds", "RFC / spec\ndocuments"],
        ["Metric", "Branch coverage,\nstate transitions", "Branch coverage,\nstate transitions", "Branch coverage,\nstate transitions", "Spec violations,\nprecision"],
        ["Bug Types", "Memory errors\n(crash-based)", "Memory errors\n(crash-based)", "Memory errors\n(crash-based)", "Logic bugs,\nspec violations"],
        ["Zero-days", "9", "3", "4", "TBD"],
    ]

    table = ax.table(
        cellText=rows,
        colLabels=headers,
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.0, 2.0)

    # Style header
    for j in range(len(headers)):
        cell = table[0, j]
        cell.set_facecolor("#4C72B0")
        cell.set_text_props(color="white", fontweight="bold")

    # Style first column
    for i in range(1, len(rows) + 1):
        cell = table[i, 0]
        cell.set_facecolor("#E8E8E8")
        cell.set_text_props(fontweight="bold")

    ax.set_title("RQ2b: Tool Characteristics Comparison\n(Dynamic Fuzzing vs Specification-Driven Analysis)",
                 fontsize=13, fontweight="bold", pad=20)

    out = FIGURES_DIR / "rq2b_complementarity.png"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] {out}")


# ── Figure 2: State Transitions Comparison ─────────────────────────
def fig2_state_transitions(data: dict, speca: dict | None):
    """Grouped bar chart of state transitions per subject."""
    st = data["state_transitions"]

    subjects = SUBJECTS_ORDER
    chatafl_vals = [st[s]["ChatAFL"] for s in subjects]
    aflnet_vals = [st[s]["AFLNet"] for s in subjects]
    nsfuzz_vals = [st[s]["NSFuzz"] for s in subjects]

    fig, ax = plt.subplots(figsize=(12, 5))
    x = np.arange(len(subjects))
    w = 0.25

    bars1 = ax.bar(x - w, chatafl_vals, w, label="ChatAFL", color=COLORS["ChatAFL"], edgecolor="white")
    bars2 = ax.bar(x, aflnet_vals, w, label="AFLNet", color=COLORS["AFLNet"], edgecolor="white")
    bars3 = ax.bar(x + w, nsfuzz_vals, w, label="NSFuzz", color=COLORS["NSFuzz"], edgecolor="white")

    # Value labels for ChatAFL
    for bar, val in zip(bars1, chatafl_vals):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2,
                f"{val:.0f}", ha="center", va="bottom", fontsize=8, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(subjects, fontsize=9, rotation=15, ha="right")
    ax.set_ylabel("State Transitions (avg, 10 runs × 24h)")
    ax.set_title("RQ2b: State Transitions per Protocol Subject\n(ChatAFL vs AFLNet vs NSFuzz)")
    ax.legend(loc="upper right")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    out = FIGURES_DIR / "rq2b_state_transitions.png"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] {out}")


# ── Figure 3: Branch Coverage Comparison ───────────────────────────
def fig3_branch_coverage(data: dict, speca: dict | None):
    """Grouped bar chart of branch coverage per subject."""
    bc = data["branch_coverage"]

    subjects = SUBJECTS_ORDER
    chatafl_vals = [bc[s]["ChatAFL"] for s in subjects]
    aflnet_vals = [bc[s]["AFLNet"] for s in subjects]
    nsfuzz_vals = [bc[s]["NSFuzz"] for s in subjects]

    fig, ax = plt.subplots(figsize=(12, 5))
    x = np.arange(len(subjects))
    w = 0.25

    bars1 = ax.bar(x - w, chatafl_vals, w, label="ChatAFL", color=COLORS["ChatAFL"], edgecolor="white")
    bars2 = ax.bar(x, aflnet_vals, w, label="AFLNet", color=COLORS["AFLNet"], edgecolor="white")
    bars3 = ax.bar(x + w, nsfuzz_vals, w, label="NSFuzz", color=COLORS["NSFuzz"], edgecolor="white")

    ax.set_xticks(x)
    ax.set_xticklabels(subjects, fontsize=9, rotation=15, ha="right")
    ax.set_ylabel("Branch Coverage (avg, 10 runs × 24h)")
    ax.set_title("RQ2b: Branch Coverage per Protocol Subject\n(ChatAFL vs AFLNet vs NSFuzz)")
    ax.legend(loc="upper right")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    out = FIGURES_DIR / "rq2b_branch_coverage.png"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] {out}")


# ── Figure 4: Zero-Day Bug Detection Matrix ───────────────────────
def fig4_bug_detection(data: dict, bugs_data: dict, speca: dict | None):
    """Heatmap showing which tool found which zero-day bug."""
    bugs = bugs_data["bugs"]

    tool_names = ["ChatAFL", "AFLNet", "NSFuzz"]
    has_speca = speca and "bug_matches" in speca
    if has_speca:
        tool_names.append("SPECA")

    n_bugs = len(bugs)
    n_tools = len(tool_names)
    matrix = np.zeros((n_bugs, n_tools))

    bug_labels = []
    for i, bug in enumerate(bugs):
        label = f"{bug['id']}: {bug['subject']}\n({bug['bug_type']})"
        bug_labels.append(label)
        det = bug["detected_by"]
        matrix[i, 0] = 1 if det.get("chatafl") else 0
        matrix[i, 1] = 1 if det.get("aflnet") else 0
        matrix[i, 2] = 1 if det.get("nsfuzz") else 0
        if has_speca:
            matrix[i, 3] = 1 if det.get("speca") else 0

    fig, ax = plt.subplots(figsize=(8, 8))

    cmap = plt.cm.colors.ListedColormap(["#F0F0F0", "#4C72B0"])
    im = ax.imshow(matrix, cmap=cmap, aspect="auto", vmin=0, vmax=1)

    ax.set_xticks(np.arange(n_tools))
    ax.set_xticklabels(tool_names, fontsize=10, fontweight="bold")
    ax.set_yticks(np.arange(n_bugs))
    ax.set_yticklabels(bug_labels, fontsize=8)

    # Annotate cells
    for i in range(n_bugs):
        for j in range(n_tools):
            val = int(matrix[i, j])
            symbol = "✓" if val == 1 else "✗"
            color = "white" if val == 1 else "#AAAAAA"
            ax.text(j, i, symbol, ha="center", va="center", fontsize=12,
                    color=color, fontweight="bold")

    ax.set_title("RQ2b: Zero-Day Bug Detection Matrix\n(ChatAFL Table VII)")

    # Legend
    found_patch = mpatches.Patch(color="#4C72B0", label="Detected")
    missed_patch = mpatches.Patch(color="#F0F0F0", label="Not detected")
    ax.legend(handles=[found_patch, missed_patch], loc="upper right",
              bbox_to_anchor=(1.0, -0.05), ncol=2)

    out = FIGURES_DIR / "rq2b_bug_detection_matrix.png"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] {out}")


# ── Figure 5: Bug Type Distribution ───────────────────────────────
def fig5_bug_types(data: dict, bugs_data: dict, speca: dict | None):
    """Bar chart: bug types found by each tool."""
    bugs = bugs_data["bugs"]

    bug_types = sorted(set(b["bug_type"] for b in bugs))
    tools = ["ChatAFL", "AFLNet", "NSFuzz"]

    tool_key_map = {"ChatAFL": "chatafl", "AFLNet": "aflnet", "NSFuzz": "nsfuzz"}

    counts = {tool: {bt: 0 for bt in bug_types} for tool in tools}
    for bug in bugs:
        bt = bug["bug_type"]
        det = bug["detected_by"]
        for tool, key in tool_key_map.items():
            if det.get(key):
                counts[tool][bt] += 1

    # Add SPECA if available
    if speca and "bug_type_counts" in speca:
        tools.append("SPECA")
        counts["SPECA"] = speca["bug_type_counts"]

    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(bug_types))
    n_tools = len(tools)
    w = 0.8 / n_tools

    for i, tool in enumerate(tools):
        vals = [counts[tool].get(bt, 0) for bt in bug_types]
        offset = (i - n_tools / 2 + 0.5) * w
        color = COLORS.get(tool, "#999999")
        bars = ax.bar(x + offset, vals, w, label=tool, color=color, edgecolor="white")
        for bar, val in zip(bars, vals):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.1,
                        str(val), ha="center", va="bottom", fontsize=9, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels([bt.replace("-", "\n") for bt in bug_types], fontsize=9)
    ax.set_ylabel("Bugs Found")
    ax.set_title("RQ2b: Zero-Day Bugs by Type\n(ChatAFL vs AFLNet vs NSFuzz)")
    ax.legend(loc="upper right")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    out = FIGURES_DIR / "rq2b_bug_types.png"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] {out}")


# ── Figure 6: Venn-style Bug Overlap (SPECA results required) ─────
def fig6_venn(data: dict, bugs_data: dict, speca: dict | None):
    """Venn diagram showing overlap between ChatAFL and SPECA findings.
    Only generated when SPECA results are available."""
    if not speca or "bug_matches" not in speca:
        print("  [SKIP] rq2b_venn_diagram.png (no SPECA results)")
        return

    chatafl_only = speca.get("chatafl_only", 0)
    speca_only = speca.get("speca_only", 0)
    overlap = speca.get("overlap", 0)

    fig, ax = plt.subplots(figsize=(8, 6))

    # Simple Euler diagram using circles
    from matplotlib.patches import Circle

    c1 = Circle((0.35, 0.5), 0.25, alpha=0.4, color=COLORS["ChatAFL"], label="ChatAFL")
    c2 = Circle((0.65, 0.5), 0.25, alpha=0.4, color=COLORS["SPECA"], label="SPECA")
    ax.add_patch(c1)
    ax.add_patch(c2)

    # Labels
    ax.text(0.25, 0.5, f"{chatafl_only}", ha="center", va="center",
            fontsize=18, fontweight="bold")
    ax.text(0.5, 0.5, f"{overlap}", ha="center", va="center",
            fontsize=18, fontweight="bold")
    ax.text(0.75, 0.5, f"{speca_only}", ha="center", va="center",
            fontsize=18, fontweight="bold")

    ax.text(0.25, 0.25, "ChatAFL only", ha="center", fontsize=10, color="#4C72B0")
    ax.text(0.5, 0.25, "Both", ha="center", fontsize=10)
    ax.text(0.75, 0.25, "SPECA only", ha="center", fontsize=10, color="#DD8452")

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("RQ2b: Bug Detection Overlap\n(ChatAFL Crashes vs SPECA Spec Violations)",
                 fontsize=13, fontweight="bold")

    out = FIGURES_DIR / "rq2b_venn_diagram.png"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] {out}")


# ── Main ───────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="RQ2b visualization")
    parser.add_argument("--speca-results", type=str, default=None,
                        help="Path to SPECA results JSON for RQ2b")
    args = parser.parse_args()

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading baselines...")
    data = load_baselines()
    bugs_data = load_bugs()
    speca = load_speca(args.speca_results)

    if speca:
        print(f"  SPECA results loaded")
    else:
        print("  SPECA results not available — generating baselines-only figures")

    print(f"\nGenerating figures...")
    fig1_complementarity(data, speca)
    fig2_state_transitions(data, speca)
    fig3_branch_coverage(data, speca)
    fig4_bug_detection(data, bugs_data, speca)
    fig5_bug_types(data, bugs_data, speca)
    fig6_venn(data, bugs_data, speca)

    n_figures = len(list(FIGURES_DIR.glob("*.png")))
    print(f"\nDone. {n_figures} figures saved to {FIGURES_DIR}")


if __name__ == "__main__":
    main()
