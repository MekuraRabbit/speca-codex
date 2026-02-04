---
Description: [WORKER] Invoke the formal-audit skill for a batch of items.
Usage: `/03_auditmap_worker WORKER_ID=... QUEUE_FILE=... [TIMESTAMP=...] [ITERATION=...] [BATCH_SIZE=...] [OUTPUT_FILE=...]`
Example: `/03_auditmap_worker WORKER_ID=0 QUEUE_FILE=outputs/03_QUEUE_0.json TIMESTAMP=1700000000 ITERATION=1 BATCH_SIZE=5 OUTPUT_FILE=outputs/03_AUDITMAP_PARTIAL_W0_1700000000_1.json`
Language: English only.
Execution hint: This worker prompt is invoked by the phase-03 async orchestrator.
---
**Always use /serena for development tasks to keep the workflow efficient.**

# Formal Audit Worker

**Goal**
For each item in the current batch, invoke the `/formal-audit` skill and aggregate the structured JSON results into a single array.

---

## 1. Inputs

1. **Worker Queue File**: `QUEUE_FILE` containing items with `check_id`, `checklist_item`, and resolved `code_scope`.
2. **Batch Size**: `BATCH_SIZE` indicates how many items to process from the queue.
3. **Output File**: `OUTPUT_FILE` path for the aggregated results.

---

## 2. Execution Steps

1. Read `QUEUE_FILE` and select the first `BATCH_SIZE` unprocessed items.
2. For each item, call the `/formal-audit` skill with the item JSON as input.
3. Collect the JSON outputs from each skill invocation into a single list.
4. Write the list to `OUTPUT_FILE` as a JSON array.

---

## 3. Output Format

Write a JSON array of audit result objects to `OUTPUT_FILE`. Each object must conform to the structure defined by the `/formal-audit` skill and include `check_id`, `property_id`, `code_scope`, `final_classification`, `bug_bounty_eligible`, `summary`, and `audit_trail`.

---

## 4. Result Output (STDOUT) — KEEP SHORT

The text written to stdout must be brief (max 8 lines). Include only the batch size, number of items processed, and a short status.
