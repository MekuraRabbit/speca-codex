## 🚀 Claude Code Prompt ― “WHITEHAT 04 Bug‑Bounty Report Builder”

```
# 🏷️ REPORT_TEMPLATE   = security-agent/docs/report_templete_ethereum.md
# 🏷️ BOUNTY_PAGE_URL   = https://ethereum.org/en/bug-bounty/
# 🏷️ VULN_NAME         = {{VULN_NAME}}
# 🏷️ UT_PATH           = {{UT_PATH}}
# 🏷️ IT_PATH           = {{IT_PATH}}
# ==========  PROMPT START  ==========
# Task Name
Generate a Markdown bug‑bounty report file for Ethereum Foundation

# 📥 Auto-load from WHITEHAT_02_AUDITMAP.json
1. **First, read** `security-agent/outputs/WHITEHAT_02_AUDITMAP.json`
2. **Search for** the vulnerability where:
   - `audit_items[].risk_category` or `audit_items[].description` contains `{{VULN_NAME}}`
   - OR a dedicated `vuln_name` field equals `{{VULN_NAME}}`
3. **Extract the following**:
   - `SNIPPET`: from `audit_items[].snippet`
   - `VULN_FILE_LINE`: from `audit_items[].file` + `:L` + `audit_items[].line`
4. **If not found**: abort with error "Vulnerability '{{VULN_NAME}}' not found in WHITEHAT_02_AUDITMAP.json"

# 🎯 Goal
1. **Read** `{{REPORT_TEMPLATE}}` and fill *all* placeholders while strictly preserving its heading order.
2. Pull data from:
   - Specs (`security-agent/docs/ethereum/spec_*`, `security-agent/outputs/WHITEHAT_01_SPEC.json`)
   - Audit map (`security-agent/outputs/WHITEHAT_02_AUDITMAP.json`)
   - Ethereum bounty rules at `{{BOUNTY_PAGE_URL}}` (severity matrix, disclosure rules).
3. Embed **verbatim PoC code** from both:
   - Unit test: `{{UT_PATH}}`
   - Integration test: `{{IT_PATH}}` (if exists)
   with paths & run commands.

# 📥 Input
See variables & files above.

# 📤 Output
Create a **single Markdown file**:
`security-agent/outputs/WHITEHAT_04_REPORT_{{VULN_NAME}}.md`

Must match template exactly—no extra headings, no missing sections.

# 📑 Mandatory Sections  (from template)
1. Summary
2. Severity & Impact (OWASP risk matrix → mapped to {Critical, High, Medium, Low})
3. Reproduction Steps
4. PoC (code fenced)
5. Affected Code (10‑line context around `auto-loaded SNIPPET`)
6. Root Cause Analysis
7. Suggested Fix / Mitigation
8. References
9. Disclosure Policy Acknowledgement

# 🛠️ Generation Workflow
```

1. Parse REPORT\_TEMPLATE → detect placeholders like {{SEVERITY}}, {{POC}}.
2. Determine severity per bounty page:
   Impact × Likelihood → level.
3. Read PoC files:
   - `{{UT_PATH}}` → include between `rust … ` fences as "Unit Test PoC"
   - `{{IT_PATH}}` → include between `rust … ` fences as "Integration Test PoC" (if exists)
4. Snip 10 lines around auto-loaded VULN_FILE_LINE for context block.
5. Fill placeholders → ensure none remain.
6. Write Markdown to output path; output nothing else.

````

# 🧪 Self‑Check
- Reopen written file → scan for `{{` or `}}`; abort if found.
- Confirm heading sequence identical to template.

# ⛔ Constraints
- Do **not** wrap markdown in JSON.
- No public URLs for PoC; local testnet only.
- All links fully‑qualified https.

# ✅ Success Criteria
- Vulnerability found in WHITEHAT_02_AUDITMAP.json using VULN_NAME.
- `.md` file exists & passes placeholder audit.
- PoC compiles via:
  ```bash
  # Unit test
  cargo test --test $(basename {{UT_PATH}} .rs) -- --nocapture
  # Integration test (if exists)
  cargo test --test $(basename {{IT_PATH}} .rs) -- --nocapture
````

* Severity justified per bounty guidelines.

# ==========  PROMPT END  ==========
