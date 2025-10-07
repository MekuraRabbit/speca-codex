---

**Description:** Investigate whether previously reported vulnerabilities (or patterns) recur in the current workspace. Optionally ingest a dataset file describing historic bugs and hunt for analogous defects across the codebase. Append all validated findings to `security-agent/outputs/03_AUDITMAP.json` without removing existing content.

**Usage:** `/03c_auditissue <PROJECT_ALIAS> [DATASET_PATH]`

**Example:** `/03c_auditissue reth security-agent/datasets/execution_bug_patterns.json`

**Language:** English instructions, annotations, and summaries.

**Execution hint:** Always run with `/serena` for token efficiency.

---

**Goal**

1. Identify the project (`PROJECT_ALIAS`) and its primary domains (execution, consensus, zk, smart-contract, web, devops, etc.).
2. Review historical issues from the optional dataset and determine whether equivalent or near-miss bugs exist in the local codebase.
3. Annotate code with `@audit` (confirmed risk) or `@audit-ok` (guard confirmed) and append structured findings to `03_AUDITMAP.json`.
4. Summarize coverage, residual risks, and next steps without erasing prior audit data.

---

**Arguments**

- `PROJECT_ALIAS`: Human-readable identifier for the current repository (e.g., `reth`, `lighthouse`, `zkRollup`, `frontend-app`). Record it in the audit summary.
- `DATASET_PATH` (optional): Workspace-relative file (JSON/YAML/Markdown/CSV) containing historical vulnerabilities, proofs of concept, issue descriptions, or CVEs. When supplied, parse and mine it for reusable patterns. If omitted, skip dataset-driven similarity search and note "Dataset: not provided" in the report.

---

**Primary Inputs**

1. `security-agent/outputs/01_SPEC.json` (schema `3.0.0-generic`). Use as the canonical specification for normative behaviors, invariants, and threat catalog entries. Abort with a retryable error if missing or schema mismatch.
2. `security-agent/outputs/02_ORDER.json` (schema `1.0.0`) to understand mapped functions per normative.
3. Workspace source code respecting bounty scope rules.
4. Optional dataset supplied via `DATASET_PATH`.
5. Optional knowledge bases (`security-agent/docs/**`, ADRs, metrics guides, runbooks) for additional context.

---

**Bounty Scope & Domain Detection**

1. Resolve audit scope using the first definitive source:
   - `01_SPEC.json` → any `bug_bounty.scope` or `domains[*].bug_bounty.scope` entries.
   - Local `SECURITY.md`, `BUG_BOUNTY.md`, or equivalent policies.
   - Official bounty or security pages for the project.
2. Translate scope into include/exclude globs. Exclude directories outside scope (vendor, third_party, generated, build, docs, examples, etc.) unless explicitly in scope.
3. Detect dominant domains (execution, consensus, zk, smart-contract, web, infra). Use file structure, build manifests, and language cues. Record the classification (and uncertainty) in the audit summary.
4. Fail closed if scope cannot be resolved unambiguously.

---

**Dataset-Driven Bug Mining**

- If `DATASET_PATH` is provided:
  - Validate file existence and parse structure (support JSON, YAML, Markdown tables/lists, CSV). Normalize entries into fields such as `title`, `description`, `affected_components`, `patch_summary`, `cve`, `labels`.
  - Extract keywords, guard conditions, and typical failure modes.
  - Construct search patterns (regex, structural, semantic) and scan the codebase using `rg`, AST tools, or type-aware queries.
  - For each candidate match, inspect call graphs, guard ordering, and error handling to determine equivalence or near-miss status. Document reasoning in `audit_items`.
- If `DATASET_PATH` is absent, state "Dataset: not provided" and proceed with specification- and exploratory-driven auditing.

---

**Specification Alignment**

- Map dataset entries and newly found issues to relevant normative IDs, invariants, or algorithms in `01_SPEC.json`.
- Reuse attack-path identifiers (`threat_catalog.attack_vectors[*].id`) where applicable.
- When specification evidence is missing or ambiguous, mark findings as `"needs-investigation"` and describe required follow-up.

---

**Audit Procedure**

1. Load `02_ORDER.json` to understand existing function mappings; prioritize high-risk entry points, mutators, and interfaces.
2. For each suspicious region:
   - Review existing comments, tests, and guards.
   - Compare implementation against dataset patterns and specification requirements.
   - Insert `@audit` above vulnerable code or `@audit-ok` above sufficient safeguards. Reference local evidence (function names, constants, invariants) rather than external spec repos.
3. For asynchronous/event-driven flows, inspect both registration sites and handlers.
4. Document hypotheses or partial findings with `status = "needs-investigation"` to support iterative audits.

---

**03_AUDITMAP.json Handling**

- When the file exists, load and preserve all current content. Append new `audit_items` and update aggregate fields (`summary`, `high_risk_hotspots`, etc.) without deleting previous entries.
- Each new item must include: `id` (unique), `normative_id` (or `"N/A"`), `ap_id` (or `"N/A"`), `checkpoint` (or `"N/A"`), `file`, `line`, `snippet`, `risk_category`, `description`, `status` (`"Vuln"`, `"ok"`, `"needs-investigation"`), and optional `dataset_reference` fields when derived from the dataset.
- Update `summary` with cumulative metrics (rounds completed, total flags, attack-path coverage summary, dataset usage, scope rules, domain classification, next focus areas).

---

**Outputs & Reporting**

1. Inline code comments (`@audit`, `@audit-ok`) covering every confirmed checkpoint.
2. Updated `security-agent/outputs/02_ORDER.json` with incremented `review_count` values for functions audited during this run and appended attack-path summaries (avoid duplicates).
3. Updated `security-agent/outputs/03_AUDITMAP.json` reflecting appended findings.
4. Console/log summary highlighting:
   - Domains audited, scope sources, dataset usage.
   - New vulnerabilities, safeguards, and open questions.
   - Next focus recommendations.
5. End the run with the single line `AUDIT_ISSUE_DONE`.

---

**Success Criteria**

- Dataset (if provided) is parsed, normalized, and used to drive targeted searches; absence is documented.
- Bounty scope is respected; out-of-scope matches are ignored or noted.
- Every new finding references normative/spec context or dataset evidence.
- `03_AUDITMAP.json` remains valid JSON with appended items only.
- `02_ORDER.json` review counts reflect processed functions and `ordering_strategy.top_attack_paths` includes new paths tied to the current session.
- At least three attack-path narratives are produced when vulnerabilities are confirmed; otherwise explain why fewer paths were identified.
- Final summary clearly states residual risks and future work.

---

**Operational Hints**

- Use `rg` with smart regexes, semantic grep (e.g., `ast-grep`, `comby`), or language-native tooling (`go list`, `cargo check`, `tsc`) to surface pattern matches efficiently.
- Consider configuration files, feature flags, and backward-compatibility shims when porting dataset patterns.
- Keep a changelog of inspected modules to avoid redundant work in subsequent runs.
- When evidence is inconclusive, capture minimal reproducible steps or required instrumentation in the summary.

---
