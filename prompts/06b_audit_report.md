---
Description: Full audit report generator for current SPECA outputs
Usage: `/07_audit_report OUTPUT_DIR=... [OUTPUT_PATH=...] [TITLE=...]`
Example: `/07_audit_report OUTPUT_DIR="outputs/rehearsal_dvd" OUTPUT_PATH="outputs/rehearsal_dvd/AUDIT_REPORT.md"`
Arguments:
- **$OUTPUT_DIR**  : SPECA run output directory.
- **$OUTPUT_PATH** : Output report path. Default: `$OUTPUT_DIR/AUDIT_REPORT.md`.
- **$TITLE**       : Optional public report title.
---

Generate a publication-ready Markdown security assessment report from current SPECA outputs.

# Data Contract

Resolve `$OUTPUT_DIR` first. Read only run artifacts from that directory:
- `BUG_BOUNTY_SCOPE.json`
- `TARGET_INFO.json`
- `01a_STATE.json`
- `01b_PARTIAL_*.json`
- `01e_PARTIAL_*.json`
- `02c_PARTIAL_*.json`
- `03_PARTIAL_*.json`
- `04_PARTIAL_*.json`
- `05_POC_CANDIDATES.json` when present
- `05_POC_RESULT_*.json` when present
- `graphs/**/*.mmd` only when needed for plain-language specification context

Do not read repository-root `outputs/` as a fallback. Do not use older aggregate output filenames; this prompt is based on the current partial-file schema listed above.

# Privacy And Publication Rules

- Do not include absolute local paths, machine usernames, Codex thread IDs, raw worker logs, app-server metadata paths, or raw partial filenames.
- Treat internal IDs as traceability anchors while drafting, then relabel them as `Finding-01`, `Finding-02`, `Candidate-01`, etc.
- File paths under `TARGET_INFO.local_checkout` may be summarized as affected components. Include short repo-relative paths only when necessary for technical clarity.
- Do not include external service URLs found in logs or local artifacts unless they come from `BUG_BOUNTY_SCOPE.json` or the user explicitly approves them.
- Distinguish tested facts from model-generated candidates. Phase 05 candidates are PoC candidates until a `05_POC_RESULT_*.json` records successful execution.

# Source Mapping

Build an internal data model before drafting:
- Scope and authorization: `BUG_BOUNTY_SCOPE.json` and `TARGET_INFO.json`.
- Specification context: `01a_STATE.json`, `01b_PARTIAL_*.json`, `01e_PARTIAL_*.json`, and graph files.
- Code location context: `02c_PARTIAL_*.json`.
- Audit findings: `03_PARTIAL_*.json` `audit_items[]`.
- Review outcomes: `04_PARTIAL_*.json` `reviewed_items[]`.
- PoC planning and execution: `05_POC_CANDIDATES.json` and `05_POC_RESULT_*.json`.

Join records by `property_id`, with `check_id` and `checklist_id` as compatibility fallbacks. When Phase 05 data is present, index both normalized and original identifiers: `representative_property_id`, `covered_property_ids[]`, `source_items[].property_id`, and `source_items[].original_property_id`. Prefer `source_items[].original_property_id` when linking a PoC candidate back to Phase 03/04 evidence, because Phase 05 may normalize property IDs for challenge grouping.

# Report Structure

## 0. Cover Page And Document Control
- Title: use `$TITLE` or derive a public target label from `TARGET_INFO.target_repo`.
- Date: current date in `YYYY-MM-DD` format.
- Assessment scope: summarize the authorized local target and bounty scope without exposing local paths.
- Commit: use `target_commit_short` when useful; avoid full hashes unless the user asks.
- Disclaimer: findings are candidate security results requiring human validation.

## 1. Executive Summary
- Overall readiness: Ready, Conditional, or Blocked.
- Top findings: list at most five confirmed or potential vulnerabilities.
- Counts: Phase 04 verdict counts and Phase 05 candidate counts.
- Caveat: property-level findings are not necessarily independent vulnerabilities.

## 2. Scope
- In-scope assets and out-of-scope items from `BUG_BOUNTY_SCOPE.json`.
- Target repository and pinned commit from `TARGET_INFO.json`.
- Local checkout statement: say the assessment used a pinned local checkout; do not print absolute paths.

## 3. Methodology
- Explain the SPECA flow: spec discovery, subgraph extraction, property generation, code pre-resolution, audit-map proof attempt, review gates, and PoC candidate selection.
- Note that Codex App runs consume tokens through the local app-server workflow; do not present API cost unless actual API usage is recorded.

## 4. Specification Traceability
- Summarize the major requirement groups from Phase 01b/01e.
- Map requirement groups to implementation concepts from Phase 02c and finding references from Phase 03/04.

## 5. Findings Summary
Include a table:

| Reference | Title | Phase 04 Verdict | Severity | Affected Component | PoC Status |
|-----------|-------|------------------|----------|--------------------|------------|

Use Phase 04 `review_verdict`, `adjusted_severity`, `reviewer_notes`, and Phase 03 `proof_trace` / `attack_scenario`.

## 6. Detailed Findings
For each confirmed or potential finding:
- Reference
- Status and severity
- Specification context
- Root cause
- Impact
- Evidence
- PoC candidate or result, when available
- Recommendation

For `DISPUTED_FP`, `DOWNGRADED`, `NEEDS_MANUAL_REVIEW`, and `PASS_THROUGH`, summarize counts and representative reasons rather than writing full vulnerability sections unless the user asks.

## 7. PoC Candidate Coverage
If Phase 05 outputs exist:
- Candidate count
- Covered property IDs, converted to report references
- Proposed or verified test path, sanitized to repo-relative form
- Execution status from `05_POC_RESULT_*.json`

## 8. Limitations
- State that generated findings require human validation.
- State whether PoCs were implemented and run.
- State any missing inputs or partial phases.

## 9. Recommendations
- Code changes
- Specification clarifications
- Additional tests
- Operational monitoring or bounty-scope follow-up

## 10. Appendix
- Sanitized glossary
- Methodology details
- Traceability notes

# Self-Check

Before finishing:
- Reopen `$OUTPUT_PATH` and confirm all required sections exist.
- Search for forbidden strings: absolute drive roots, `codex_app_threads`, `logs/`, `03_PARTIAL_`, `04_PARTIAL_`, `05_POC_CANDIDATES`, `TARGET_INFO`, `BUG_BOUNTY_SCOPE`, and raw local output paths.
- Confirm all counts match the loaded JSON.
- Confirm every detailed finding references Phase 03/04 evidence, and every PoC statement references Phase 05 data or is clearly marked as proposed.
