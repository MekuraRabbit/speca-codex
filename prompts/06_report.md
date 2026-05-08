---
Description: Bug-bounty report builder for a reviewed SPECA finding or PoC candidate
Usage: `/06_report OUTPUT_DIR=... REPORT_TYPE=... [CANDIDATE_ID=...] [PROPERTY_ID=...] [SEVERITY=...] [OUTPUT_PATH=...]`
Example: `/06_report OUTPUT_DIR="outputs/rehearsal_dvd" CANDIDATE_ID="POC-truster-unauthorized-token-approval-76774102" REPORT_TYPE="IMMUNEFI" SEVERITY="high"`
Arguments:
- **$OUTPUT_DIR**    : SPECA run output directory containing `TARGET_INFO.json`, `03_PARTIAL_*.json`, `04_PARTIAL_*.json`, and optionally `05_POC_CANDIDATES.json` / `05_POC_RESULT_*.json`.
- **$REPORT_TYPE**   : One of `CANTINA`, `CODE4RENA`, `ETHEREUM`, `IMMUNEFI`, `SHERLOCK`.
- **$CANDIDATE_ID**  : Optional `candidates[].candidate_id` from `05_POC_CANDIDATES.json`.
- **$PROPERTY_ID**   : Optional Phase 04 `reviewed_items[].property_id`; required when `CANDIDATE_ID` is omitted.
- **$SEVERITY**      : Optional override (`critical`, `high`, `medium`, `low`, `informational`).
- **$OUTPUT_PATH**   : Optional report path. Default: `$OUTPUT_DIR/report_<title_slug>.md`.
---

Generate exactly one Markdown bug-bounty report from current SPECA outputs.

# Data Contract

1. Resolve `$OUTPUT_DIR` relative to the current workspace unless it is absolute.
2. Load only files inside `$OUTPUT_DIR`:
   - `TARGET_INFO.json`
   - `03_PARTIAL_*.json` with `audit_items[]`
   - `04_PARTIAL_*.json` with `reviewed_items[]`
   - `05_POC_CANDIDATES.json` when `$CANDIDATE_ID` is provided
   - `05_POC_RESULT_<candidate_id>.json` when present
3. Load the report template from `docs/report_templates/<report_type_lower>.md`.
4. Do not read repository-root `outputs/` as a fallback when `$OUTPUT_DIR` points elsewhere.
5. Do not read target code except for the files named by the selected finding or candidate, and only under `TARGET_INFO.local_checkout`.

# Selection Rules

If `$CANDIDATE_ID` is provided:
1. Find `candidates[]` in `05_POC_CANDIDATES.json` where `candidate_id == $CANDIDATE_ID`.
2. Use its `representative_property_id`, `covered_property_ids`, `source_items`, `target_files`, `attack_summary`, `recommended_output_path`, `run_command`, and matching `05_POC_RESULT_<candidate_id>.json` when available.
3. Join the representative property back to Phase 04 `reviewed_items[]` and Phase 03 `audit_items[]` by indexing all known identifiers: candidate `representative_property_id`, every `covered_property_ids[]` value, every `source_items[].property_id`, and every `source_items[].original_property_id`.
4. Phase 05 may normalize property IDs for challenge grouping. When `source_items[].original_property_id` is present, treat it as the preferred lookup key for the original Phase 03/04 evidence, with the normalized `property_id` as a display/coverage key.
5. If missing, abort with: `Candidate '<id>' not found in 05_POC_CANDIDATES.json`.

If `$PROPERTY_ID` is provided:
1. Find the Phase 04 `reviewed_items[]` entry where `property_id == $PROPERTY_ID`.
2. Use only entries with `review_verdict` equal to `CONFIRMED_VULNERABILITY` or `CONFIRMED_POTENTIAL`, unless the user explicitly asks for a disputed report draft.
3. Join to Phase 03 `audit_items[]` by `property_id`, `check_id`, or `checklist_id`.
4. If missing, abort with: `Property '<id>' not found in 04_PARTIAL_*.json`.

# Report Inputs

Use these current fields when available:
- Phase 03: `classification`, `code_path`, `code_scope`, `proof_trace`, `attack_scenario`, `summary`, `checklist_id`.
- Phase 04: `review_verdict`, `original_classification`, `adjusted_severity`, `reviewer_notes`, `spec_reference`, `final_recommendation`.
- Phase 05 candidate: `candidate_id`, `attack_summary`, `covered_property_ids`, `source_items[].property_id`, `source_items[].original_property_id`, `target_files`, `primary_file`, `primary_symbol`, `recommended_output_path`, `run_command`, `target_local_checkout`.
- Phase 05 result: PoC file path, command, execution status, stdout/stderr summary, and any reproduction notes.
- Target info: `target_repo`, `target_commit`, `target_commit_short`, `local_checkout`, `language`.

# Authoring Rules

- Treat SPECA output IDs and local paths as internal evidence. The public report may mention concise file paths only when the bounty template requires evidence; never include absolute local paths.
- Never include `OUTPUT_DIR`, raw partial filenames, Codex thread IDs, app-server logs, or local machine usernames.
- Do not claim exploitability beyond the Phase 04 verdict and PoC result evidence.
- When `$SEVERITY` is omitted, use Phase 04 `adjusted_severity`; if missing, derive severity from impact and clearly state the rationale.
- If a PoC result is absent, label the reproduction section as a proposed PoC plan rather than a verified exploit.
- All public links must be fully-qualified `https://` links.

# Output

Write exactly one Markdown file:
- `$OUTPUT_PATH` when provided, or
- `$OUTPUT_DIR/report_<title_slug>.md`.

The slug must be lowercase ASCII, use underscores, and keep the filename under 55 characters.

# Required Sections

Follow the selected template's heading order. If the template is sparse, include:

1. Summary
2. Severity
3. Affected Component
4. Root Cause
5. Impact
6. Proof of Concept or Reproduction Plan
7. Recommended Fix
8. Evidence and Scope Notes

# Self-Check

Before finishing:
- Reopen the written file and verify no `{{...}}` placeholders remain.
- Confirm the report does not contain absolute paths, `codex_app_threads`, `logs/`, `03_PARTIAL_`, `04_PARTIAL_`, `05_POC_CANDIDATES`, or `TARGET_INFO`.
- Confirm every claim maps back to Phase 03/04 evidence or Phase 05 PoC evidence.
- Confirm the output file is inside `$OUTPUT_DIR` unless the user supplied an explicit `$OUTPUT_PATH`.
