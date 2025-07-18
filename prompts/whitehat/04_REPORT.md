## 🚀 Claude Code Prompt ― “WHITEHAT 04 Bug‑Bounty Report Builder”

```
# 🏷️ REPORT_TEMPLATE   = security-agent/docs/report_templete_ethereum.md
# 🏷️ BOUNTY_PAGE_URL   = https://ethereum.org/en/bug-bounty/
# 🏷️ VULN_NAME         = DoSUnboundedImport
# 🏷️ SNIPPET           = "fn import_transactions("
# 🏷️ VULN_FILE_LINE    = crates/net/network/src/transactions/mod.rs
# 🏷️ POC_TEST_FILE     = crates/net/network/src/transactions/it_poc_dos_unbounded_import.rs
# ==========  PROMPT START  ==========
# Task Name
Generate a Markdown bug‑bounty report file for Ethereum Foundation

# 🎯 Goal
1. **Read** `{{REPORT_TEMPLATE}}` and fill *all* placeholders while strictly preserving its heading order.
2. Pull data from:
   - Specs (`security-agent/docs/ethereum/spec_*`, `security-agent/outputs/WHITEHAT_01_SPEC.json`)
   - Audit map (`security-agent/outputs/WHITEHAT_02_AUDITMAP.json`)
   - Ethereum bounty rules at `{{BOUNTY_PAGE_URL}}` (severity matrix, disclosure rules).
3. Embed **verbatim PoC code** from `{{Poc_TEST_FILE}}` with path & run command.

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
5. Affected Code (10‑line context around `{{SNIPPET}}`)
6. Root Cause Analysis
7. Suggested Fix / Mitigation
8. References
9. Disclosure Policy Acknowledgement

# 🛠️ Generation Workflow
```

1. Parse REPORT\_TEMPLATE → detect placeholders like {{SEVERITY}}, {{POC}}.
2. Determine severity per bounty page:
   Impact × Likelihood → level.
3. Read POC\_TEST\_FILE → include between `rust … ` fences.
4. Snip 10 lines around VULN\_FILE\_LINE for context block.
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
- `.md` file exists & passes placeholder audit.
- PoC compiles via:
  ```bash
  cargo test --test $(basename {{Poc_TEST_FILE}} .rs) -- --nocapture
````

* Severity justified per bounty guidelines.

# ==========  PROMPT END  ==========