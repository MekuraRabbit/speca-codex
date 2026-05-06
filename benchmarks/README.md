# SPECA Benchmarks

This directory contains the evaluation harnesses for the two benchmarks reported
in the upstream SPECA paper ([arXiv:2604.26495](https://arxiv.org/abs/2604.26495))
plus an exploratory third track. The numbers below are upstream paper results
kept for reference. This Codex App-compatible fork changes the worker runtime
and does not claim that Codex-run audits reproduce the exact upstream
Claude-run outputs. Summary artifacts, labels, figures, and scripts are retained
where practical, but raw worker logs and model trace logs are intentionally
omitted from this fork. Use [NyxFoundation/speca](https://github.com/NyxFoundation/speca)
when you need the original paper artifact bundle.

## Overview

| Benchmark | Dataset | Targets | Ground Truth | Status |
|---|---|---|---|---|
| **[RQ1](#rq1--sherlock-ethereum-fusaka-audit-contest)** | Sherlock Ethereum Fusaka Audit Contest | 10 production Ethereum clients (Go, Rust, Nim, TypeScript, C) | 15 H/M/L issues from 366 expert submissions | Upstream paper result |
| **[RQ2](#rq2--repoaudit-cc-benchmark)** | RepoAudit (ICML 2025) | 15 OSS C/C++ projects (avg 251K LoC) | 35 non-disputed + 5 disputed bugs | Upstream paper result |
| [RQ2b](#rq2b--profuzzbench-exploratory-not-in-paper) | ProFuzzBench (ChatAFL, NDSS 2024) | 6 text-based protocol implementations | 9 zero-day bugs | Upstream exploratory track |

The detailed tables below are retained as upstream paper context. They are not
validation results for the Codex runner added by this fork.

## Repository Layout

```
benchmarks/
├── README.md              ← you are here
├── data/                  ← input datasets (Sherlock CSV, RepoAudit GT lists)
│   └── rq1/
│       └── sherlock_contest_1140_issues_1766639267091.csv
├── rq1/                   ← RQ1 evaluation code (matchers, recall/precision, FP analysis)
│   ├── cli.py
│   ├── evaluate.py
│   ├── matchers.py
│   ├── analyze_deep.py
│   └── generate_report.py
├── rq2a/                  ← RQ2 evaluation code + published baselines
│   ├── visualize.py
│   ├── evaluate.py
│   ├── analyze_deep.py
│   ├── ground_truth_bugs.yaml
│   ├── published_baselines.yaml
│   └── README.md
├── rq2b/                  ← RQ2b ProFuzzBench (exploratory)
│   ├── visualize.py
│   ├── ground_truth_bugs.yaml
│   ├── published_baselines.yaml
│   └── README.md
├── results/
│   ├── rq1/sherlock_ethereum_audit_contest/   ← 10× audit outputs, labels, charts
│   ├── rq2a/                                  ← per-model SPECA outputs + figures
│   └── rq2b/figures/
├── runners/               ← orchestration helpers (target-cloning, batch dispatch)
├── scripts/
│   └── collect_branch_outputs.py
└── archive/               ← deprecated benchmarks (PrimeVul function-level)
```

## Prerequisites

For upstream-style benchmark reproduction, the legacy Claude workflow may still
be required. Normal Codex App usage should start from the
[top-level Quick Start](../README.md#quick-start).

- Python 3.11+ with `uv` (`pip install uv`)
- Node.js 20+
- Codex CLI for Codex App workflows, or Claude Code CLI for legacy upstream-style
  benchmark reproduction
- `git` for cloning target repositories

Install Python deps once:

```bash
uv sync
```

For RQ2 visualizations only (no SPECA execution), `matplotlib` and `pyyaml` are sufficient — `uv run python3 benchmarks/rq2a/visualize.py` works on a fresh checkout without running the pipeline.

---

## RQ1 — Sherlock Ethereum Fusaka Audit Contest

### Dataset

- **Source.** [Sherlock Ethereum Fusaka Audit Contest #787](https://audits.sherlock.xyz/contests/787).
- **Targets.** 10 Ethereum implementations of EIP-7594 (PeerDAS) and EIP-7691, spanning 5 languages: `alloy_evm_fusaka` (Rust), `c_kzg_4844_fusaka` (C), `grandine_fusaka` (Rust), `lighthouse_fusaka` (Rust), `lodestar_fusaka` (TypeScript), `nethermind_fusaka` (C#), `nimbus_fusaka` (Nim), `prysm_fusaka` (Go), `reth_fusaka` (Rust), `rust_eth_kzg_fusaka` (Rust).
- **Ground truth.** [`benchmarks/data/rq1/sherlock_contest_1140_issues_1766639267091.csv`](data/rq1/sherlock_contest_1140_issues_1766639267091.csv) — 366 contest submissions of which **15 were judged valid** (5 High, 2 Medium, 8 Low).
- **Spec inputs.** EIP-7594 / EIP-7691 plus the consensus-spec PRs they reference (auto-discovered by Phase 01a).

### Reported Numbers (paper, post-Phase 6)

| Metric | Value |
|---|---|
| Phase 5 findings (pre-review) | 102 |
| Phase 6 findings (post-review) | 72 |
| **H/M/L recovered (expert-augmented)** | **15 / 15 (100%)** |
| H/M/L recovered (automated-only) | 8 / 15 (53%) |
| Strict precision (H/M/L match) | 26.4% (19/72) |
| Confirmed-useful precision | 59.7% (43/72) |
| Broad precision (non-FP rate) | 66.7% (48/72) |
| **F1 (broad precision)** | **0.800** (Phase 5 → 6: 0.725 → 0.800) |
| Cluster-level strict precision | 48.7% |
| Novel bugs confirmed by developer fix commits | 4 |

### Reproduction

#### A. Reuse the ten committed audit branches (fastest, no API spend)

The repository ships with the per-target audit outputs already committed to ten dedicated branches (one per implementation). To re-evaluate from those:

```bash
# 1. Fetch the audit branches
git fetch origin \
  alloy_evm_fusaka c_kzg_4844_fusaka grandine_fusaka lighthouse_fusaka \
  lodestar_fusaka nethermind_fusaka nimbus_fusaka prysm_fusaka \
  reth_fusaka rust_eth_kzg_fusaka

# 2. Run the recall + precision evaluator (uses the committed Phase-03/04 outputs)
uv run python3 -m benchmarks.rq1 \
  --branches "alloy_evm_fusaka,c_kzg_4844_fusaka,grandine_fusaka,lighthouse_fusaka,lodestar_fusaka,nethermind_fusaka,nimbus_fusaka,prysm_fusaka,reth_fusaka,rust_eth_kzg_fusaka" \
  --use-llm

# 3. Generate the human-readable report (Markdown + JSON)
uv run python3 benchmarks/rq1/generate_report.py
```

Outputs land in [`benchmarks/results/rq1/sherlock_ethereum_audit_contest/`](results/rq1/sherlock_ethereum_audit_contest/):

- `evaluation_summary.{json,md}` — recall / precision / F1, per-severity breakdown, matched-issue table.
- `phase_comparison.json` — Phase 5 → Phase 6 metric transition.
- `findings_labels.csv` — per-finding labels (`tp`, `tp_info`, `fp_invalid`, ...).
- Per-branch `evaluation_<branch>.json` — per-target detail.
- Charts (regenerated by `generate_report.py`):
  - `chart_phase_comparison.png` — Phase 5 vs Phase 6 precision/recall/F1.
  - `chart_findings_per_issue.png` — property neighborhood histogram.
  - `chart_sankey_flow.png` — property-family → ground-truth-issue flow (visualizes the neighborhood effect from the property side).
  - `chart_per_repo.png` — per-implementation finding distribution.
  - `chart_gate_effectiveness.png` — per-gate FP filter effectiveness.
  - `chart_fp_taxonomy.png` — three-root-cause FP decomposition.
  - `chart_property_type_ablation.png` — Invariant / Pre / Post / Assumption precision.
  - `chart_issue_property_heatmap.png` — issue × property TP matrix across the 10 clients.
  - `chart_label_distribution.png` — per-label count distribution.

#### B. Run SPECA end-to-end against the targets (full reproduction)

```bash
# 1. Clone target implementations and configure scope
#    Each branch contains its own outputs/TARGET_INFO.json + outputs/BUG_BOUNTY_SCOPE.json
git checkout alloy_evm_fusaka

# 2. Run the SPECA pipeline (Phases 01a → 04)
uv run python3 scripts/run_phase.py --target 04 --workers 4 --max-concurrent 64

# 3. Repeat for each of the 10 branches, then re-run the evaluator from step A.
```

Approximate runtime per target (paper numbers, Sonnet 4.5):

| Branch | Phase 03 wall-time | Tokens (in/out) | Cost |
|---|---|---|---|
| alloy_evm_fusaka | 2.4m | 23K / 435K | ~$30–60 |
| c_kzg_4844_fusaka | 4.4m | 13K / 341K | ~$30–60 |
| grandine_fusaka | 3.7m | 35K / 773K | ~$30–60 |
| lighthouse_fusaka | 8.1m | 56K / 1.28M | ~$60–80 |
| nethermind_fusaka | 4.4m | 9K / 224K | ~$30–60 |
| nimbus_fusaka | 3.9m | 30K / 646K | ~$30–60 |
| prysm_fusaka | 4.2m | 54K / 1.36M | ~$60–80 |
| reth_fusaka | 4.3m | 25K / 501K | ~$30–60 |
| ... | | | |

**Total RQ1 budget: ~$400–620** (10 implementations).

#### C. Run on GitHub Actions

Five `workflow_dispatch` workflows make full reproduction one click each:

| Workflow | Purpose |
|---|---|
| [`benchmark-rq1-01-setup.yml`](../.github/workflows/benchmark-rq1-01-setup.yml) | Clone target repos for each audit branch |
| [`benchmark-rq1-02-eval-recall.yml`](../.github/workflows/benchmark-rq1-02-eval-recall.yml) | Run recall evaluator (issue match) |
| [`benchmark-rq1-03-eval-fp.yml`](../.github/workflows/benchmark-rq1-03-eval-fp.yml) | Run FP labeling on novel findings |
| [`benchmark-rq1-035-collect-phase04.yml`](../.github/workflows/benchmark-rq1-035-collect-phase04.yml) | Collect Phase 04 outputs and compute the Phase 5 → 6 delta |
| [`benchmark-rq1-04-report.yml`](../.github/workflows/benchmark-rq1-04-report.yml) | Render `evaluation_summary.md` and the chart set |

### Matching Methodology

Issue matching uses **LLM-assisted semantic matching followed by two-author manual verification** (paper §4.2; initial agreement 93%, disagreements resolved by consensus). A match is accepted only when **both root cause and security impact** align between the SPECA finding and the ground-truth issue. Many-to-one matches (multiple findings → one issue) count the issue as recovered if at least one finding matches; each finding is counted independently for precision.

The matcher is a 3-stage pipeline:

1. **Text similarity** — embedding-cosine over titles + summaries.
2. **Token-overlap** — Jaccard on normalized identifier tokens.
3. **Keyword candidate selection** + LLM adjudication — only invoked for ambiguous candidates.

LLM calls are cached at [`benchmarks/results/rq1/sherlock_ethereum_audit_contest/llm_cache.jsonl`](results/rq1/sherlock_ethereum_audit_contest/llm_cache.jsonl) (and `llm_cache_fp.jsonl` for the FP gate) so re-runs are deterministic and free.

### Finding Labels

Each finding is labeled into one of seven categories (paper Table 3):

| Label | Counts as | Definition |
|---|---|---|
| `tp` | TP | Matches a valid H/M/L contest issue |
| `tp_info` | TP | Real informational/low-severity finding |
| `fixed` | TP | Independently fixed on the target repo (developer fix commit) |
| `partially_fixed` | TP | Partially addressed by a fix commit |
| `potential-info` | TP* | Plausible but unconfirmed observation |
| `fp_invalid` | FP | False positive (invalid reasoning) |
| `fp_review` | FP | False positive flagged by Phase-6 review gate |

Three precision granularities are reported: **strict** (only `tp`), **confirmed-useful** (`tp` + `tp_info` + `fixed` + `partially_fixed`), and **broad** (anything that isn't `fp_*`).

### Re-using RQ1 on a New Audit Contest

The harness is dataset-agnostic. To reuse on, say, a Code4rena or Cantina contest:

1. Export the contest issue list to a CSV with columns matching `benchmarks/data/rq1/sherlock_contest_*.csv`. Required columns: `issue_id`, `severity`, `title`, `body` (root cause + impact narrative).
2. Run the SPECA pipeline against each target implementation (one git branch per target works well; see option B above).
3. Pass `--csv path/to/your_contest.csv` to `benchmarks.rq1` and the matchers will use semantic matching against your issue list.
4. (Optional) Provide labeled human-eval samples via `--human-labels labels.jsonl` ([format](#human-label-format)) to compute precision under your own adjudication rules.

### Human Label Format

```jsonl
{"branch": "alloy_evm_fusaka", "item_id": "PROP-...", "label": true,  "notes": "confirmed bug"}
{"branch": "alloy_evm_fusaka", "item_id": "PROP-...", "label": false, "notes": "design choice"}
```

Required keys: `branch`, `item_id`. Label key (any): `label` / `is_valid_bug` / `is_bug` / `is_true_positive` / `valid` / `bug` / `verdict`. Values: bool, `1`/`0`, `yes`/`no`, `vulnerable`/`clean`. A starter file is at [`benchmarks/human_labels_template.jsonl`](human_labels_template.jsonl).

---

## RQ2 — RepoAudit C/C++ Benchmark

### Dataset

- **Source.** [RepoAudit (Guo et al., ICML 2025)](https://arxiv.org/abs/2501.18160).
- **Targets.** 15 open-source C/C++ projects, average 251K LoC: `libsass`, `linux/sound`, `linux/mm`, `linux/drivers/peci`, `sofa-pbrpc`, `coturn`, `libfreenect`, `Redis`, `shadowsocks-libev`, `icu/i18n`, `imagemagick`, `memcached`, `nfs-ganesha`, `OpenLDAP`, and one Linux kernel sub-tree (see [`rq2a/published_baselines.yaml`](rq2a/published_baselines.yaml)).
- **Ground truth.** 35 non-disputed bugs (NPD / MLK / UAF) confirmed by developer fixes, plus 5 disputed bugs. See [`rq2a/ground_truth_bugs.yaml`](rq2a/ground_truth_bugs.yaml).
- **Baselines.** RepoAudit (Claude 3.5 Sonnet, Claude 3.7 Sonnet, DeepSeek R1, o3-mini), Meta Infer, Amazon CodeGuru — all numbers transcribed from the v3 (camera-ready) RepoAudit paper.

### Reported Numbers (paper)

| Method | TP | FP | Precision | Beyond-GT cand. | Cost |
|---|---|---|---|---|---|
| _Partially controlled (DeepSeek R1)_ | | | | | |
| RepoAudit (DeepSeek R1) | 41 | 6 | 87.2% | (in TP) | $8.55 |
| **SPECA (DeepSeek R1)** | — | 15 | 72.7% | **7** | $93.51 |
| _Latest models_ | | | | | |
| RepoAudit (Claude 3.7 Sonnet) | 40 | 5 | 88.9% | (in TP) | $23.85 |
| **SPECA (Sonnet 4.5)** | — | 6 | **88.9%** | **12** | $81.05 |
| _Other configurations_ | | | | | |
| Amazon CodeGuru | 0 | 18 | 0.0% | 0 | — |
| Meta Infer | 7 | 2 | 77.8% | 0 | free |
| RepoAudit (o3-mini) | 36 | 9 | 80.0% | (in TP) | $4.50 |
| RepoAudit (Claude 3.5 Sonnet) | 40 | 11 | 78.4% | (in TP) | $38.10 |
| **SPECA (Sonnet 4)** | — | 13 | 81.2% | **18** | $100.68 |

> **Per-bug cost.** Sonnet 4.5: ~**$1.69 / bug**. Recall is intentionally not reported because the GT was constructed from RepoAudit's own discoveries (structurally unfair to compare).

Two beyond-GT candidates have been **externally validated**:

- **`PROP-N3-npd-001` (coturn, NPD)** — Level A: bug existed in the analyzed commit, independently fixed in a later release (PR #1841 self-withdrawn after discovering the fix).
- **`PROP-U5-uaf-002` (ICU i18n, UAF race)** — Level B: ICU maintainer approved the corresponding Jira ticket (PR #3921).

### Reproduction

#### A. Visualize from committed SPECA outputs (no API spend)

The three model-configuration runs ship under [`benchmarks/results/rq2a/`](results/rq2a/):

```
results/rq2a/
├── speca/                ← Sonnet 4.5 (primary configuration)
├── speca_sonnet4/        ← Sonnet 4 (intermediate)
├── speca_deepseek_r1/    ← DeepSeek R1 (matched-backbone control)
└── figures/              ← rq2a_*.png (regenerated by visualize.py)
```

Regenerate the paper figures from these:

```bash
# Baseline-only comparison
uv run python3 benchmarks/rq2a/visualize.py

# With SPECA results overlaid (Sonnet 4.5 by default)
uv run python3 benchmarks/rq2a/visualize.py \
  --speca-results benchmarks/results/rq2a/speca/speca_summary.json

# Multi-model comparison (used for the symmetric-comparison and adherence figures)
uv run python3 benchmarks/rq2a/visualize.py \
  --speca-multi \
    "Sonnet 4.5=benchmarks/results/rq2a/speca/speca_summary.json" \
    "Sonnet 4=benchmarks/results/rq2a/speca_sonnet4/speca_summary.json" \
    "DeepSeek R1=benchmarks/results/rq2a/speca_deepseek_r1/speca_summary.json"
```

Generated figures (8 PNG + 1 LaTeX table) land in [`benchmarks/results/rq2a/figures/`](results/rq2a/figures/). The published baselines are read from [`rq2a/published_baselines.yaml`](rq2a/published_baselines.yaml).

#### B. Run SPECA end-to-end on the 15 RepoAudit projects

```bash
# 1. Clone target dataset (RepoAudit benchmark) under target_workspace/
gh workflow run rq2a-01-setup-dataset.yml

# 2. Run audit per project — three model configurations
gh workflow run rq2a-03-audit-map.yml          # Sonnet 4.5 (primary)
gh workflow run rq2a-03-audit-map-sonnet4.yml  # Sonnet 4
gh workflow run rq2a-03-audit-map-deepseek-r1.yml  # DeepSeek R1

# 3. Evaluate (label findings vs. ground truth)
gh workflow run rq2a-04-evaluate.yml
gh workflow run rq2a-04-evaluate-sonnet4.yml
gh workflow run rq2a-04-evaluate-deepseek-r1.yml

# 4. Render figures (or run benchmarks/rq2a/visualize.py locally as in A)
gh workflow run rq2a-02-visualize.yml
```

Or locally:

```bash
# Single project example (libsass)
git clone https://github.com/sass/libsass target_workspace/libsass
cd target_workspace/libsass && git checkout <pinned-commit-from-published_baselines.yaml> && cd ../..
uv run python3 scripts/run_phase.py --target 04 --workers 4
uv run python3 benchmarks/rq2a/evaluate.py --project libsass
```

#### C. Beyond-GT Candidate Review

The 18 author-validated beyond-GT candidates from the Sonnet 4 run are listed in [`benchmarks/results/rq2a/REVIEW_GUIDE.md`](results/rq2a/REVIEW_GUIDE.md) with full provenance and cross-model corroboration. Run

```bash
uv run python3 benchmarks/rq2a/analyze_corroboration.py
```

to regenerate the corroboration matrix (which candidates are detected by ≥2 model configurations).

### Re-using RQ2 on a New Codebase

The harness is C/C++/Rust/Go-agnostic — Phase 02c uses Tree-sitter MCP for symbol resolution. To audit a new project for memory-safety bugs:

1. Add the project's pinned commit to a new entry under `target_workspace/` and write a minimal `outputs/TARGET_INFO.json`.
2. Use the [generic NPD/MLK/UAF property template](rq2a/ground_truth_bugs.yaml) as the starting `outputs/BUG_BOUNTY_SCOPE.json`, or generate properties via Phases 01a–01e from the project's own documentation.
3. Run `scripts/run_phase.py --target 04` and label outputs against your own ground truth using `benchmarks/rq2a/evaluate.py --project <name>`.

---

## RQ2b — ProFuzzBench (Exploratory, Not in Paper)

### Status

⚠️ **This track is exploratory and is not reported in the paper.** It explores whether SPECA's specification-grounded findings are *complementary* to fuzzing-discovered crashes (ChatAFL, NDSS 2024). Results are not yet quantitative; we publish the harness for completeness and to enable follow-up work.

### Dataset

- **Source.** [ChatAFL (Meng et al., NDSS 2024)](https://www.ndss-symposium.org/wp-content/uploads/2024-688-paper.pdf), [ProFuzzBench](https://github.com/profuzzbench/profuzzbench).
- **Subjects.** 6 text-based protocol implementations: Live555 (RTSP), ProFTPD/PureFTPD (FTP), Kamailio (SIP), Exim (SMTP), forked-daapd (DAAP).
- **Ground truth.** 9 zero-day bugs from ChatAFL Table VII; details in [`rq2b/ground_truth_bugs.yaml`](rq2b/ground_truth_bugs.yaml).

### Reproduction

```bash
# Visualize baselines-only
uv run python3 benchmarks/rq2b/visualize.py

# With SPECA results overlaid (when available)
uv run python3 benchmarks/rq2b/visualize.py \
  --speca-results benchmarks/results/rq2b/speca/speca_rq2b.json
```

Workflows: [`rq2b-01-setup-dataset.yml`](../.github/workflows/rq2b-01-setup-dataset.yml), [`rq2b-02-visualize.yml`](../.github/workflows/rq2b-02-visualize.yml).

### Open Items

- File/function/line details for 8 of 9 zero-day bugs require author contact (Ruijie Meng / Marcel Böhme).
- SPECA has not yet been run end-to-end on the 6 protocol implementations; placeholder columns in `ground_truth_bugs.yaml`.

---

## Archived: PrimeVul Function-Level RQ2

A previous function-level RQ2 (PrimeVul, deprecated) lives under [`benchmarks/archive/`](archive/). All current RQs use repository/project-level benchmarks because function-level evaluation does not exercise the cross-function reasoning that distinguishes SPECA from local pattern matchers. Code, results, and workflows are preserved verbatim for historical reference.

---

## Reusing the Framework on Your Own Targets

For external researchers / engineers:

1. **Pick a benchmark template** that matches your target shape:
   - **RQ1-style** (specification + multiple implementations + adjudicated ground-truth issue list) → start from `benchmarks/rq1/`.
   - **RQ2-style** (single project + per-bug ground truth list + published baselines) → start from `benchmarks/rq2a/`.
2. **Drop in your dataset.** Place your issue CSV in `benchmarks/data/<your-bench>/` and your published baselines in YAML mirroring [`rq2a/published_baselines.yaml`](rq2a/published_baselines.yaml).
3. **Wire up SPECA.** Write `outputs/TARGET_INFO.json` (target repo + commit) and `outputs/BUG_BOUNTY_SCOPE.json` (trust model + severity rubric) — see the [top-level Configuration section](../README.md#configuration). One pair of files per target.
4. **Run the pipeline.** `uv run python3 scripts/run_phase.py --target 04 --workers 4`.
5. **Evaluate.** Adapt `evaluate.py` from the closest existing benchmark; the matcher and human-label aggregator (`benchmarks/rq1/`) are dataset-agnostic.
6. **Visualize.** The `visualize.py` scripts in `rq2a/` and `rq2b/` are good starting points — they produce paper-quality figures from a single summary JSON.

The pipeline's design is **domain-agnostic**: STRIDE + CWE Top 25 threat modeling, RFC 2119–derived invariants, and Tree-sitter symbol resolution have no hard-coded language or domain assumptions. We have run it successfully on Ethereum consensus clients, C/C++ memory-safety projects, and (in the archive) Solidity DeFi protocols.

## Citation

If you use this harness or any of the included results, please cite:

```bibtex
@misc{kamba2026speca,
  title         = {Beyond Code Reasoning: A Specification-Anchored Audit Framework for Expert-Augmented Security Verification},
  author        = {Kamba, Masato and Murakami, Hirotake and Sannai, Akiyoshi},
  year          = {2026},
  eprint        = {2604.26495},
  archivePrefix = {arXiv},
  primaryClass  = {cs.CR},
  url           = {https://arxiv.org/abs/2604.26495}
}
```

For RepoAudit baseline numbers also cite Guo et al., *RepoAudit: An Autonomous LLM-Agent for Repository-Level Code Auditing* (ICML 2025, [arXiv:2501.18160](https://arxiv.org/abs/2501.18160)). For the ChatAFL baseline cite Meng et al., NDSS 2024 ([DOI](https://doi.org/10.14722/ndss.2024.24688)).
