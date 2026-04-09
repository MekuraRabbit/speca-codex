#!/usr/bin/env python3
"""RQ2a: RepoAudit 15-Project Benchmark — Visualization

Generates comparison figures from published baseline data.
SPECA results are optionally overlaid when available.

Usage:
    uv run python3 benchmarks/rq2a/visualize.py
    uv run python3 benchmarks/rq2a/visualize.py --speca-results path/to/speca_summary.json
    uv run python3 benchmarks/rq2a/visualize.py --speca-multi "Sonnet 4.5=path1.json" "Sonnet 4=path2.json"
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
FIGURES_DIR = SCRIPT_DIR.parent / "results" / "rq2a" / "figures"

# ── Style ──────────────────────────────────────────────────────────
COLORS = {
    "RepoAudit\n(Claude 3.5)": "#4C72B0",
    "RepoAudit\n(DeepSeek R1)": "#55A868",
    "RepoAudit\n(Claude 3.7)": "#8172B2",
    "RepoAudit\n(o3-mini)": "#C44E52",
    "Meta Infer": "#CCB974",
    "CodeGuru": "#64B5CD",
    "Single-fn\nLLM": "#AAAAAA",
    "SPECA": "#DD8452",
    # SPECA model-specific colors
    "SPECA\n(Sonnet 4.5)": "#DD8452",
    "SPECA\n(Sonnet 4)": "#E8794A",
    "SPECA\n(DeepSeek R1)": "#8B5CF6",
}

plt.rcParams.update({
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
    "figure.dpi": 150,
    "savefig.dpi": 150,
})


def load_baselines() -> dict:
    with open(BASELINES_PATH) as f:
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


def load_speca_multi(specs: list[str] | None) -> list[tuple[str, dict]]:
    """Load multiple SPECA results as (label, data) pairs.

    Each spec is "Label=path/to/summary.json".
    """
    if not specs:
        return []
    results = []
    for spec in specs:
        if "=" not in spec:
            print(f"[WARN] Invalid --speca-multi format (need Label=path): {spec}")
            continue
        label, path = spec.split("=", 1)
        p = Path(path)
        if not p.exists():
            print(f"[WARN] SPECA results not found: {p}")
            continue
        with open(p) as f:
            data = json.load(f)
        results.append((label.strip(), data))
    return _sort_speca_list(results)


# Canonical ordering for SPECA model variants
_SPECA_ORDER = ["DeepSeek R1", "Sonnet 4", "Sonnet 4.5"]


def _sort_speca_list(lst: list[tuple[str, dict]]) -> list[tuple[str, dict]]:
    """Sort SPECA variants into canonical order: DR1 → S4 → S4.5."""
    def _key(item: tuple[str, dict]) -> int:
        label = item[0]
        # Check most-specific names first to avoid "Sonnet 4" matching "Sonnet 4.5"
        for i, name in reversed(list(enumerate(_SPECA_ORDER))):
            if name in label:
                return i
        return len(_SPECA_ORDER)
    return sorted(lst, key=_key)


# ── Figure 1: Precision Comparison (bar chart) ─────────────────────
def fig1_precision(data: dict, speca_list: list[tuple[str, dict]]):
    """Bar chart comparing precision across all tools."""
    tools = data["tools"]

    names = []
    precisions = []
    colors = []

    # Order: RepoAudit variants → traditional → SPECA
    order = [
        ("repoaudit_deepseek_r1", "RepoAudit\n(DeepSeek R1)"),
        ("repoaudit_claude37_sonnet", "RepoAudit\n(Claude 3.7)"),
        ("repoaudit_o3_mini", "RepoAudit\n(o3-mini)"),
        ("repoaudit_claude35_sonnet", "RepoAudit\n(Claude 3.5)"),
        ("meta_infer", "Meta Infer"),
        ("amazon_codeguru", "CodeGuru"),
    ]

    for key, label in order:
        t = tools[key]
        p = t.get("precision")
        if p is not None:
            names.append(label)
            precisions.append(p)
            colors.append(COLORS.get(label, "#999999"))

    # Add SPECA variants
    for label, sdata in speca_list:
        if sdata.get("precision") is not None:
            display = f"SPECA\n({label})"
            names.append(display)
            precisions.append(sdata["precision"])
            colors.append(COLORS.get(display, "#DD8452"))

    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(names))
    bars = ax.bar(x, precisions, color=colors, edgecolor="white", width=0.6)

    # Value labels
    for bar, val in zip(bars, precisions):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1.0,
                f"{val:.1f}%", ha="center", va="bottom", fontsize=10, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(names, fontsize=9)
    ax.set_ylabel("Precision (%)")
    ax.set_ylim(0, 105)
    ax.set_title("RQ2a: Tool Precision Comparison\n(RepoAudit 15-Project Benchmark, ICML 2025)")
    ax.axhline(y=50, color="gray", linestyle="--", alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    out = FIGURES_DIR / "rq2a_precision_comparison.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"  [OK] {out}")


# ── Figure 2: TP / FP Comparison (grouped bar) ─────────────────────
def fig2_tp_fp(data: dict, speca_list: list[tuple[str, dict]]):
    """Grouped bar chart of TP and FP counts.

    Order: baselines first, then SPECA variants (DR1 → S4 → S4.5).
    TP bars split into GT match (blue) and new bugs (green) where data available.
    """
    tools_data = data["tools"]
    gt_total = 35  # non-disputed ground truth bugs

    # Build entries: (label, gt_tp, new_tp, fp)
    entries: list[tuple[str, int, int, int]] = []

    # Baselines
    baseline_order = [
        ("repoaudit_deepseek_r1", "RepoAudit\n(DeepSeek R1)"),
        ("repoaudit_claude37_sonnet", "RepoAudit\n(Claude 3.7)"),
        ("repoaudit_claude35_sonnet", "RepoAudit\n(Claude 3.5)"),
        ("repoaudit_o3_mini", "RepoAudit\n(o3-mini)"),
        ("meta_infer", "Meta Infer"),
        ("amazon_codeguru", "CodeGuru"),
        ("single_function_llm", "Single-fn\nLLM"),
    ]
    for key, label in baseline_order:
        t = tools_data.get(key, {})
        tp = t.get("tp")
        if tp is not None:
            entries.append((label, min(tp, gt_total), max(0, tp - gt_total), t.get("fp", 0)))

    # SPECA variants (already sorted: DR1 → S4 → S4.5)
    for label, sdata in speca_list:
        if sdata.get("tp") is not None:
            entries.append((f"SPECA\n({label})", sdata.get("gt_tp", min(sdata["tp"], gt_total)),
                            sdata.get("new_tp", max(0, sdata["tp"] - gt_total)), sdata.get("fp", 0)))

    names = [e[0] for e in entries]
    gt_tps = [e[1] for e in entries]
    new_tps = [e[2] for e in entries]
    fps = [e[3] for e in entries]

    fig, ax = plt.subplots(figsize=(14, 6))
    x = np.arange(len(names))
    w = 0.35

    # Stacked TP: GT match (blue) + new bugs (green)
    bars_gt = ax.bar(x - w / 2, gt_tps, w, label="TP: GT Match", color="#4C72B0", edgecolor="white")
    ax.bar(x - w / 2, new_tps, w, bottom=gt_tps, label="TP: New Bugs", color="#2ecc71", edgecolor="white")
    bars_fp = ax.bar(x + w / 2, fps, w, label="False Positives (FP)", color="#C44E52", edgecolor="white")

    # Set ylim with headroom for annotations
    max_val = max(max(g + n for g, n in zip(gt_tps, new_tps)), max(fps)) if fps else 0
    ax.set_ylim(0, max_val * 1.15)

    # TP total labels
    for i, (gt, new) in enumerate(zip(gt_tps, new_tps)):
        total = gt + new
        if total > 0:
            bar_x = x[i] - w / 2
            label_text = str(total) if new == 0 else f"{gt}+{new}"
            ax.text(bar_x + w / 2, total + 0.5, label_text,
                    ha="center", va="bottom", fontsize=9, fontweight="bold")

    for bar, val in zip(bars_fp, fps):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                    str(val), ha="center", va="bottom", fontsize=10, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(names, fontsize=9)
    ax.set_ylabel("Count")
    ax.set_title("RQ2a: True Positives vs False Positives\n(RepoAudit 15-Project Benchmark)")
    ax.legend(loc="upper right", fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    out = FIGURES_DIR / "rq2a_tp_fp_comparison.png"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] {out}")


# ── Figure 3: Bug Type Breakdown (stacked bar) ─────────────────────
def fig3_bug_type(data: dict, speca_list: list[tuple[str, dict]]):
    """Stacked bar showing TP breakdown by bug type (NPD/MLK/UAF)."""
    projects = data["projects"]

    # Count by bug type
    type_counts = {"NPD": 0, "MLK": 0, "UAF": 0}
    for p in projects:
        bt = p["bug_type"]
        total_tp = p["old_tp"] + p["new_tp"][0]
        type_counts[bt] += total_tp

    fig, ax = plt.subplots(figsize=(8, 5))

    # RepoAudit breakdown
    labels = ["RepoAudit\n(Claude 3.5)"]
    npd_vals = [type_counts["NPD"]]
    mlk_vals = [type_counts["MLK"]]
    uaf_vals = [type_counts["UAF"]]

    # Meta Infer (NPD only, 7 TP)
    labels.append("Meta Infer")
    npd_vals.append(7)
    mlk_vals.append(0)
    uaf_vals.append(0)

    # SPECA variants
    for label, sdata in speca_list:
        if "bug_type_breakdown" in sdata:
            labels.append(f"SPECA\n({label})")
            bt = sdata["bug_type_breakdown"]
            npd_vals.append(bt.get("NPD", 0))
            mlk_vals.append(bt.get("MLK", 0))
            uaf_vals.append(bt.get("UAF", 0))

    x = np.arange(len(labels))
    w = 0.5

    bars_npd = ax.bar(x, npd_vals, w, label="NPD", color="#4C72B0")
    bars_mlk = ax.bar(x, mlk_vals, w, bottom=npd_vals, label="MLK", color="#55A868")
    uaf_bottom = [n + m for n, m in zip(npd_vals, mlk_vals)]
    bars_uaf = ax.bar(x, uaf_vals, w, bottom=uaf_bottom, label="UAF", color="#C44E52")

    # Value labels
    for i, (n, m, u) in enumerate(zip(npd_vals, mlk_vals, uaf_vals)):
        total = n + m + u
        ax.text(i, total + 0.5, str(total), ha="center", va="bottom",
                fontsize=11, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel("True Positives")
    ax.set_title("RQ2a: Bug Type Breakdown\n(NPD / MLK / UAF)")
    ax.legend(loc="upper right")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    out = FIGURES_DIR / "rq2a_bug_type_breakdown.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"  [OK] {out}")


# ── Figure 4: Per-Project Detection Heatmap ─────────────────────────

GT_BUGS_PATH = SCRIPT_DIR / "ground_truth_bugs.yaml"


def _load_meta_infer_per_project(projects: list[dict]) -> dict[str, int]:
    """Load Meta Infer per-project TP counts from ground_truth_bugs.yaml.

    Falls back to zero if data is missing. Meta Infer detects NPD only.
    """
    if not GT_BUGS_PATH.exists():
        return {}
    with open(GT_BUGS_PATH) as f:
        gt = yaml.safe_load(f)
    bugs = gt.get("bugs", [])

    # Map project IDs (N1, N2, ...) to Meta Infer TP counts
    id_to_count: dict[str, int] = {}
    for bug in bugs:
        det = bug.get("detected_by", {})
        if det.get("meta_infer") is True:
            bug_id = bug.get("id", "")
            # Extract project ID: RA-N1-O1 → N1
            parts = bug_id.split("-")
            if len(parts) >= 2:
                proj_id = parts[1]
                id_to_count[proj_id] = id_to_count.get(proj_id, 0) + 1
    return id_to_count


def fig4_per_project(data: dict, speca_list: list[tuple[str, dict]]):
    """Heatmap: projects × tools detection matrix.

    Meta Infer data sourced from ground_truth_bugs.yaml per-bug detections.
    """
    projects = data["projects"]
    proj_names = [p["name"] for p in projects]
    proj_types = [p["bug_type"] for p in projects]

    # Build matrix: rows=projects, cols=tools
    tool_cols = ["RepoAudit\n(Claude 3.5)", "Meta Infer", "CodeGuru"]
    for label, sdata in speca_list:
        if "per_project" in sdata:
            tool_cols.append(f"SPECA\n({label})")

    n_proj = len(projects)
    n_tools = len(tool_cols)
    matrix = np.zeros((n_proj, n_tools))

    # Meta Infer per-project from ground truth
    infer_counts = _load_meta_infer_per_project(projects)

    for i, p in enumerate(projects):
        total_tp = p["old_tp"] + p["new_tp"][0]
        # RepoAudit
        matrix[i, 0] = total_tp
        # Meta Infer — from ground truth per-bug data
        matrix[i, 1] = infer_counts.get(p["id"], 0)
        # CodeGuru: 0 TP everywhere
        matrix[i, 2] = 0

    # Fill SPECA columns
    speca_col_start = 3
    for si, (label, sdata) in enumerate(speca_list):
        if "per_project" in sdata:
            col = speca_col_start + si
            for i, p in enumerate(projects):
                matrix[i, col] = sdata["per_project"].get(p["id"], 0)

    # Warn if Meta Infer total doesn't match expected
    infer_total = int(matrix[:, 1].sum())
    expected_infer = data.get("tools", {}).get("meta_infer", {}).get("tp", 7)
    if infer_total != expected_infer:
        print(f"  [WARN] Meta Infer heatmap total={infer_total}, "
              f"expected={expected_infer}. "
              f"Populate meta_infer detections in ground_truth_bugs.yaml.")

    fig, ax = plt.subplots(figsize=(8, 10))
    im = ax.imshow(matrix, cmap="YlOrRd", aspect="auto", vmin=0, vmax=max(8, matrix.max()))

    ax.set_xticks(np.arange(n_tools))
    ax.set_xticklabels(tool_cols, fontsize=9)
    ax.set_yticks(np.arange(n_proj))
    ylabels = [f"{name}\n({bt})" for name, bt in zip(proj_names, proj_types)]
    ax.set_yticklabels(ylabels, fontsize=8)

    # Annotate cells
    for i in range(n_proj):
        for j in range(n_tools):
            val = int(matrix[i, j])
            color = "white" if val > 3 else "black"
            ax.text(j, i, str(val), ha="center", va="center", fontsize=9, color=color)

    ax.set_title("RQ2a: Per-Project Bug Detection\n(RepoAudit 15-Project Benchmark)")
    fig.colorbar(im, ax=ax, label="Bugs Detected", shrink=0.6)

    out = FIGURES_DIR / "rq2a_per_project_heatmap.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"  [OK] {out}")


# ── Figure 5: Cost Efficiency ──────────────────────────────────────
def fig5_cost(data: dict, speca_list: list[tuple[str, dict]]):
    """Scatter plot: cost vs bugs detected."""
    tools = data["tools"]

    fig, ax = plt.subplots(figsize=(8, 5))

    # RepoAudit (Claude 3.5): $2.54/project × 15 = $38.10 total, 40 TP
    ra = tools["repoaudit_claude35_sonnet"]
    total_cost = ra["avg_cost_per_project"] * 15
    ax.scatter(total_cost, ra["tp"], s=200, c=COLORS["RepoAudit\n(Claude 3.5)"],
               edgecolor="black", zorder=5, label="RepoAudit (Claude 3.5)")
    ax.annotate(f"40 TP\n${total_cost:.0f}", (total_cost, ra["tp"]),
                textcoords="offset points", xytext=(10, -5), fontsize=9)

    # Meta Infer: free (open source)
    ax.scatter(0, 7, s=200, c=COLORS["Meta Infer"],
               edgecolor="black", zorder=5, label="Meta Infer (free)")
    ax.annotate("7 TP\n$0", (0, 7),
                textcoords="offset points", xytext=(10, 5), fontsize=9)

    # CodeGuru: proprietary cost unknown, mark at estimated $50
    ax.scatter(50, 0, s=200, c=COLORS["CodeGuru"],
               edgecolor="black", zorder=5, label="CodeGuru (est. cost)")
    ax.annotate("0 TP\n~$50", (50, 0),
                textcoords="offset points", xytext=(10, 5), fontsize=9)

    # SPECA variants
    max_cost = total_cost
    max_tp = ra["tp"]
    speca_offsets = [(12, 6), (12, -8), (12, -22)]  # stagger annotations
    for idx, (label, sdata) in enumerate(speca_list):
        if sdata.get("tp") is not None and sdata.get("total_cost") is not None:
            cost_val = sdata["total_cost"]
            tp_val = sdata["tp"]
            ax.scatter(cost_val, tp_val, s=300,
                       c=COLORS.get(f"SPECA\n({label})", "#DD8452"),
                       edgecolor="black", zorder=6, marker="*", label=f"SPECA ({label})")
            offset = speca_offsets[idx] if idx < len(speca_offsets) else (12, 0)
            ax.annotate(f"{tp_val} TP, ${cost_val:.0f}",
                        (cost_val, tp_val),
                        textcoords="offset points", xytext=offset, fontsize=9,
                        fontweight="bold",
                        arrowprops=dict(arrowstyle="-", color="#999", lw=0.5) if idx > 0 else None)
            max_cost = max(max_cost, cost_val)
            max_tp = max(max_tp, tp_val)

    ax.set_xlabel("Total Cost (USD)")
    ax.set_ylabel("True Positives")
    ax.set_title("RQ2a: Cost vs Detection Performance\n(15 C/C++ Projects)")
    ax.legend(loc="upper left", fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_xlim(-5, max(60, max_cost + 20))
    ax.set_ylim(-3, max_tp + 8)

    out = FIGURES_DIR / "rq2a_cost_efficiency.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"  [OK] {out}")


# ── Figure 6: Bug Detection Matrix (per-bug × tool) ──────────────
GROUND_TRUTH_PATH = SCRIPT_DIR / "ground_truth_bugs.yaml"


def fig6_bug_detection_matrix(data: dict, speca_list: list[tuple[str, dict]]):
    """Heatmap: individual bugs × tools detection matrix (Issue #96 spec).

    Disputed bugs (no exploit path) are shown with a distinct "TN" marker
    when not detected by SPECA, indicating correct rejection rather than a miss.
    """
    if not GROUND_TRUTH_PATH.exists():
        print("  [SKIP] rq2a_bug_detection_matrix.png (no ground_truth_bugs.yaml)")
        return

    with open(GROUND_TRUTH_PATH) as f:
        gt = yaml.safe_load(f)

    bugs = gt["bugs"]
    tool_names = ["RepoAudit\n(Claude 3.5)", "Meta Infer", "CodeGuru"]
    tool_keys = ["repoaudit_claude35", "meta_infer", "amazon_codeguru"]
    # Add all SPECA model variants as separate columns
    for speca_label, speca_data in speca_list:
        tool_names.append(f"SPECA\n({speca_label})")
        tool_keys.append(f"speca:{speca_label}")
    speca = speca_list[0][1] if speca_list else None

    n_bugs = len(bugs)
    n_tools = len(tool_names)
    # Matrix values: 0=miss, 0.15=disputed TN, 0.5=unknown, 1=detected
    matrix = np.zeros((n_bugs, n_tools))

    # Build per-SPECA-model detected bug sets from summaries
    speca_detected: dict[str, set[str]] = {}
    for speca_label, speca_data in speca_list:
        speca_detected[speca_label] = set(speca_data.get("detected_bugs", []))

    disputed_rows = set()
    bug_labels = []
    for i, bug in enumerate(bugs):
        is_disputed = bug.get("disputed", False)
        label = f"{bug['id']} ({bug['bug_type']})"
        if is_disputed:
            label += " †"
            disputed_rows.add(i)
        bug_labels.append(label)
        det = bug.get("detected_by", {})
        for j, key in enumerate(tool_keys):
            if key.startswith("speca:"):
                # SPECA model variant — use summary's detected_bugs list
                model_label = key.split(":", 1)[1]
                detected_set = speca_detected.get(model_label, set())
                if bug["id"] in detected_set:
                    matrix[i, j] = 1
                elif is_disputed:
                    matrix[i, j] = 0.15  # disputed TN
                else:
                    matrix[i, j] = 0
            else:
                val = det.get(key)
                if val is True:
                    matrix[i, j] = 1
                elif val is False:
                    matrix[i, j] = 0
                else:
                    matrix[i, j] = 0.5  # unknown/null

    fig_width = 8 + max(0, (n_tools - 4) * 1.5)
    fig, ax = plt.subplots(figsize=(fig_width, 16))

    cmap = plt.cm.colors.ListedColormap(["#F0F0F0", "#E8F5E9", "#DDDDDD", "#4C72B0"])
    bounds = [0, 0.1, 0.3, 0.75, 1.0]
    norm = plt.cm.colors.BoundaryNorm(bounds, cmap.N)
    im = ax.imshow(matrix, cmap=cmap, norm=norm, aspect="auto")

    # X-axis labels at bottom
    ax.set_xticks(np.arange(n_tools))
    ax.set_xticklabels(tool_names, fontsize=9, fontweight="bold")
    ax.tick_params(axis="x", bottom=True, top=False, labelbottom=True, labeltop=False)
    ax.set_yticks(np.arange(n_bugs))
    ax.set_yticklabels(bug_labels, fontsize=7)

    for i in range(n_bugs):
        for j in range(n_tools):
            val = matrix[i, j]
            if val == 1:
                symbol, color = "\u2713", "white"
            elif val == 0.15:
                symbol, color = "TN", "#2E7D32"
            elif val == 0:
                symbol, color = "\u2717", "#AAAAAA"
            else:
                symbol, color = "?", "#888888"
            ax.text(j, i, symbol, ha="center", va="center", fontsize=9,
                    color=color, fontweight="bold")

    n_disputed = len(disputed_rows)
    title_note = f"({n_bugs} Ground Truth Bugs \u00d7 Tools"
    if n_disputed > 0:
        title_note += f", {n_disputed} disputed\u2020"
    title_note += ")"
    ax.set_title(f"RQ2a: Bug Detection Matrix\n{title_note}", pad=12)

    # Legend — placed below chart with enough spacing to avoid label overlap
    found = mpatches.Patch(color="#4C72B0", label="Detected")
    missed = mpatches.Patch(color="#F0F0F0", label="Not detected")
    disputed_tn = mpatches.Patch(color="#E8F5E9", label="Disputed TN\u2020")
    unknown = mpatches.Patch(color="#DDDDDD", label="Unknown")
    ax.legend(handles=[found, missed, disputed_tn, unknown], loc="upper center",
              bbox_to_anchor=(0.5, -0.08), ncol=4, fontsize=8,
              frameon=True, edgecolor="#CCCCCC")

    # Footnote
    if n_disputed > 0:
        fig.text(0.5, 0.005,
                 "\u2020 Disputed: no exploit path exists; not detecting = correct TN "
                 "(defensive-coding fix, not exploitable vulnerability)",
                 ha="center", fontsize=7, style="italic", color="#555555")

    out = FIGURES_DIR / "rq2a_bug_detection_matrix.png"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] {out}")


# ── Figure 8: Symmetric Model Comparison ──────────────────────────
def fig_symmetric_comparison(data: dict, speca_list: list[tuple[str, dict]]):
    """Grouped bar chart: same-LLM symmetric comparison.

    Pair 1: DeepSeek R1 (RepoAudit vs SPECA)
    Pair 2: Latest models (RepoAudit Claude 3.7 vs SPECA Sonnet 4.5)
    TP split: GT match (blue) + new bugs (green). FP: red.
    """
    tools_data = data["tools"]
    gt_total = 35

    # Find SPECA variants
    speca_dr1 = None
    speca_s45 = None
    for label, sdata in speca_list:
        if "DeepSeek" in label or "deepseek" in label or "R1" in label or "DR1" in label:
            speca_dr1 = (label, sdata)
        elif "4.5" in label or "Sonnet 4.5" in label:
            speca_s45 = (label, sdata)

    # Build pairs: (pair_label, tool1_data, tool2_data)
    # Each tool: (name, gt_tp, new_tp, fp, precision)
    pairs = []

    # Pair 1: DeepSeek R1
    ra_dr1 = tools_data.get("repoaudit_deepseek_r1", {})
    if ra_dr1.get("tp") is not None and speca_dr1:
        sd = speca_dr1[1]
        pairs.append((
            "DeepSeek R1",
            ("RepoAudit\n(DR1)", min(ra_dr1["tp"], gt_total),
             max(0, ra_dr1["tp"] - gt_total), ra_dr1.get("fp", 0),
             ra_dr1.get("precision", 0)),
            (f"SPECA\n(DR1)", sd.get("gt_tp", min(sd.get("tp", 0), gt_total)),
             sd.get("new_tp", max(0, sd.get("tp", 0) - gt_total)),
             sd.get("fp", 0), sd.get("precision", 0)),
        ))

    # Pair 2: Latest models
    ra_c37 = tools_data.get("repoaudit_claude37_sonnet", {})
    if ra_c37.get("tp") is not None and speca_s45:
        sd = speca_s45[1]
        pairs.append((
            "Latest Models",
            ("RepoAudit\n(Claude 3.7)", min(ra_c37["tp"], gt_total),
             max(0, ra_c37["tp"] - gt_total), ra_c37.get("fp", 0),
             ra_c37.get("precision", 0)),
            (f"SPECA\n(Sonnet 4.5)", sd.get("gt_tp", min(sd.get("tp", 0), gt_total)),
             sd.get("new_tp", max(0, sd.get("tp", 0) - gt_total)),
             sd.get("fp", 0), sd.get("precision", 0)),
        ))

    if not pairs:
        print("  [SKIP] rq2a_symmetric_comparison.png (insufficient SPECA data)")
        return

    # Layout: grouped bars for each pair
    n_pairs = len(pairs)
    fig, axes = plt.subplots(1, n_pairs, figsize=(6 * n_pairs, 5.5), sharey=True)
    if n_pairs == 1:
        axes = [axes]

    for ax, (pair_label, t1, t2) in zip(axes, pairs):
        # t1, t2 = (name, gt_tp, new_tp, fp, precision)
        tools = [t1, t2]
        names = [t[0] for t in tools]
        gt_tps = [t[1] for t in tools]
        new_tps = [t[2] for t in tools]
        fps_vals = [t[3] for t in tools]
        precs = [t[4] for t in tools]

        x = np.arange(len(names))
        w = 0.35

        # GT match (blue) + new bugs (green) stacked
        ax.bar(x - w / 2, gt_tps, w, color="#4C72B0", edgecolor="white", label="GT Match")
        ax.bar(x - w / 2, new_tps, w, bottom=gt_tps, color="#2ecc71",
               edgecolor="white", label="New Bugs")
        ax.bar(x + w / 2, fps_vals, w, color="#C44E52", edgecolor="white", label="FP")

        # Annotations: TP total
        for i in range(len(names)):
            total_tp = gt_tps[i] + new_tps[i]
            if total_tp > 0:
                label_text = str(total_tp) if new_tps[i] == 0 else f"{gt_tps[i]}+{new_tps[i]}"
                ax.text(x[i] - w / 2, total_tp + 0.8, label_text,
                        ha="center", va="bottom", fontsize=10, fontweight="bold")
            if fps_vals[i] > 0:
                ax.text(x[i] + w / 2, fps_vals[i] + 0.8, str(fps_vals[i]),
                        ha="center", va="bottom", fontsize=10, fontweight="bold")
            # Precision annotation above the bars
            prec_val = precs[i]
            max_h = max(total_tp, fps_vals[i])
            ax.text(x[i], max_h + 3.5, f"P={prec_val:.1f}%", ha="center",
                    fontsize=9, fontweight="bold", color="#555")

        ax.set_xticks(x)
        ax.set_xticklabels(names, fontsize=10)
        ax.set_title(f"Pair: {pair_label}", fontsize=11, fontweight="bold")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    axes[0].set_ylabel("Count")
    axes[0].legend(fontsize=8, loc="upper right")

    fig.suptitle("Symmetric Model Comparison: Same LLM Backbone", fontsize=13, fontweight="bold")
    fig.tight_layout(rect=[0, 0.05, 1, 0.93])

    out = FIGURES_DIR / "rq2a_symmetric_comparison.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] {out}")


# ── LaTeX Table: Tool Comparison ─────────────────────────────────
def generate_latex_table(data: dict, speca_list: list[tuple[str, dict]]):
    """Generate rq2a_table.tex (Issue #96 spec)."""
    tools = data["tools"]

    rows = []
    order = [
        ("repoaudit_claude35_sonnet", "RepoAudit (Claude 3.5 Sonnet)"),
        ("repoaudit_deepseek_r1", "RepoAudit (DeepSeek R1)"),
        ("repoaudit_claude37_sonnet", "RepoAudit (Claude 3.7 Sonnet)"),
        ("repoaudit_o3_mini", "RepoAudit (o3-mini)"),
        ("meta_infer", "Meta Infer"),
        ("amazon_codeguru", "Amazon CodeGuru"),
        ("single_function_llm", "Single-function LLM"),
    ]

    for key, label in order:
        t = tools[key]
        tp = t.get("tp", "---")
        fp = t.get("fp", "---")
        prec = t.get("precision")
        prec_s = f"{prec:.2f}\\%" if prec is not None else "---"
        source = t.get("source", "")
        rows.append(f"    {label} & {tp} & {fp} & {prec_s} & {source} \\\\")

    for label, sdata in speca_list:
        if sdata.get("tp") is not None:
            prec_s = f"{sdata['precision']:.2f}\\%" if sdata.get("precision") is not None else "---"
            rows.append(f"    \\textbf{{SPECA ({label})}} & \\textbf{{{sdata['tp']}}} & \\textbf{{{sdata.get('fp', '---')}}} & \\textbf{{{prec_s}}} & This study \\\\")

    if not speca_list:
        rows.append("    \\textbf{SPECA} & \\textbf{TBD} & \\textbf{TBD} & \\textbf{TBD} & This study \\\\")

    latex = (
        "% Auto-generated by benchmarks/rq2a/visualize.py\n"
        "\\begin{table}[htbp]\n"
        "  \\centering\n"
        "  \\caption{RQ2a: Tool Comparison on RepoAudit 15-Project Benchmark}\n"
        "  \\label{tab:rq2a-comparison}\n"
        "  \\begin{tabular}{lcccc}\n"
        "    \\toprule\n"
        "    Tool & TP & FP & Precision & Source \\\\\n"
        "    \\midrule\n"
        + "\n".join(rows) + "\n"
        "    \\bottomrule\n"
        "  \\end{tabular}\n"
        "\\end{table}\n"
    )

    out = FIGURES_DIR / "rq2a_table.tex"
    out.write_text(latex)
    print(f"  [OK] {out}")


# ── Main ───────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="RQ2a visualization")
    parser.add_argument("--speca-results", type=str, default=None,
                        help="Path to single SPECA results JSON (backward compat)")
    parser.add_argument("--speca-multi", nargs="+", metavar="LABEL=PATH",
                        help='Multiple SPECA results: "Sonnet 4.5=path1.json" "Sonnet 4=path2.json"')
    args = parser.parse_args()

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading baselines...")
    data = load_baselines()

    # Build speca_list from either --speca-multi or --speca-results
    speca_list: list[tuple[str, dict]] = []
    if args.speca_multi:
        speca_list = load_speca_multi(args.speca_multi)
    elif args.speca_results:
        speca = load_speca(args.speca_results)
        if speca:
            speca_list = [("default", speca)]

    if speca_list:
        for label, sdata in speca_list:
            print(f"  SPECA ({label}): TP={sdata.get('tp')}, FP={sdata.get('fp')}, Precision={sdata.get('precision')}")
    else:
        print("  SPECA results not available — generating baselines-only figures")

    print("\nGenerating figures...")
    fig1_precision(data, speca_list)
    fig2_tp_fp(data, speca_list)
    fig3_bug_type(data, speca_list)
    fig4_per_project(data, speca_list)
    fig5_cost(data, speca_list)
    fig6_bug_detection_matrix(data, speca_list)
    fig_symmetric_comparison(data, speca_list)
    generate_latex_table(data, speca_list)

    n_figs = len(list(FIGURES_DIR.glob("*.png")))
    n_tex = len(list(FIGURES_DIR.glob("*.tex")))
    print(f"\nDone. {n_figs} figures + {n_tex} LaTeX tables saved to {FIGURES_DIR}")


if __name__ == "__main__":
    main()
