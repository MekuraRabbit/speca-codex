#!/usr/bin/env python3
"""Generate a markdown summary for RQ1 evaluation."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

# Ensure project root is on sys.path so `benchmarks.rq1.*` imports work
# when this script is invoked directly (not via `python -m`).
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# AI model used in the experiment
_AI_MODEL = "Claude 4.5 Sonnet"


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def fmt_seconds(value: float | int | None) -> str:
    if value is None:
        return "n/a"
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if seconds < 60:
        return f"{seconds:.0f}s"
    return f"{seconds / 60:.1f}m"


def build_branch_env_table(branches: list[str], collection: dict) -> list[str]:
    manifests = {entry.get("branch"): entry for entry in collection.get("branches", [])}
    lines = [
        "| Branch | Commit | Phase 03 Runtime | Tokens (in/out/total) | Turns | Files |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for branch in branches:
        manifest = manifests.get(branch, {})
        target_info = manifest.get("target_info") or {}
        commit = (
            target_info.get("target_commit_short")
            or manifest.get("commit_short")
            or manifest.get("commit")
            or "n/a"
        )
        timing = manifest.get("phase_log_timing") or {}
        runtime = fmt_seconds(timing.get("estimated_total_seconds"))
        num_turns = timing.get("num_turns")
        num_turns_cell = str(num_turns) if isinstance(num_turns, (int, float)) else "n/a"
        tokens = timing.get("tokens") or {}
        token_in = tokens.get("input_tokens") or tokens.get("prompt_tokens") or 0
        token_out = tokens.get("output_tokens") or tokens.get("completion_tokens") or 0
        token_cache = (tokens.get("cache_read_input_tokens") or 0) + (tokens.get("cache_creation_input_tokens") or 0)
        token_total = tokens.get("total_tokens") or (token_in + token_out + token_cache)
        token_cell = f"{token_in}/{token_out}/{token_total}" if token_total else "n/a"
        files = str(len(manifest.get("files", []))) if manifest else "n/a"
        lines.append(f"| {branch} | {commit} | {runtime} | {token_cell} | {num_turns_cell} | {files} |")
    return lines


# ---------------------------------------------------------------------------
# Chart generation
# ---------------------------------------------------------------------------

_TP_LABELS = {"tp", "tp_info", "potential-info", "fixed", "partially_fixed"}
_FP_LABELS = {"fp_invalid", "fp_review"}


def _generate_charts(
    results_dir: Path,
    phase_cmp: dict,
    labels_csv_path: Path,
) -> list[tuple[str, Path]]:
    """Generate PNG charts. Returns [(description, path), ...]."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("[report] warning: matplotlib not available, skipping charts")
        return []

    charts: list[tuple[str, Path]] = []

    # 1. Overall Phase 03 vs Phase 04 comparison
    cmp = phase_cmp.get("comparison", {})
    p03 = cmp.get("phase_03", {})
    p04 = cmp.get("phase_04", {})
    if p03 and p04:
        path = _chart_phase_comparison(results_dir, p03, p04, plt)
        if path:
            charts.append(("Phase 03 vs Phase 04 — Recall / Precision / F1", path))

    # 2. Per-repository breakdown
    if labels_csv_path.exists():
        verdicts = phase_cmp.get("verdicts", {})
        path = _chart_per_repo(results_dir, labels_csv_path, verdicts, plt)
        if path:
            charts.append(("Per-Repository Findings Breakdown", path))

    return charts


def _chart_phase_comparison(
    results_dir: Path, p03: dict, p04: dict, plt: object,
) -> Path | None:
    """Bar chart: Phase 03 vs Phase 04 for Recall, Precision, F1."""
    import numpy as np

    metrics = ["Recall", "Precision", "F1"]
    phase03_vals = [
        p03.get("recall", 0.0),
        p03.get("precision_auto") or p03.get("precision", 0.0),
        p03.get("f1", 0.0),
    ]
    phase04_vals = [
        p04.get("recall", 0.0),
        p04.get("precision_auto") or p04.get("precision", 0.0),
        p04.get("f1", 0.0),
    ]

    x = np.arange(len(metrics))
    width = 0.32

    fig, ax = plt.subplots(figsize=(7, 4.5))  # type: ignore[attr-defined]
    bars1 = ax.bar(x - width / 2, phase03_vals, width, label="Phase 03 (Audit)", color="#4a86c8")
    bars2 = ax.bar(x + width / 2, phase04_vals, width, label="Phase 04 (After FP Filter)", color="#e8913a")

    ax.set_ylabel("Score")
    ax.set_title(f"SPECA — Phase 03 vs Phase 04\n({_AI_MODEL}, Precision = non-FP rate)")
    ax.set_xticks(x)
    ax.set_xticklabels(metrics)
    ax.set_ylim(0, 1.15)
    ax.legend(loc="upper right")
    ax.grid(axis="y", alpha=0.3)

    # Value labels on bars
    for bar in list(bars1) + list(bars2):
        h = bar.get_height()
        ax.annotate(f"{h:.1%}", xy=(bar.get_x() + bar.get_width() / 2, h),
                    xytext=(0, 4), textcoords="offset points", ha="center", va="bottom", fontsize=9)

    fig.tight_layout()
    out = results_dir / "chart_phase_comparison.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)  # type: ignore[attr-defined]
    return out


def _chart_per_repo(
    results_dir: Path, labels_csv_path: Path, verdicts: dict, plt: object,
) -> Path | None:
    """Grouped horizontal bar chart: Phase 03 vs Phase 04 TP/FP per repo."""
    import numpy as np

    # Load CSV
    rows: list[dict] = []
    with labels_csv_path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            rows.append(row)

    if not rows:
        return None

    # Aggregate per repo: Phase 03 (all) vs Phase 04 (after filter)
    repo_p03: dict[str, dict[str, int]] = {}  # {repo: {TP: n, FP: n}}
    repo_p04: dict[str, dict[str, int]] = {}
    for row in rows:
        repo = row.get("repo", "unknown")
        short = repo.split("/")[-1] if "/" in repo else repo
        label = row.get("auto_label", "unknown")
        fid = row.get("finding_id", "")
        is_filtered = verdicts.get(fid, {}).get("classification") == "filtered"

        if label in _TP_LABELS:
            cat = "TP"
        elif label in _FP_LABELS:
            cat = "FP"
        else:
            continue  # skip unknown for clarity

        # Phase 03: all findings
        repo_p03.setdefault(short, {"TP": 0, "FP": 0})
        repo_p03[short][cat] += 1

        # Phase 04: only surviving findings
        if not is_filtered:
            repo_p04.setdefault(short, {"TP": 0, "FP": 0})
            repo_p04[short][cat] += 1

    # Sort repos by Phase 03 total descending
    repos = sorted(repo_p03.keys(), key=lambda r: sum(repo_p03[r].values()), reverse=True)
    n = len(repos)
    bar_h = 0.35
    y = np.arange(n)

    fig, ax = plt.subplots(figsize=(9, max(3.5, n * 0.7 + 1.5)))  # type: ignore[attr-defined]

    # Phase 03 bars (top row per repo)
    p03_tp = [repo_p03.get(r, {}).get("TP", 0) for r in repos]
    p03_fp = [repo_p03.get(r, {}).get("FP", 0) for r in repos]
    ax.barh(y - bar_h / 2, p03_tp, height=bar_h, color="#4a86c8", label="Phase 03 TP")
    ax.barh(y - bar_h / 2, p03_fp, height=bar_h, left=p03_tp, color="#a3c4e9", label="Phase 03 FP")

    # Phase 04 bars (bottom row per repo)
    p04_tp = [repo_p04.get(r, {}).get("TP", 0) for r in repos]
    p04_fp = [repo_p04.get(r, {}).get("FP", 0) for r in repos]
    ax.barh(y + bar_h / 2, p04_tp, height=bar_h, color="#e8913a", label="Phase 04 TP")
    ax.barh(y + bar_h / 2, p04_fp, height=bar_h, left=p04_tp, color="#f5cfa0", label="Phase 04 FP")

    # Count labels
    for i in range(n):
        # Phase 03
        if p03_tp[i]:
            ax.text(p03_tp[i] / 2, y[i] - bar_h / 2, str(p03_tp[i]),
                    ha="center", va="center", fontsize=8, color="white", fontweight="bold")
        if p03_fp[i]:
            ax.text(p03_tp[i] + p03_fp[i] / 2, y[i] - bar_h / 2, str(p03_fp[i]),
                    ha="center", va="center", fontsize=8, color="#3a5a8c", fontweight="bold")
        # Phase 04
        if p04_tp[i]:
            ax.text(p04_tp[i] / 2, y[i] + bar_h / 2, str(p04_tp[i]),
                    ha="center", va="center", fontsize=8, color="white", fontweight="bold")
        if p04_fp[i]:
            ax.text(p04_tp[i] + p04_fp[i] / 2, y[i] + bar_h / 2, str(p04_fp[i]),
                    ha="center", va="center", fontsize=8, color="#8c5a1a", fontweight="bold")

    ax.set_yticks(y)
    ax.set_yticklabels(repos)
    ax.invert_yaxis()
    ax.set_xlabel("Number of Findings")
    ax.set_title(f"SPECA — Per-Repository: Phase 03 vs Phase 04\n({_AI_MODEL})")
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(axis="x", alpha=0.3)

    fig.tight_layout()
    out = results_dir / "chart_per_repo.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)  # type: ignore[attr-defined]
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate markdown summary for RQ1 evaluation")
    parser.add_argument("--summary", required=True, help="Path to evaluation_summary.json")
    parser.add_argument("--collection", default="", help="Path to collection_summary.json")
    parser.add_argument("--labels-csv", default="", help="Path to findings_labels.csv (recomputes precision)")
    parser.add_argument("--output", required=True, help="Output markdown path")
    args = parser.parse_args()

    summary_path = Path(args.summary)
    summary = load_json(summary_path)
    collection = load_json(Path(args.collection)) if args.collection else {}

    # Recompute precision from labels CSV (picks up human labels)
    if args.labels_csv:
        labels_path = Path(args.labels_csv)
        if labels_path.exists():
            from benchmarks.rq1.evaluate import compute_precision

            prec = compute_precision(labels_path)
            summary["precision"] = prec
            recall = summary.get("recall", 0.0)
            if prec["precision_auto"] > 0 and recall > 0:
                summary["f1"] = round(
                    2 * prec["precision_auto"] * recall / (prec["precision_auto"] + recall), 4,
                )
            else:
                summary["f1"] = 0.0
            summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines: list[str] = []
    lines.append("# RQ1 Evaluation Report")
    lines.append("")
    lines.append(f"- Generated at (UTC): {summary.get('generated_at', 'unknown')}")
    dataset = summary.get("dataset", {})
    lines.append(f"- Dataset: {dataset.get('path', 'unknown')} ({dataset.get('issues_csv_total', '?')} issues in CSV)")
    lines.append(f"- Severity filter: {', '.join(summary.get('severity_filter', []))}")
    lines.append(f"- Audit classifications: {', '.join(summary.get('audit_classifications', []))}")
    lines.append(f"- Branches: {len(summary.get('branches', []))}")
    lines.append(f"- Audit findings: {summary.get('audit_items_total', 0)}")
    lines.append(f"- LLM calls: {summary.get('llm_calls', 0)}")
    lines.append("")

    # Environment
    lines.append("## Experiment Environment")
    metadata = summary.get("run_metadata", {})
    ai_meta = metadata.get("ai", {})
    cli_version = ai_meta.get("version") or metadata.get("ai_version") or ""
    if cli_version:
        lines.append(f"- AI model: {_AI_MODEL} (CLI: {cli_version})")
    else:
        lines.append(f"- AI model: {_AI_MODEL}")
    branches = summary.get("branches", [])
    if collection:
        lines.extend(build_branch_env_table(branches, collection))
    lines.append("")

    # Recall
    issues_total = summary.get("issues_total", 0)
    issues_matched = summary.get("issues_matched", 0)
    recall = summary.get("recall", 0.0)
    lines.append("## Recall")
    lines.append(f"**{issues_matched}/{issues_total} = {recall:.1%}**")
    lines.append("")

    # Severity breakdown
    breakdown = summary.get("severity_breakdown", {})
    if breakdown:
        lines.append("| Severity | Total | Matched | Recall |")
        lines.append("| --- | --- | --- | --- |")
        for sev in ["high", "medium", "low"]:
            stats = breakdown.get(sev, {})
            total = stats.get("total", 0)
            matched = stats.get("matched", 0)
            sev_recall = stats.get("recall", 0.0)
            lines.append(f"| {sev.capitalize()} | {total} | {matched} | {sev_recall:.1%} |")
        lines.append("")

    # Match details
    matches = summary.get("matches", {})
    if matches:
        lines.append("## Matched Issues")
        lines.append("| Issue # | Finding | Confidence |")
        lines.append("| --- | --- | --- |")
        for issue_id, info in sorted(matches.items(), key=lambda x: x[0]):
            finding_id = info.get("finding_id") or "?"
            confidence = info.get("confidence", 0.0)
            lines.append(f"| #{issue_id} | {finding_id} | {confidence:.2f} |")
        lines.append("")

    # Precision
    prec = summary.get("precision", {})
    if prec:
        lines.append("## Precision")
        total_findings = prec.get("total_findings", 0)
        auto_tp = prec.get("auto_tp", 0)
        auto_fp_invalid = prec.get("auto_fp_invalid", 0)
        auto_tp_info = prec.get("auto_tp_info", 0)
        auto_unknown = prec.get("auto_unknown", 0)
        human_tp = prec.get("human_tp", 0)
        human_fp = prec.get("human_fp", 0)
        precision_auto = prec.get("precision_auto", 0.0)
        precision_conservative = prec.get("precision_conservative", 0.0)
        lines.append(f"**Precision (labeled): {precision_auto:.1%}** | Conservative (unknown=FP): {precision_conservative:.1%}")
        lines.append("")
        lines.append("| Category | Count | Precision role |")
        lines.append("| --- | --- | --- |")
        lines.append(f"| Total findings | {total_findings} | |")
        lines.append(f"| TP — H/M/L match (auto) | {auto_tp} | TP |")
        lines.append(f"| TP — info match (auto) | {auto_tp_info} | TP |")
        lines.append(f"| FP — invalid match (auto) | {auto_fp_invalid} | FP |")
        lines.append(f"| TP (human) | {human_tp} | TP |")
        lines.append(f"| FP (human) | {human_fp} | FP |")
        lines.append(f"| Unknown (unlabeled) | {auto_unknown} | — |")
        lines.append("")

    # F1
    f1 = summary.get("f1")
    if f1 is not None:
        lines.append("## F1 Score")
        lines.append(f"**F1 = {f1:.3f}** (recall={recall:.1%}, precision={prec.get('precision_auto', 0.0):.1%})")
        lines.append("")

    # Missed issues
    missed = summary.get("missed_issues", [])
    if missed:
        lines.append("## Missed Issues")
        lines.append("| Issue # | Severity | Title |")
        lines.append("| --- | --- | --- |")
        for m in missed:
            lines.append(f"| #{m.get('issue_id', '?')} | {(m.get('severity') or '').capitalize()} | {m.get('title', '')} |")
        lines.append("")
    elif issues_total > issues_matched:
        lines.append("## Missed Issues")
        lines.append(f"{issues_total - issues_matched} issue(s) not matched by any audit finding.")
        lines.append("")

    # Phase 04 comparison (from phase_comparison.json)
    results_dir = summary_path.parent
    phase_cmp = load_json(results_dir / "phase_comparison.json")
    cmp = phase_cmp.get("comparison", {})
    p03 = cmp.get("phase_03", {})
    p04 = cmp.get("phase_04", {})
    delta = cmp.get("delta", {})
    if p03 and p04:
        lines.append("## Phase 04 FP Filter Comparison")
        lines.append("")
        lines.append("| Metric | Phase 03 | Phase 04 | Delta |")
        lines.append("| --- | --- | --- | --- |")
        lines.append(f"| Findings | {p03.get('total_findings', 0)} | {p04.get('total_findings', 0)} | {delta.get('findings_removed', 0):+d} removed |")
        lines.append(f"| Recall | {p03.get('recall', 0.0):.1%} | {p04.get('recall', 0.0):.1%} | {delta.get('recall_delta', 0.0):+.4f} |")
        p03_prec = p03.get("precision_auto") or p03.get("precision", 0.0)
        p04_prec = p04.get("precision_auto") or p04.get("precision", 0.0)
        prec_delta = delta.get("precision_auto_delta") or delta.get("precision_delta", 0.0)
        lines.append(f"| Precision | {p03_prec:.1%} | {p04_prec:.1%} | {prec_delta:+.4f} |")
        lines.append(f"| F1 | {p03.get('f1', 0.0):.3f} | {p04.get('f1', 0.0):.3f} | {delta.get('f1_delta', 0.0):+.4f} |")
        lost = p04.get("lost_recall_issues", [])
        if lost:
            lines.append(f"\nLost recall issues: {', '.join(f'#{i}' for i in lost)}")
        lines.append("")

    # Ground truth analysis
    gt = cmp.get("ground_truth_analysis") or phase_cmp.get("ground_truth_analysis", {})
    if gt:
        lines.append("## Ground Truth Analysis")
        lines.append("")

        # Label distribution
        label_dist = gt.get("label_distribution", {})
        if label_dist:
            labeled_count = gt.get("labeled_count") or sum(label_dist.values())
            lines.append(f"**{labeled_count} labeled findings**")
            lines.append("")
            lines.append("| Label | Count |")
            lines.append("| --- | --- |")
            for lbl, count in sorted(label_dist.items()):
                lines.append(f"| {lbl} | {count} |")
            lines.append("")

        # Filter effectiveness (supports both old and new field names)
        fe = gt.get("filter_effectiveness") or gt.get("disputed_fp_analysis", {})
        total_filtered = fe.get("total_filtered") or fe.get("total", 0)
        if total_filtered > 0:
            correct_fp = fe.get("correct_fp") or fe.get("correct_filters", 0)
            wrong_tp = fe.get("wrong_tp") or fe.get("wrong_filters", 0)
            other = total_filtered - correct_fp - wrong_tp
            fp_precision = fe.get("filter_precision", 0.0)
            lines.append("### DISPUTED_FP Filter Effectiveness")
            lines.append("")
            lines.append(f"- Total filtered: {total_filtered}")
            lines.append(f"- Correct (true FP): {correct_fp}")
            lines.append(f"- Wrong (true TP filtered): {wrong_tp}")
            lines.append(f"- Other: {other}")
            lines.append(f"- **Filter precision: {fp_precision:.1%}**")
            lines.append("")

        # Confusion matrix
        cm = gt.get("confusion_matrix", {})
        if cm:
            # Collect all ground truth labels across verdicts
            gt_labels = sorted({lbl for counts in cm.values() for lbl in counts})
            lines.append("### Confusion Matrix (Verdict x Ground Truth)")
            lines.append("")
            header = "| Verdict | " + " | ".join(gt_labels) + " | Total |"
            sep = "| --- | " + " | ".join("---" for _ in gt_labels) + " | --- |"
            lines.append(header)
            lines.append(sep)
            for verdict, counts in sorted(cm.items()):
                total = sum(counts.values())
                cells = " | ".join(str(counts.get(lbl, 0)) for lbl in gt_labels)
                lines.append(f"| {verdict} | {cells} | {total} |")
            lines.append("")

        # Per-verdict TP rate (supports both new and old field name)
        vtp = gt.get("verdict_tp_rates") or gt.get("verdict_tp_rate", {})
        if vtp:
            lines.append("### Per-Verdict TP Rate")
            lines.append("")
            lines.append("| Verdict | Total | TP | TP Rate |")
            lines.append("| --- | --- | --- | --- |")
            for verdict, info in sorted(vtp.items()):
                lines.append(f"| {verdict} | {info.get('total', 0)} | {info.get('tp', 0)} | {info.get('tp_rate', 0.0):.1%} |")
            lines.append("")

        # Per-label filter rate (supports both new and old field name)
        lfr = gt.get("label_filter_rates") or gt.get("label_filter_rate", {})
        if lfr:
            lines.append("### Per-Label Filter Rate")
            lines.append("")
            lines.append("| Ground Truth | Total | Filtered | Filter Rate |")
            lines.append("| --- | --- | --- | --- |")
            for lbl, info in sorted(lfr.items()):
                filter_rate = info.get("filter_rate") or info.get("rate", 0.0)
                lines.append(f"| {lbl} | {info.get('total', 0)} | {info.get('filtered', 0)} | {filter_rate:.1%} |")
            lines.append("")

    # Efficiency (from phase_comparison.json)
    eff = phase_cmp.get("efficiency", {})
    e03 = eff.get("phase_03", {})
    e04 = eff.get("phase_04", {})
    if e03 or e04:
        lines.append("## Token Efficiency")
        lines.append("")
        lines.append("| Metric | Phase 03 (Audit) | Phase 04 (Review) |")
        lines.append("| --- | --- | --- |")
        lines.append(f"| Total tokens | {e03.get('total_tokens', 0):,} | {e04.get('total_tokens', 0):,} |")
        lines.append(f"| Total time (sum of batches) | {e03.get('total_secs', 0):.0f}s | {e04.get('total_secs', 0):.0f}s |")
        lines.append(f"| Items | {e03.get('total_findings', 0)} findings | {e04.get('total_reviews', 0)} reviews |")
        lines.append(f"| **Tokens/item** | **{e03.get('tokens_per_finding', 0):,}** | **{e04.get('tokens_per_review', 0):,}** |")
        lines.append(f"| **Secs/item** | **{e03.get('secs_per_finding', 0):.1f}s** | **{e04.get('secs_per_review', 0):.1f}s** |")
        lines.append("")

    # Metadata — reference files instead of inlining
    lines.append("## Data Files")
    lines.append("")
    lines.append(f"- Evaluation summary: `{summary_path.name}`")
    if args.collection:
        lines.append(f"- Collection summary: `{Path(args.collection).name}`")
    if (results_dir / "phase_comparison.json").exists():
        lines.append("- Phase comparison: `phase_comparison.json`")
    if (results_dir / "findings_labels.csv").exists():
        lines.append("- Findings labels: `findings_labels.csv`")
    if (results_dir / "run_metadata.json").exists():
        lines.append("- Run metadata: `run_metadata.json`")
    lines.append("")

    # Generate charts
    labels_csv_path = Path(args.labels_csv) if args.labels_csv else results_dir / "findings_labels.csv"
    chart_paths = _generate_charts(results_dir, phase_cmp, labels_csv_path)
    if chart_paths:
        lines.append("## Charts")
        lines.append("")
        for desc, path in chart_paths:
            rel = path.name
            lines.append(f"### {desc}")
            lines.append(f"![{desc}]({rel})")
            lines.append("")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    print(f"[report] wrote {output_path}")
    for desc, path in chart_paths:
        print(f"[report] chart: {path}")


if __name__ == "__main__":
    main()
