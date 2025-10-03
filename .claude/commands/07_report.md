---
Description: Bug-Bounty Report Builder
Usage: `/07_report <VULN_ID> <REPORT_TEMPLATE> <BOUNTY_PAGE_URL>`
Example: `/07_report 0023344 security-agent/docs/report_template_ethereum.md https://ethereum.org/en/bug-bounty/`
Arguments:
- **VULN_ID**         : `audit_items[].id` in `03_AUDITMAP.json`
- **REPORT_TEMPLATE** : Path to the Markdown template
                       *(default: `security-agent/docs/report_template_ethereum.md`)*
- **BOUNTY_PAGE_URL** : Bug-bounty rules page
                       *(default: `https://ethereum.org/en/bug-bounty/`)*
---

Generate a complete **Markdown bug-bounty report** for the Ethereum Foundation.
**Always use /serena for these development tasks to maximize token efficiency:**


# 📥 Auto-load from 03_AUDITMAP.json
1. **Read** `security-agent/outputs/03_AUDITMAP.json`.
2. **Locate** the entry where `audit_items[].id == {{VULN_ID}}`.
3. **Extract**
   - `SNIPPET`        <- `audit_items[].snippet`
   - `SRC_FILE`       <- `audit_items[].file`
   - `SRC_FUNCTION`   <- infer the enclosing function or method name (fallback: short descriptive label)
   - `UT_PATH`        <- first `poc_tests[].file` with `"type": "unit"`
   - `IT_PATH`        <- first `integration_tests[].file` (if any)
   - `VULN_TITLE_RAW` <- `audit_items[].description`
   - `VULN_TITLE`     <- text before the first colon (`:`) in `VULN_TITLE_RAW`, or the full string if no colon exists. If empty, craft a concise fallback title without embedding `VULN_ID`.
   - `TITLE_SLUG`     <- `VULN_TITLE` transformed to lowercase snake_case containing only ASCII letters, digits, and underscores (convert spaces/punctuation to underscores, collapse repeats, strip leading/trailing underscores).
4. **If not found** → abort with
   `"Vulnerability '{{VULN_ID}}' not found in 03_AUDITMAP.json"`.

# 🎯 Goal
1. **Read** `{{REPORT_TEMPLATE}}` and fill *all* placeholders while preserving heading order.
2. Use internal data sources (Ethereum specs, audit map, bounty rules) strictly for authoring context—never surface repository paths or filenames in the final report.
   - Pull from `security-agent/docs/ethereum/spec_*`, `security-agent/outputs/01_SPEC.json`, and `security-agent/outputs/03_AUDITMAP.json` as needed, but redact those identifiers from the deliverable.
   - Reference `{{BOUNTY_PAGE_URL}}` for impact & severity details without citing internal shorthand like 03_AUDITMAP/AP/SR.
3. Embed **verbatim PoC code** from sanitized sources:
   - Unit test → `{{UT_PATH}}`
   - Integration test → `{{IT_PATH}}` (if present)
   Provide human-friendly labels and run commands that omit `security-agent/` prefixes or other repository-only context.

# 📤 Output
Write exactly **one Markdown file**:
`security-agent/outputs/report_{{TITLE_SLUG}}.md`
(no extra headings, no missing sections).

# 📝 Mandatory Sections

Must Follow templete

# 🛠️ Generation Workflow
```

1. Parse REPORT\_TEMPLATE → collect placeholders like {{SEVERITY}}, {{POC}}.
2. Determine severity per bounty rules (Impact × Likelihood).
3. Read PoC files (UT_PATH and IT_PATH) and include in fenced code blocks.
4. Grab ~10 lines of source around the vulnerable logic, annotating references using `SRC_FILE` + `SRC_FUNCTION` only (no raw line numbers, GitHub URLs, or absolute paths).
5. Replace all placeholders; verify none remain.
6. Save Markdown to output path.

````

# 🧪 Self-Check
- Re-open the written file → scan for `{{` or `}}`; abort if any remain.
- Confirm the heading sequence matches the template exactly.

# ⛔ Constraints
- **Do not** wrap Markdown in JSON.
- No public URLs for PoC code; assume local testnet execution.
- Never mention internal identifiers like `03_AUDITMAP`, `AP`, `SR`, or any `security-agent/` paths in the generated report.
- All links must be fully-qualified `https://`.

# ✅ Success Criteria
- Entry with `id == VULN_ID` found.
- `report_{{TITLE_SLUG}}.md` created and passes placeholder audit.
- PoCs compile via the project’s test runner, e.g.
  ```bash
  # Unit test
  <runner_for_project> <args_to_run> {{UT_PATH}}
  # Integration test (if present)
  <runner_for_project> <args_to_run> {{IT_PATH}}
````

* Severity is justified per bounty guidelines.

```
