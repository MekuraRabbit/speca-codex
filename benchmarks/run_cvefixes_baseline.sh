#!/usr/bin/env bash
set -euo pipefail

# Run all baseline tools on CVEFixes subset and generate evaluation + graphs.
# Prerequisites:
#   - benchmarks/data/cvefixes/cvefixes_subset_paired.jsonl must exist
#   - semgrep, cppcheck, flawfinder must be installed

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

DATASET="benchmarks/data/cvefixes/cvefixes_subset_paired.jsonl"
RESULTS="benchmarks/results/rq2/cvefixes"
FIGURES="${RESULTS}/figures"

if [ ! -f "${DATASET}" ]; then
  echo "ERROR: Dataset not found: ${DATASET}"
  echo "Run the CVEFixes download pipeline first."
  exit 1
fi

LINES=$(wc -l < "${DATASET}")
echo "=== CVEFixes Baseline Benchmark ==="
echo "Dataset: ${DATASET} (${LINES} samples)"
echo ""

mkdir -p "${RESULTS}" "${FIGURES}"

# Step 1: Run Cppcheck
echo ">>> Step 1/5: Running Cppcheck..."
python3 benchmarks/runners/run_cppcheck.py \
  --dataset "${DATASET}" \
  --output "${RESULTS}/cppcheck_results.json" \
  --timeout 30

# Step 2: Run Flawfinder
echo ""
echo ">>> Step 2/5: Running Flawfinder..."
python3 benchmarks/runners/run_flawfinder.py \
  --dataset "${DATASET}" \
  --output "${RESULTS}/flawfinder_results.json" \
  --timeout 30

# Step 3: Run Semgrep (may produce 0 findings for C/C++)
echo ""
echo ">>> Step 3/5: Running Semgrep..."
if command -v semgrep >/dev/null 2>&1; then
  python3 benchmarks/runners/run_semgrep.py \
    --dataset "${DATASET}" \
    --output "${RESULTS}/semgrep_results.json" \
    --config auto \
    --timeout 60
else
  echo "  WARNING: semgrep not found, skipping."
fi

# Step 4: Evaluate
echo ""
echo ">>> Step 4/5: Running evaluation..."
python3 benchmarks/rq2/evaluate.py \
  --dataset cvefixes \
  --output-dir "${RESULTS}"

# Step 5: Generate graphs
echo ""
echo ">>> Step 5/5: Generating visualizations..."
python3 benchmarks/rq2/visualize.py \
  --metrics "${RESULTS}/metrics.json" \
  --output-dir "${FIGURES}"

echo ""
echo "=== Done ==="
echo "Metrics:  ${RESULTS}/metrics.json"
echo "Figures:  ${FIGURES}/"
