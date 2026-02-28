# Benchmark Report

Generated: 2026-02-28T00:38:44.430976+00:00

## Dataset

- Path: /Users/hiro/Documents/security-agent/.claude/worktrees/zealous-cohen/benchmarks/data/primevul/primevul_test_paired.jsonl
- Ground-truth samples: 868
- Total samples: 868
- Pair groups: 412 (eligible: 386, skipped: 26)

## Tool Metrics

| Tool | Precision | Recall | F1 | Coverage | TP | FP | TN | FN | Errors |
| ---- | --------- | ------ | -- | -------- | -- | -- | -- | -- | ------ |
| semgrep | 0.000 | 0.000 | 0.000 | 1.000 | 0 | 0 | 433 | 435 | 0 |
| cppcheck | 0.499 | 0.867 | 0.633 | 1.000 | 377 | 379 | 54 | 58 | 2 |
| flawfinder | 0.508 | 0.290 | 0.369 | 1.000 | 126 | 122 | 311 | 309 | 0 |
| codeql | n/a | n/a | n/a | 0.000 | 0 | 0 | 0 | 0 | 0 |
| security_agent | n/a | n/a | n/a | 0.000 | 0 | 0 | 0 | 0 | 0 |
| llm_baseline | 0.000 | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 | 0 | 20 |
| static_baseline | n/a | n/a | n/a | 0.000 | 0 | 0 | 0 | 0 | 0 |

## Tool Metadata

| Tool | Version | Timeout | Limit |
| ---- | ------- | ------- | ----- |
| semgrep | 1.152.0 | 300 | 0 |
| cppcheck | Cppcheck 2.17.1 from cppcheck-wheel 1.5.1 | 30 | 0 |
| flawfinder | 2.0.19 | 30 | 0 |
| llm_baseline | n/a | 120 | 20 |

## Pairwise Correct

## Pairwise Statistics (Security Agent vs Baselines)

- n/a

| Tool | Accuracy | Correct | Scored | Total | Skipped |
| ---- | -------- | ------- | ------ | ----- | ------- |
| semgrep | 0.000 | 0 | 386 | 386 | 0 |
| cppcheck | 0.003 | 1 | 386 | 386 | 0 |
| flawfinder | 0.010 | 4 | 386 | 386 | 0 |
| codeql | n/a | 0 | 0 | 0 | 0 |
| security_agent | n/a | 0 | 0 | 0 | 0 |
| llm_baseline | 0.000 | 0 | 0 | 386 | 386 |
| static_baseline | n/a | 0 | 0 | 0 | 0 |

## Unique Detections (Security Agent)

- Count: 0

## CWE Coverage (Top 10 by vulnerable count)

| CWE | Total | Semgrep Recall | Cppcheck Recall | Flawfinder Recall | LLM Baseline Recall |
| --- | --- | --- | --- | --- | --- |
| CWE-787 | 72 | 0.000 | 0.972 | 0.292 | 0.000 |
| CWE-125 | 47 | 0.000 | 0.872 | 0.234 | 0.000 |
| CWE-703 | 47 | 0.000 | 0.745 | 0.213 | 0.000 |
| CWE-476 | 39 | 0.000 | 0.846 | 0.256 | 0.000 |
| CWE-416 | 29 | 0.000 | 0.931 | 0.207 | 0.000 |
| CWE-200 | 16 | 0.000 | 0.938 | 0.312 | 0.000 |
| CWE-369 | 14 | 0.000 | 0.643 | 0.071 | 0.000 |
| CWE-20 | 14 | 0.000 | 1.000 | 0.429 | 0.000 |
| CWE-119 | 14 | 0.000 | 1.000 | 0.357 | 0.000 |
| CWE-617 | 12 | 0.000 | 0.583 | 0.333 | 0.000 |

## Tool Weaknesses (Top Missed CWEs)

- semgrep: CWE-787 (72), CWE-125 (47), CWE-703 (47), CWE-476 (39), CWE-416 (29)
- cppcheck: CWE-703 (12), CWE-476 (6), CWE-125 (6), CWE-617 (5), CWE-369 (5)
- flawfinder: CWE-787 (51), CWE-703 (37), CWE-125 (36), CWE-476 (29), CWE-416 (23)
- llm_baseline: CWE-787 (72), CWE-125 (47), CWE-703 (47), CWE-476 (39), CWE-416 (29)

## Example Cases (Security Agent Only)

- n/a

## Notes

- codeql: results missing.
- security_agent: results missing.
- llm_baseline: no scored samples (check runner configuration).
- static_baseline: results missing.
