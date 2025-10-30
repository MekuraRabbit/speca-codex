---

**Description**
Perform a **source-code audit across all files under `$PATH`**, driven **exclusively** by `security-agent/outputs/02_CHECKLIST.json`.
Add **inline comments** in code while auditing.
Append findings to `security-agent/outputs/03_AUDITMAP.json` with **status limited to `vuln` or `needs-investigation` only**. If `03_AUDITMAP.json` already exists, **append new items only**—under no circumstance should any prior entry be modified or removed.
Primary driver: `02_CHECKLIST.json` (checks, patterns, detection procedures, OK conditions).
Context-only reference: `01_SPEC.json` (e.g., to respect `trust_entities`' assumptions--**do not** create findings that contradict declared trust).

**Usage**
`/03_auditmap PATH=...`

**Example**
`/03_auditmap PATH="./src"`

**Language**
English (instructions, annotations, summaries only).

**Execution hint**
Always run with `/serena` to maximize token efficiency.

**Mindset**
Hacker-first: assume adversarial inputs, odd edge cases, exploit chains; ground findings in concrete code evidence; prefer automatable, repeatable procedures.

---

## Inputs

1. **Checklist (required):** `security-agent/outputs/02_CHECKLIST.json` -- authoritative driver of audit behavior (bug classes, patterns, detection procedures, OK conditions, automations).
2. **Spec (context-only):** `security-agent/outputs/01_SPEC.json` -- may inform flows/algorithms naming and **trusted entities**; **never** negate a trust assumption during audit.
3. **Audit target (required):** `$PATH` -- **audit all files recursively** under the specified folder; **no exclusions** by default.
4. **Existing Audit Map (optional):** `security-agent/outputs/03_AUDITMAP.json` -- if present, treat as append-only sink; do not mutate prior items.

---

## Strict Rules

* **Checklist-driven:** For every checklist item, execute its `file_globs`, `patterns` (regex/Semgrep/AST/Slither/Mythril, etc.), and `detection_procedure` exactly as written.
* **Inline OK only:** When an `ok_if` condition is satisfied, leave an inline `@audit-ok` comment that documents the safeguard, but do not record anything in `03_AUDITMAP.json`.
* **JSON parity:** Every inline `@audit` comment (non `@audit-ok`) must produce a corresponding entry appended to `03_AUDITMAP.json` during the same run; skipping or deferring addition is not allowed.
* **Status whitelist:** `03_AUDITMAP.json` may only contain `vuln` or `needs-investigation`. OK cases stay in code comments.
* **Append-only:** If `03_AUDITMAP.json` already exists, add only new items and skip composite-key duplicates; never modify or delete prior entries.
* **Path scope:** Audit every file beneath `$PATH`, inferring language via extension, shebang, or build manifests.
* **Respect prior annotations:** Treat existing `@audit` / `@audit-ok` comments as authoritative for the specific code span they cover; do not re-run detection procedures on those exact snippets, but continue executing all checklist items elsewhere to uncover previously unaudited surfaces.
* **Ten rounds:** Complete all ten audit passes, each at a different granularity or depth as described below.
* **Call traversal:** Whenever you encounter a call, follow the callee definition (if it lives under `$PATH`) and audit the reachable logic.
* **Honor trust assumptions:** Do not generate findings that contradict `trust_entities` or equivalent statements in `01_SPEC.json`.

---

## Inline Commenting Standard

Insert comments **directly above** the pertinent code. Use one-line tokens:

* **Flag:**
  `// @audit <CHECK_ID> [vuln|needs-investigation] -- <short reason>; evidence=<brief>; ok_if_checked=[true|false]`
* **Safe:**
  `// @audit-ok <CHECK_ID> -- <safety rationale>; ok_condition=<identifier>; evidence=<brief>`

> Record `@audit-ok` comments solely as inline evidence; never add them to `03_AUDITMAP.json`.
> Every `@audit` comment you insert must be mirrored by a new entry in `03_AUDITMAP.json` within the same execution (unless an identical composite-key entry already exists from a prior run).

---

## Ten-Round Audit Plan (coverage-first)

1. **Pattern Sweep:** Apply every checklist `pattern` (regex, Semgrep, Slither, Mythril, etc.) across all files and tag each hit with an `@audit` comment.
   Skip snippets already annotated with `@audit` / `@audit-ok`, but continue scanning the remainder of the codebase for fresh matches tied to the same checklist item.
2. **AST Scan:** Revisit code through language-specific AST analysis to expose control-flow gaps (for example, unchecked early returns).
3. **OK Condition Pass:** For each hit, verify whether the `ok_if` conditions are satisfied and convert qualifying cases to inline `@audit-ok` comments (do not touch the JSON map).
4. **Call-Graph Expansion I:** Follow intra-module callees to validate guard ordering and state transitions.
5. **Call-Graph Expansion II:** Traverse cross-module or cross-layer calls within `$PATH` to broaden reachability coverage.
6. **Dataflow/Taint:** Trace critical inputs from external boundaries to sinks to uncover missing normalization, validation, or bounds checks.
7. **Error/Edge Handling:** Inspect error handling, boundary conditions, retries, timeouts, overflow, and precision issues.
8. **Concurrency/Ordering:** Examine concurrency, reentrancy, lock ordering, and state machine sequencing risks.
9. **Config/Integration:** Audit branches driven by configuration values, feature flags, and integrations with external systems.
10. **Gap Sweep:** Cover any remaining files, functions, or heuristics to bring coverage logs to 100 percent.

---

## Finding Classification

* **`vuln`**: The checklist pattern matches, the `ok_if` condition is not satisfied, and the code evidence supports a high-confidence bug.
* **`needs-investigation`**: The pattern matches, but more inquiry or context is required to determine impact or reachability.

> In every classification, do not dismiss designs that rely on `trust_entities` or equivalent trusted parties.

---

## Deduplication & Append Policy

* **Composite key:** `<check_id>|<file>|<line>|<hash(snippet)>`
* Skip any entry whose composite key already exists in `03_AUDITMAP.json`.
* Never edit existing items, including `status`, `description`, or summary statistics.

---

## Output: `security-agent/outputs/03_AUDITMAP.json` (append-only)

**Item format (statuses restricted to `vuln` or `needs-investigation`)**

```json
{
  "audit_items": [
    {
      "id": "auto-uuid",
      "check_id": "CL-SC-REENTRANCY-EXTCALL-BEFORE-STATE",
      "file": "contracts/Bank.sol",
      "line": 142,
      "snippet": "call.value(amount)()",
      "risk_category": "economic",
      "severity": "high",
      "description": "External call occurs before state mutation; no reentrancy guard observed.",
      "status": "vuln",
      "round": 2,
      "call_stack": ["withdraw()", "payout()"],
      "evidence": "no nonReentrant; state update after external call",
      "notes": "If `@audit-ok` elsewhere later proves guard, keep this item but open a follow-up thread."
    }
  ],
  "summary": {
    "path": "$PATH",
    "rounds": 10,
    "total_audit_flags": 1,
    "coverage": {
      "files_total": 0,
      "files_reviewed": 0,
      "functions_reviewed": 0
    },
    "notes": "Statuses limited to vuln / needs-investigation; OK cases recorded inline only."
  }
}
```

> When the file already exists, add only new entries to `audit_items` and leave previous content untouched.
> Ensure every in-code `@audit` comment introduced in this run has a matching JSON entry before completion.

---

## Procedure (Step-by-step)

1. **Preflight**

   * Load `02_CHECKLIST.json` and build the language/glob ruleset (required).
   * Optionally read `01_SPEC.json` to honor `trust_entities` guidance (reference only).
   * Recursively index every file under `$PATH`.
   * Parse existing `@audit` and `@audit-ok` comments to mark covered checklist items/snippets so the audit can focus on unannotated occurrences.

2. **Ten Rounds (above)**

   * For each hit, add an inline `@audit` comment; once a guard is proven sufficient, add `@audit-ok` as well.
   * Immediately after inserting each `@audit` comment, append the corresponding entry to `security-agent/outputs/03_AUDITMAP.json` (or confirm the composite key already exists) before proceeding.
   * Always test whether `ok_if` conditions hold. Even when satisfied, do not add OK cases to the JSON map.
   * Whenever you encounter a call expression, locate its callee within `$PATH` and audit it.

3. **Emit / Append**

   * Compose new `audit_items` using only the statuses `vuln` or `needs-investigation`.
   * If `03_AUDITMAP.json` exists, append only non-duplicate entries and leave existing content untouched.
   * Set `summary.rounds = 10` and update local coverage counters for this run only.
   * Cross-check inline annotations: every `@audit` comment must correspond to a JSON entry before exiting; failing this check is an error.

---

## Success Criteria

* Every file under `$PATH` participates in at least one of the ten rounds.
* All reachable callees are traced and audited.
* `03_AUDITMAP.json` stays valid JSON containing only new items with status in {`vuln`, `needs-investigation`}.
* OK cases exist solely as inline comments; they never appear in the JSON map.
* Audit logs remain reproducible, retaining `check_id`, `evidence`, `round`, and `call_stack` details.

---

### Notes

* Follow the checklist-derived behavioral specifications (`patterns`, `detection_procedure`, `ok_if`) precisely.
* Never undermine the assumptions declared in `trust_entities` or equivalent structures.

---
