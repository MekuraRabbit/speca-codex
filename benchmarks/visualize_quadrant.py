#!/usr/bin/env python3
"""Generate the spec-driven vs code-driven 4-quadrant comparison figure.

Axes:
  x: Information Representation (code-local <-> spec/property-centric)
  y: Threat Model (implicit <-> explicit)

Usage:
    uv run python3 benchmarks/visualize_quadrant.py
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "results"

plt.rcParams.update({
    "font.size": 11,
    "axes.titlesize": 14,
    "axes.labelsize": 12,
    "figure.dpi": 150,
    "savefig.dpi": 150,
    "font.family": "sans-serif",
})


def main():
    # Tool positions: (x, y) where x=code-to-spec, y=implicit-to-explicit
    # x: 0=code-local, 1=spec-centric
    # y: 0=implicit threat model, 1=explicit threat model
    tools = {
        "Static Analyzers\n(Infer, CodeGuru)": {
            "pos": (0.12, 0.15),
            "color": "#95a5a6",
            "marker": "s",
            "size": 180,
            "label_offset": (0.0, -0.14),
            "label_ha": "center",
        },
        "Single-Function\nLLM": {
            "pos": (0.22, 0.20),
            "color": "#bdc3c7",
            "marker": "D",
            "size": 140,
            "label_offset": (0.10, 0.06),
            "label_ha": "left",
        },
        "RepoAudit\n(LLM-Agent)": {
            "pos": (0.40, 0.35),
            "color": "#4C72B0",
            "marker": "o",
            "size": 200,
        },
        "Fuzzing\n(ChatAFL, AFLNet)": {
            "pos": (0.25, 0.50),
            "color": "#2ecc71",
            "marker": "^",
            "size": 180,
        },
        "SPECA": {
            "pos": (0.85, 0.88),
            "color": "#e8913a",
            "marker": "*",
            "size": 400,
        },
    }

    fig, ax = plt.subplots(figsize=(9, 7))

    # Background quadrants
    ax.axhline(0.5, color="#ddd", linestyle="--", linewidth=1, zorder=0)
    ax.axvline(0.5, color="#ddd", linestyle="--", linewidth=1, zorder=0)

    # Quadrant labels
    ax.text(0.25, 0.02, "Code-Local\nImplicit Threat Model",
            ha="center", va="bottom", fontsize=9, color="#888", style="italic")
    ax.text(0.75, 0.02, "Spec-Centric\nImplicit Threat Model",
            ha="center", va="bottom", fontsize=9, color="#888", style="italic")
    ax.text(0.25, 0.97, "Code-Local\nExplicit Threat Model",
            ha="center", va="top", fontsize=9, color="#888", style="italic")
    ax.text(0.75, 0.97, "Spec-Centric\nExplicit Threat Model",
            ha="center", va="top", fontsize=9, color="#888", style="italic")

    # Plot tools
    for name, info in tools.items():
        x, y = info["pos"]
        ax.scatter(x, y, c=info["color"], marker=info["marker"],
                   s=info["size"], zorder=5, edgecolors="white", linewidth=1.5)

        # Per-tool label offset, or fallback to automatic positioning
        if "label_offset" in info:
            offset_x, offset_y = info["label_offset"]
            ha = info.get("label_ha", "left")
        else:
            offset_x, offset_y = 0.04, 0.04
            ha = "left"
            if x > 0.7:
                offset_x = -0.04
                ha = "right"
            if y > 0.8:
                offset_y = -0.06

        ax.annotate(name, (x, y),
                    xytext=(x + offset_x, y + offset_y),
                    fontsize=9, fontweight="bold",
                    ha=ha, va="center",
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8, edgecolor="#ddd"),
                    arrowprops=dict(arrowstyle="-", color="#999", lw=0.8))

    # Axes
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    ax.set_xlabel("Information Representation\n(Code-Local  $\\longleftrightarrow$  Spec / Property-Centric)",
                  fontsize=12)
    ax.set_ylabel("Threat Model\n(Implicit  $\\longleftrightarrow$  Explicit)",
                  fontsize=12)
    ax.set_title("Security Audit Tool Landscape:\nInformation Representation vs Threat Model Explicitness")

    # Remove numeric ticks
    ax.set_xticks([])
    ax.set_yticks([])

    # Add arrow indicators
    ax.annotate("", xy=(0.95, -0.02), xytext=(0.05, -0.02),
                arrowprops=dict(arrowstyle="->", color="#666", lw=1.5),
                annotation_clip=False)
    ax.annotate("", xy=(-0.02, 0.95), xytext=(-0.02, 0.05),
                arrowprops=dict(arrowstyle="->", color="#666", lw=1.5),
                annotation_clip=False)

    fig.tight_layout()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DIR / "chart_quadrant_comparison.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[quadrant] Saved {out}")


if __name__ == "__main__":
    main()
