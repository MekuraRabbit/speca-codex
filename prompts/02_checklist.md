---

**Description:** Generate an append-only, automation-friendly code audit checklist sourced strictly from existing security-agent outputs, ensuring every implementation surface described upstream is covered (no skipping "minor" components) and that analogous logic across different languages receives parallel checks.

**Usage:** `/02_checklist`

**Example:** `/02_checklist`

**Language:** English only.

**Execution hint:** Run after `/01_spec` completes so all upstream artefacts are available.

---

# **Checklist Creation Prompt**

**Description**
Create a thorough, code-audit checklist for the target project that engineers can directly apply to the source code base. Enumerate checks for **every** user flow, algorithm, API, module, configuration surface, and dependency captured in upstream artefacts—do not limit coverage to primary or "major" implementations. The checklist must be derived **only** from the following existing artefacts and must be **append-only** if a prior checklist exists:

* `security-agent/outputs/01_SPEC.json`
* `security-agent/outputs/01_SIMILAR_ISSUES.json`
* `security-agent/outputs/01_PAST_REPORTS/*`
* (Optional, if present) existing `security-agent/outputs/02_CHECKLIST.json` to be merged/deduplicated.

**Output (required):** `security-agent/outputs/02_CHECKLIST.json`
**Language:** English only.
**Mindset:** Hacker-first. Assume adversarial inputs, weird edge cases, and creative exploit chains. Seek practical, code-level evidence and automate where possible.

---

## **Inputs & Interpretation Rules**

1. **01_SPEC.json (Authoritative Spec for Behavior & Structure)**

   * Treat user flows, algorithms, APIs, and domain breakdowns as **normative intent**.
   * Parse **domains**, **flows**, **algorithms**, **APIs**, **data models**, and any **NORMATIVE_IDs** or spec IDs present.
   * **Important:** If `trust_entities` (or similar e.g., `trusted_entities`, `trust_assumptions`) are present anywhere in `01_SPEC.json`, you **must not** create checklist items that second-guess or require validation of those trust assumptions. Do **not** propose checks that treat trusted entities as untrusted.

2. **01_SIMILAR_ISSUES.json (Repository Issues/PR signals)**

   * Mine historical symptoms, bug classes, file paths, modules, labels, and regression patterns.
   * Extract repeat offenders, “flaky” areas, and code ownership hints.
   * Use these to **prioritize** checklist items and to propose **automatable patterns** (regex/AST/Semgrep/Slither/Mythril/etc.).
   * When signals come from other projects, assess whether the same flaw could exist here; remap the scenario onto this repository’s architecture, naming, and languages before drafting the checklist item.

3. **01_PAST_REPORTS/* (Audits & Bug Bounty Reports)**

   * Derive **bug-to-code** mappings: *“When code looks like X, suspect bug Y; perform checks Z.”*
   * Record **triage heuristics** and **false-positive reducers** that prior researchers used.
   * Draw explicit connections to functions, files, modules, or patterns when possible.
   * Even if the report is from another project, translate the root cause into this project’s components (match analogous modules, flows, configs) and craft a bespoke checklist entry.

4. **Existing 02_CHECKLIST.json (If any)**

   * Load and **append** without losing prior content.
   * **Deduplicate** by stable `id` + `title` (or hash of `domain + title + languages + patterns`).
   * Update references and counts; keep IDs stable across runs.

---

## **What to Produce**

Build an exhaustive **mapping from code patterns to suspected bugs and verification checks**, covering every spec-identified surface. Adapt lessons from external reports/issues into project-specific language, pointing to this repo’s concrete files, modules, configs, or scripts. If any flow/algorithm/API/config from upstream artefacts lacks a concrete pattern, add a TODO checklist entry with explicit rationale instead of omitting it. For every checklist item:

* Clearly state **bug class**, **risk category**, and **code patterns** to search for (regex/AST/Semgrep/Slither/Mythril queries, file globs, dependency clues).
* Provide a **stepwise detection/verification procedure** an auditor can follow.
* Provide explicit **“OK if …” (safe) conditions** to reduce false positives, such as:

  * Smart contracts: **reentrancy guard present**, call is **internal**, **checks-effects-interactions** ordering is enforced, **non-upgradeable** path, prior **input bounds** or **null checks** exist, etc.
  * Web/backend: **authZ beforehand**, **input normalized**, **prepared statements**, **CSRF/XSRF tokens**, **CSP/CORS** correctly set, **TLS pinning**, etc.
  * ZK: **soundness proofs validated**, **range constraints present**, **no unconstrained witnesses**, **fixed domain separation**, **no Fiat–Shamir misuse**.
  * Systems/infra: **idempotent runbooks**, **least-privilege IAM**, **write once** settings, **explicit bounds/timeouts**, etc.
* When identical or analogous functionality exists across multiple languages/stacks (e.g., Rust + TypeScript clients, Solidity + Cairo contracts), create language-specific checklist entries or extend `languages` and pattern definitions so each implementation variant is explicitly covered.
* **Never include** checks that contradict `trust_entities`. If something is defined as trusted in `01_SPEC.json`, **do not** emit a checklist item that re-validates or undermines that assumption.

---

## **Construction Method (Autonomous Workflow)**

1. **Model the Domains:**
   Enumerate domains from `01_SPEC.json` (e.g., execution, consensus, zk, smart-contract, web, infrastructure). Map each domain’s user flows and algorithms to code surfaces (modules/files/functions), and maintain a coverage tracker so every flow/algorithm/API/config in the spec is accounted for by at least one checklist item (use TODO placeholders with rationale if concrete patterns are unknown).

2. **Derive Candidate Checks:**
   For each user flow & algorithm step, ask: *“What code pattern would implement this? What typical flaws arise here?”* Produce candidates per domain & language, cloning/adapting checks for every language/framework that implements the same logic.

3. **Augment with History:**
   Cross-reference with `01_SIMILAR_ISSUES.json` and `01_PAST_REPORTS/*` to:

   * Add real-world patterns (filenames, functions, libs, configs),
   * Sharpen pattern matchers,
   * Attach evidence references.
   * Re-contextualize cross-project incidents: map their triggering conditions to this codebase’s modules, languages, and configurations so the resulting checklist item is actionable for the current project.

4. **Safety Filters:**

   * Remove any items that rely on **trusted** entities being **untrusted**.
   * Add **OK conditions** (guards/validations/architecture constraints) that make findings **safe**.

5. **Prioritize & Normalize:**
   Assign severity/likelihood/confidence and produce a priority score. Normalize field names and keep IDs stable between runs.

6. **Append & Dedupe:**
   If a prior `02_CHECKLIST.json` exists, merge by stable ID and title; update references, keep historical context.

7. **Coverage Validation:**
   Before writing the file, verify the coverage tracker has no remaining flows/algorithms/APIs/configs without checklist entries; if gaps remain, emit TODO items with rationale and point back to the missing spec component.

---

## **Field Semantics (per checklist item)**

* `id`: Stable slug `CL-<DOMAIN>-<BUG-CLASS>-<SHORT-SLUG>`; reuse the same value across regenerations.
* `title`: Short, actionable description of the risky condition being checked.
* `bug_class`: Canonical vulnerability class (e.g., `reentrancy`, `authz-bypass`, `integer-overflow`, `dos`, `xss`, `crypto-misuse`, `consensus-safety`, etc.); stay consistent with previously used labels.
* `risk_category`: One of `integrity`, `availability`, `confidentiality`, `economic`, `compliance`.
* `languages`: Array of languages targeted by the check, e.g., `['Solidity']`, `['Rust', 'TypeScript']`.
* `file_globs`: Array of glob patterns defining the code search scope, e.g., `['contracts/**/*.sol']`.
* `patterns`: Array of detector objects shaped like `{ "type": "<detector>", "rule": "<query-or-rule>", "comment": "<what-it-catches>" }` for Semgrep, Slither, regex, AST, or other tools.
* `detection_procedure`: Array of numbered-step strings (e.g., "1. ...") guiding the auditor through manual validation.
* `ok_if`: Array of strings describing safeguards or architecture constraints that make the finding acceptable.
* `not_ok_if`: Array of strings highlighting aggravating evidence that confirms the bug.
* `references`: Object containing arrays `spec_normative_ids`, `similar_issues`, and `past_reports` to point back to the source artefacts.
* `severity`: One of `critical`, `high`, `medium`, `low`, `info`.
* `likelihood`: One of `high`, `medium`, `low`.
* `confidence`: One of `high`, `medium`, `low`.
* `priority_score`: Integer 0–100 derived from severity/likelihood/confidence/history signals.
* `automation`: Array of runnable commands or tool invocations, e.g., `"slither . --detect reentrancy-eth"`.
* `notes`: Optional string for extra context or caveats.

---

## **Output Format (simple JSON example)**

**File:** `security-agent/outputs/02_CHECKLIST.json`
**Behavior:** If an older file exists, append new items and deduplicate by `id + title` (prefer existing IDs; update evidence and counts). Do **not** include any item that contradicts `trust_entities` from `01_SPEC.json`.

```json
{
  "metadata": {
    "project_name": "$PROJECT_NAME",
    "generated_at": "2025-10-29T09:00:00Z",
    "sources": [
      "security-agent/outputs/01_SPEC.json",
      "security-agent/outputs/01_SIMILAR_ISSUES.json",
      "security-agent/outputs/01_PAST_REPORTS/"
    ],
    "mode": "append",
    "schema_version": "1.0.0-checklist",
    "language": "rust"
  },
  "checks": [
    {
      "id": "CL-SC-REENTRANCY-EXTCALL-BEFORE-STATE",
      "title": "External call before state update (reentrancy risk)",
      "bug_class": "reentrancy",
      "risk_category": "economic",
      "languages": ["Solidity"],
      "file_globs": ["contracts/**/*.sol"],
      "patterns": [
        {
          "type": "semgrep",
          "rule": "pattern-either: [pattern: |foo() { ... external_call(...); ... state_var = ...; } ]",
          "comment": "External call occurs prior to a state write in same function"
        },
        {
          "type": "slither",
          "rule": "reentrancy-eth",
          "comment": "Use Slither's built-in detector"
        }
      ],
      "detection_procedure": [
        "1. Search for external calls (`call`, `delegatecall`, `transfer`, `send`) preceding state writes.",
        "2. Confirm code path order under all branches; ensure no early returns bypass checks.",
        "3. If hit found, proceed to OK conditions to reduce false positives."
      ],
      "ok_if": [
        "Function is annotated with `nonReentrant` and state writes occur before any external call.",
        "Call target is an internal function only (no external interaction).",
        "Preceded by strict effects-after-checks and no reentrant callbacks possible."
      ],
      "not_ok_if": [
        "Untrusted external call prior to state mutation.",
        "Use of low-level `.call` without checking return value or reentrancy guard."
      ],
      "references": {
        "spec_normative_ids": ["<NORMATIVE_ID-if-present>"],
        "similar_issues": ["GH-1234", "PR-5678"],
        "past_reports": ["report-2023-foo#3.2"]
      },
      "severity": "high",
      "likelihood": "medium",
      "confidence": "high",
      "priority_score": 87,
      "automation": [
        "slither . --detect reentrancy-eth",
        "semgrep --config <ruleset> --lang=solidity"
      ],
      "notes": "Exclude if the callee is in `trust_entities` from 01_SPEC.json."
    }
  ]
}
```

---

## **Authoring Rules (Quality Bar)**

* **Exhaustive coverage:** For each domain/language present in `01_SPEC.json`, enumerate all relevant bug classes and attach concrete code patterns, ensuring every user flow, algorithm, API, configuration, and dependency has at least one checklist (or TODO) entry—never skip a component because it seems minor.
* **Cross-language parity:** Whenever similar behavior exists in multiple languages or stacks, emit separate checks (or multi-language pattern definitions) so each implementation receives dedicated coverage and automation guidance.
* **Project-specific adaptation:** When borrowing insights from other projects’ issues or reports, rewrite the checklist item to reference this repository’s modules, paths, configs, and terminology; avoid generic wording.
* **Actionable & automatable:** Prefer patterns expressible as Semgrep rules, Slither/Mythril detectors, or simple regex/AST walks. Include CLI snippets.
* **De-dup & stability:** Keep IDs stable, prefer update-in-place over churn.
* **False-positive control:** Always include `ok_if` (safe conditions) and `not_ok_if` (aggravators).
* **No trust violations:** Remove any item that treats `trust_entities` as untrusted.
* **Prioritization:** Derive `priority_score` from severity/likelihood/confidence and history (similar issues + past reports).
* **English only.**

---

**Deliverable:** Write the finalized checklist to `security-agent/outputs/02_CHECKLIST.json` exactly in the format above.
