Benchmark RQ1/RQ2 Overview

This repo defines two quantitative evaluation tracks:
- RQ1: How well the security agent finds real-world audit contest bugs, including bugs missed by humans.
- RQ2: How well the agent compares to traditional static tools / fuzzing baselines on labeled datasets.

RQ1: Sherlock Audit Contest (Audit Map vs Issues)

Method
- Inputs: audit findings JSON (03_PARTIAL_*.json / 03_AUDITMAP_PARTIAL_*.json) produced by the agent and the Sherlock contest issue CSV.
- Matching: 3-stage matching (text similarity, token overlap, keyword candidate selection + optional LLM adjudication).
- Output: overlap vs new findings, per-branch summaries, matching details.
- Optional: statistical comparison vs a baseline run, and human-label precision on sampled "new" findings.
- Code: see `benchmarks/rq1/` (matchers, stats, evaluate). `benchmarks/rq1/cli.py` is the CLI wrapper.

Core metrics
- overlap_rate: fraction of audit items matched to known issues.
- new_rate: fraction of audit items not matched (candidate novel findings).
- issue_recall: fraction of known issues matched by at least one audit item.
- stage_counts: how many matches came from each matching stage.
- llm_calls: number of LLM adjudications used.
- overlap_rate_ci / new_rate_ci: bootstrap confidence intervals.
- baseline_comparison: McNemar exact test + Cliff's delta effect size vs baseline results (if provided).
- human_eval: precision of sampled items judged true bugs (if labels provided).

How to run (local)
1) Evaluate branches (optionally with LLM)
   uv run python benchmarks/rq1/cli.py \
     --branches "branchA,branchB" \
     --use-llm

2) Compare against a baseline evaluation directory
   uv run python benchmarks/rq1/cli.py \
     --branches "branchA,branchB" \
     --use-llm \
     --baseline-results /path/to/baseline_results_dir

3) Generate human-eval sample (default: new_only)
   uv run python benchmarks/rq1/cli.py \
     --branches "branchA,branchB" \
     --use-llm \
     --human-scope new_only \
     --human-sample-size 100

4) Aggregate human labels (JSONL with branch, item_id, and label/is_bug/etc.)
   uv run python benchmarks/rq1/cli.py \
     --branches "branchA,branchB" \
     --use-llm \
     --human-scope new_only \
     --human-labels /path/to/labels.jsonl \
     --human-labels-report /path/to/labels_report.json

Human label format
- Input: JSONL, one JSON object per line.
- Required keys: "branch", "item_id".
- Label keys (any one): "label", "is_valid_bug", "is_bug", "is_true_positive", "valid", "bug", "verdict".
- Label values accepted: true/false, 1/0, yes/no, vulnerable/clean.

Example label row
{"branch":"branchA","item_id":"123","label":true,"notes":"confirmed bug"}

Template
- benchmarks/human_labels_template.jsonl

Labeling guidance (recommended)
- For new_only sampling: label "true" only if it is a real bug not already in the contest issues.
- Use the audit item text/snippet + file/line to locate code context.
- If unsure, mark false and add a note for adjudication.

Outputs
- benchmarks/results/rq1/sherlock_ethereum_audit_contest/evaluation_summary.json
- benchmarks/results/rq1/sherlock_ethereum_audit_contest/evaluation_<branch>.json
- benchmarks/results/rq1/sherlock_ethereum_audit_contest/human_eval_sample.jsonl (if requested)
- benchmarks/results/rq1/sherlock_ethereum_audit_contest/evaluation_summary.md

Workflow (GitHub Actions)
- .github/workflows/benchmark-rq1-sherlock-eval.yml

RQ2a: Repository-Level Bug Detection (RepoAudit, ICML 2025)

Method
- Benchmark: 15 C/C++ OSS projects (avg 251K LoC)
- Bug types: NPD, MLK, UAF (40 ground truth bugs)
- Baselines: RepoAudit (Claude 3.5/3.7, DeepSeek R1, o3-mini), Meta Infer, Amazon CodeGuru
- Comparison: published paper results (v3 camera-ready) vs SPECA new experiment

How to run
1) Visualize baselines-only:
   uv run python3 benchmarks/rq2a/visualize.py

2) Visualize with SPECA results:
   uv run python3 benchmarks/rq2a/visualize.py --speca-results benchmarks/results/rq2a/speca/speca_summary.json

Outputs
- benchmarks/results/rq2a/figures/*.png (6 figures + 1 LaTeX table)
- benchmarks/rq2a/published_baselines.yaml (paper data)
- benchmarks/rq2a/ground_truth_bugs.yaml (40 bugs, 80% with file/function details)

Workflows
- .github/workflows/rq2a-01-setup-dataset.yml (clone RepoAudit benchmark)
- .github/workflows/rq2a-02-visualize.yml (auto-generate figures)

RQ2b: Dynamic Testing Comparison (ChatAFL, NDSS 2024)

Method
- Benchmark: ProFuzzBench 6 text-based protocol implementations
- Subjects: Live555, ProFTPD, PureFTPD, Kamailio, Exim, forked-daapd
- Baselines: ChatAFL, AFLNet, NSFuzz (9 zero-day bugs)
- Comparison: bug-level cross-matching (crash bugs vs spec violations)

How to run
1) Visualize baselines-only:
   uv run python3 benchmarks/rq2b/visualize.py

2) Visualize with SPECA results:
   uv run python3 benchmarks/rq2b/visualize.py --speca-results benchmarks/results/rq2b/speca/speca_rq2b.json

Outputs
- benchmarks/results/rq2b/figures/*.png (5 figures + 1 LaTeX table)
- benchmarks/rq2b/published_baselines.yaml (paper data)
- benchmarks/rq2b/ground_truth_bugs.yaml (9 zero-day bugs)

Workflows
- .github/workflows/rq2b-01-setup-dataset.yml (clone ProFuzzBench + ChatAFL)
- .github/workflows/rq2b-02-visualize.yml (auto-generate figures)

Archived: RQ2 PrimeVul (deprecated)

The old function-level PrimeVul benchmark has been archived.
- Code: benchmarks/archive/rq2_primevul/
- Results: benchmarks/archive/results_rq2/
- Workflows: benchmarks/archive/workflows/benchmark-rq2-*.yml
- Guide: benchmarks/archive/RQ2_BENCHMARK_GUIDE.md

Notes
- All RQs now use repository/project-level benchmarks (not function-level).
- Baseline results are cited from published papers; only SPECA results are new experiments.
- Issue #96: https://github.com/NyxFoundation/security-agent/issues/96
