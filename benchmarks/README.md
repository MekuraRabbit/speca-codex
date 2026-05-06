# SPECA Benchmark Harnesses

This directory keeps benchmark and evaluation code inherited from upstream
SPECA where it is useful for running your own experiments. This Codex
App-compatible fork does not bundle upstream rendered paper figures, historical
audit outputs, raw worker logs, or model trace artifacts.

The upstream paper results were produced by NyxFoundation/speca and its runner
setup. Because this fork changes the worker runtime to support Codex App and
`codex app-server`, Codex-run audits from this repository should not be treated
as reproductions of the upstream Claude-run paper results.

For the original research claims and artifact bundle, use:

- [NyxFoundation/speca](https://github.com/NyxFoundation/speca)
- [arXiv:2604.26495](https://arxiv.org/abs/2604.26495)

## What Remains Here

- `data/`: benchmark input datasets and ground-truth metadata where included by
  upstream.
- `rq1/`: RQ1 evaluation scripts for issue matching, recall, precision, and
  false-positive analysis.
- `rq2a/`: RepoAudit evaluation and visualization scripts.
- `rq2b/`: exploratory ProFuzzBench evaluation and visualization scripts.
- `runners/` and `scripts/`: helpers for benchmark orchestration and branch
  output collection.
- `archive/`: deprecated benchmark code retained for reference, without bundled
  generated result artifacts.

Generated files should be written under `benchmarks/results/` during a local or
CI run. The directory is intentionally empty in this fork until you run a
benchmark yourself.

## Codex Fork Notes

Normal Codex App usage should start from the top-level
[Quick Start](../README.md#quick-start). Legacy upstream-style benchmark
reproduction may still require the Claude runner and upstream-specific
configuration.

Use these harnesses only for repositories, systems, or datasets that you own,
maintain, or are explicitly authorized to assess.

## Citation

If your work relies on the upstream SPECA method or benchmark design, cite the
upstream paper:

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
