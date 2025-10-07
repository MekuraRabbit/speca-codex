---

**Description:** Audit local implementation corresponding to one or more `normative_spec.id` values defined in `security-agent/outputs/01_SPEC.json`. Use `02_ORDER.json` to determine the exact function order, add inline `@audit` / `@audit-ok` comments, append findings to `security-agent/outputs/03_AUDITMAP.json` without deleting existing entries, and increment `review_count` in `02_ORDER.json`.

**Usage:** `/03_auditmap <NORMATIVE_IDS> [KNOWN_BUGS_PATH]`

**Example:** `/03_auditmap "TX-ADMISSION,DA-SAMPLING" security-agent/docs/bugs/shared_findings.json`

**Language:** English instructions, annotations, and summaries.

**Execution hint:** Always run with `/serena` for token efficiency.

---

**Strict Rules**

• **Workspace only** — Never cite external specification repositories or third-party sources inside code annotations. Reference local evidence and the canonical spec JSON only.
• **Scope fidelity** — Audit exclusively within bounty-defined include globs. Treat directories outside scope as off-limits (unless explicitly included by policy).
• **Source of truth** — Load `security-agent/outputs/01_SPEC.json` (schema `3.0.0-generic`) at start. Treat it as the authoritative registry for normatives, algorithms, invariants, security requirements, and threat catalog entries. Abort with a retryable error if the file is missing, malformed, or incorrect schema.
• **Attack-path priority** — For each audited normative, evaluate every applicable entry under `threats.attack_paths` from `01_SPEC.json`. For every relevant checkpoint, annotate the corresponding code with `@audit` or `@audit-ok`. Provide justification when checkpoints are not applicable.
• **No drift** — Preserve existing content in `security-agent/outputs/03_AUDITMAP.json`; only append new findings or update aggregate statistics.

---

**Goal**

Given `NORMATIVE_IDS`, sequentially audit the associated local functions (ordered via `02_ORDER.json`), enrich code with inline annotations, update `03_AUDITMAP.json`, and keep `02_ORDER.json` in sync while covering all relevant attack-path checkpoints and documenting risk insights.

---

**Inputs**

1. **Normatives:** `NORMATIVE_IDS` (comma-separated). Use `*` to request all IDs in `01_SPEC.json`.
2. **Spec:** `security-agent/outputs/01_SPEC.json` (schema `3.0.0-generic`).
3. **Order map:** `security-agent/outputs/02_ORDER.json` (one `audit_chunk` per normative with local `functions`).
4. **Risk knowledge base:** `security-agent/docs/**` or domain-specific references in the repo.
5. **Known bugs database (optional):** file supplied as `KNOWN_BUGS_PATH`. If omitted, record "Bug DB: not provided" in the audit summary.
6. **Static call graph (optional):** `{{STATIC_CALLGRAPH}}` (`NONE` to derive internally).

---

**Bounty Scope — Resolution & Enforcement**

* Resolve scope using (first definitive source wins):
  1. `01_SPEC.json` → `bug_bounty.scope` / `domains[*].bug_bounty.scope`
  2. Local `SECURITY.md` / `BUG_BOUNTY.md` / `SECURITY_POLICY`
  3. Official bounty or security program page
* Materialize explicit include/exclude globs (language-, stack-, or domain-specific). Examples: execution (`./core/**`, `./eth/**`, `./execution/**`), consensus (`./beacon/**`, `./consensus/**`, `./p2p/**`), web (`./apps/**`, `./api/**`), etc.
* Exclude by default: `vendor/`, `third_party/`, `generated/`, `out/`, `dist/`, `build/`, `target/`, `mocks/`, `test/`, `docs/`, unless policy explicitly includes them.
* Fail closed if scope cannot be uniquely resolved.
* Append scope rules & citations to the audit summary in `03_AUDITMAP.json`.

---

**Layer & Normative Matching**

* Detect repository domains/layers (execution, consensus, zk, smart-contract, web, infrastructure, devops) using directory heuristics, build manifests, or language cues.
* For each normative ID:
  * Confirm it aligns with detected domains; otherwise record it under “Unmapped normative IDs (layer mismatch)” and skip auditing.
  * Load normative context: `summary`, `procedure`, `inputs`, `errors`, `invariants`, `security_requirements`, `attack_paths`, and any related algorithms.

---

**Function Selection (from `02_ORDER.json`)**

* Locate the `audit_chunk` whose title starts with `§ <ID> —`.
* Use the provided `functions` list (file + line) as the authoritative review order.
* Filter each entry through bounty scope rules; note exclusions.
* If a normative ID is missing in `02_ORDER.json`, attempt bounded discovery (AST search, call graph hints) within scope. If no candidates found, record under “Unmapped normative IDs (no local functions found)”.

---

**Audit & Annotation Procedure**

1. Load the normative context from `01_SPEC.json` along with relevant `attack_paths` checkpoints.
2. Gather supporting intelligence from documentation, risk playbooks, and optional bug database entries.
3. Traverse each function in the prescribed order:
   * Evaluate checkpoints and invariants; insert `@audit` or `@audit-ok` inline comments directly above the relevant code segments.
   * Reference local evidence (function names, constants, guard conditions) instead of external spec repositories.
   * Note assumptions, TODOs, or open questions inline when status is `needs-investigation`.
4. Increment `review_count` for the function in `02_ORDER.json` after annotation.
5. Capture risk reasoning (DoS, integrity, confidentiality, economic, compliance) tied to attack paths.

---

**Known Bugs Database Integration**

* If `KNOWN_BUGS_PATH` provided:
  * Parse structure (JSON/YAML/Markdown/CSV) to extract bug descriptors, affected components, guard deltas, CVEs.
  * Cross-reference entries during auditing; if a pattern matches, cite `dataset_reference` in findings.
  * Document how each bug pattern was evaluated (matched, partially matched, not observed).
* If omitted, record “Bug DB: not provided” in summary.

---

**Recommended Trap Families (adaptable by domain)**

* **Cross-layer / cross-service interfaces** — Validate authentication, payload schema, replay tolerance, timeout handling.
* **Peer-to-peer & networking** — Check handshake validation, resource limits, gossip filters, partial connectivity resilience.
* **Resource exhaustion & DoS** — Identify unbounded loops, allocations, retries, rate-limit gaps.
* **State transitions & consensus** — Review fork-choice decisions, state mutation ordering, rollback/reorg paths, recovery logic.
* **Data availability & storage** — Validate indexing, caching, erasure coding, redundancy checks.
* **API / schema drift** — Inspect JSON/REST/GraphQL bindings, streaming lifecycles, optional fields vs nil/empty distinctions.
* **Observability & ops** — Ensure metrics/logging doesn’t leak secrets and supports alerting on identified attack paths.

Capture emergent hypotheses in audit items for follow-up even if immediate evidence is inconclusive.

---

**Outputs**

1. Inline source comments (`@audit`, `@audit-ok`) per evaluated checkpoint.
2. Updated `security-agent/outputs/02_ORDER.json` reflecting incremented `review_count` and appended narratives in `ordering_strategy.top_attack_paths` (avoid duplicates; annotate new paths only).
3. Updated `security-agent/outputs/03_AUDITMAP.json` with appended findings.
4. Optional per-ID report: `security-agent/outputs/03_AUDITMAP_<ID>.json` if granular exports are needed.
5. Top attack paths (≥3) derived from audited functions, each listing entry → sink and succinct `risk_reason` (≤40 words) tied to `ap_id` where applicable.

---

**03_AUDITMAP.json Schema Expectations**

```jsonc
{
  "audit_items": [
    {
      "id": "auto-uuid",
      "normative_id": "<ID>",
      "ap_id": "AP-1",
      "checkpoint": "C1",
      "file": "path/to/file.go",
      "line": 142,
      "snippet": "if !guard { return ErrEarly }",
      "risk_category": "DoS",
      "description": "Missing guard allows unbounded workload.",
      "status": "Vuln",
      "dataset_reference": "dataset:id-123" // optional
    }
  ],
  "summary": {
    "rounds": 4,
    "total_audit_flags": 9,
    "ap_coverage": { "AP-1": "4/4", "AP-2": "3/5" },
    "high_risk_hotspots": ["module/a.rs:check_path"],
    "next_focus": "Investigate retry backoff under burst load",
    "scope_rules": "include ./core/**, exclude ./docs/**",
    "bug_db": "security-agent/docs/bugs/shared_findings.json",
    "domains": ["execution", "zk"],
    "notes": "Dataset-driven checks revealed legacy guard regression."
  }
}
```

---

**Success Criteria**

* Every requested normative audited or logged as unmapped with justification.
* 100% of functions listed for those IDs in `02_ORDER.json` processed exactly once.
* `03_AUDITMAP.json` remains valid JSON; new findings appended without overwriting existing data.
* Attack-path checkpoints from `01_SPEC.json` evaluated; non-applicability justified.
* At least three attack paths documented for audited functions (or rationale for fewer).
* Bug database usage clearly stated.
* `ordering_strategy` in `02_ORDER.json` extended with scope rules, document references, coverage stats, and unmapped IDs stemming from this run.

---

**Notes & Hints**

* Respect inversion-of-control (registration handlers, callbacks, dependency injection) and asynchronous flows when tracing guards.
* Consider generated code; if in scope, annotate the generated output and reference the generator template in findings.
* Keep track of visited modules and remaining gaps for future audit phases.
* When uncertain, provide provisional judgments (using `needs-investigation`) with concrete follow-up steps.

---
