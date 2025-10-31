---

**Description:**
Derive a property catalog from the latest project specification, translating normative behaviours into `{property, anti_property}` tuples with testable predicates, observability, and cross‑implementation parity vectors. Emit a **deterministic** JSON for downstream checklist generation, parity testing, and fuzz harnesses.

**Usage:** `/01_prop`
**Language:** English only.
**Execution hint:** Run immediately after `/01_spec` so the latest specification is available.
**Tooling note:** Always use **/serena** for these development tasks to maximize token efficiency.

---
**Always use /serena for these development tasks to maximize token efficiency:**

# **Property Extraction Prompt**

**Goal**
Translate every normative behaviour captured in `security-agent/outputs/01_SPEC.json` and supporting architecture into actionable, self‑sufficient property tuples:

```
{ property_id, property, anti_property, state_predicate, enforcement_scope,
  falsification, observability, testing_hooks, parity_vectors,
  spec_refs, signals, trust_scope, status, notes,
  criticality, confidence }
```

**Output (required file):** `security-agent/outputs/01_PROP.json`
**Determinism:** Sort all top‑level arrays deterministically (see "Determinism & IDs").

---

## 0) Preflight & Guardrails

* **Require** `security-agent/outputs/01_SPEC.json`. If missing or unreadable, stop and emit a minimal JSON with:

  * `status: "error"` and `notes: "missing 01_SPEC.json"`.
* **Freshness:** Read `metadata.spec_generated_at`. If older than **72 hours** relative to `now`, set top‑level `metadata.stale: true` and annotate `notes`; proceed but mark properties with `status: "needs-refresh"` unless proven otherwise.
* **Source discovery caps:** Respect `metadata.source_directory` and (if present) `metadata.reference_paths`. Exclude large vendor/generated folders using defaults:

  * `exclude_globs`: `["**/node_modules/**","**/build/**","**/dist/**",".git/**","**/.venv/**"]`.

---

## 1) Inputs & Authority

1. **Primary spec (authoritative):** `security-agent/outputs/01_SPEC.json`

   * Set `metadata.project_name` from spec and copy `metadata.spec_generated_at`.
   * Treat everything under `domains[]`, `user_flows`, `algorithms`, `state_machines`, `trusted_entities` as normative truth.
   * Respect trust assumptions; do **not** assume trusted actors become adversarial unless marked conditionally trusted.

2. **Architecture references (supporting):**

   * Recursively scan `metadata.source_directory` and any `metadata.reference_paths` for invariants, contracts, state layouts, diagrams, ADRs, and code comments.

3. **External research (required):**

   * For each URL in `metadata.reference_urls` (and domain‑level lists), perform a **fresh** lookup of the latest official docs or advisories. Prefer vendor docs, audited repos, and recent security analyses.
   * Record **all** consulted sources in `metadata.sources` (as objects: `{title, url, accessed_at}`).
   * In property `notes`, refer to sources **by index** (e.g., `src[3]`), not by raw URLs.

4. **Historical signals (optional):**

   * `security-agent/outputs/01_SIMILAR_ISSUES.json`
   * `security-agent/outputs/01_PAST_REPORTS/*`
     Use only for justification; never invent behaviour not in spec/architecture.

---

## 2) Determinism & IDs

* **property_id format:** `PROP-<DOMAIN>-<SLUG>[-<H4>]`

  * `<SLUG>`: Uppercase KEBAB from the concise invariant name (e.g., `EXACTLY-ONCE-DELIVERY`).
  * `<H4>`: Optional 4‑hex stable digest of `project_name|origin_ids|SLUG` (e.g., first 4 of SHA‑1) to avoid collisions.
* **Uniqueness:** Must be unique across the file. If collision, append/recompute `<H4>`.
* **Stable ordering:** Sort `properties` lexicographically by `property_id`. Sort inner arrays (`testing_hooks`, `parity_vectors`, etc.) by `id`/`name`.

---

## 3) Derivation Procedure

1. **Enumerate Normative Behaviour**

   * For every spec flow/algorithm/state‑machine, write a **positive** `property` (declarative invariant) and map it to spec identifiers (`spec_refs`: e.g., `FLOW-001`, `ALGO-COMMIT-VERIFY`).
   * Ensure **each domain** and each of its `user_flows / algorithms / state_machines` yields ≥1 property tuple.

2. **Dual Anti‑Property**

   * Write `anti_property` as the **precise failure** phrased attacker‑centrically and mutually exclusive with `property`.

3. **Formalisation**

   * `state_predicate`: Boolean relation over contract/storage/protocol state.

     * Use ASCII DSL by default (e.g., `forall guid: committed(guid) -> executed_once(guid) and tombstoned(guid)`).
     * If mathematical symbols are clearer, include `state_predicate_math` alongside (UTF‑8).
   * `enforcement_scope`: Where it must hold (entrypoints, modules, storage keys, events, off‑chain components).
   * `falsification`: How to break it.

     * **Dynamic:** negative tests, fuzz/scenario scripts.
     * **Static:** analyzers or code queries (e.g., Slither, Semgrep, grepable patterns).
     * Include **expected_counterexample_signal**.
     * Include **budget**: `{timeout_s, max_cases, seed}`.
     * Include **environment_matrix** if relevant (e.g., `{networks:["devnet","testnet"], tool_versions:{foundry:"X", scarb:"Y"}}`).
   * `observability`: Evidence of coverage.

     * Name concrete events/logs/metrics and **thresholds** or cardinality expectations.
     * Provide **alert_rules** as pseudocode (e.g., PromQL/KQL‑like).

4. **Testing Hooks**

   * Bind to executable artefacts (Foundry/Echidna/Cairo fuzzers, invariant harnesses, unit tests).
   * Provide commands and required env vars. Prefer CI‑safe commands.

5. **Parity Vectors**

   * For cross‑implementation behaviour, define vectors:

     * `{vector_id, input_description, expected_outputs{impl_key: value}, verification_method, status}`
   * If artefacts are missing, set `status: "pending-detail"` with blocking notes.
   * Store fixtures under `security-agent/outputs/parity_vectors/…`.

6. **Linkage & Metadata**

   * `spec_refs` (normative IDs/section titles) and optional `signals` (issue/report IDs).
   * `trust_scope`: one of `["trusted","conditionally_trusted","untrusted"]`.
   * `status`: one of `["verified","pending-detail","needs-refresh","error"]`.

7. **Prioritisation & Confidence**

   * `criticality`: `{impact: "low|medium|high|critical", likelihood: "low|medium|high"}`
   * `confidence`: `"low|medium|high"` with rationale.

---

## 4) Coverage Index (required)

Emit a `coverage` object summarising what was covered and what is missing:

```
"coverage": {
  "summary": {
    "domains_total": <int>,
    "flows_total": <int>, "flows_covered": <int>,
    "algorithms_total": <int>, "algorithms_covered": <int>,
    "state_machines_total": <int>, "state_machines_covered": <int>
  },
  "gaps": [
    {"type":"flow","domain":"<domain>","id":"<FLOW‑ID>","reason":"no property","status":"pending-detail"}
  ]
}
```

---

## 5) JSON Schema Requirements

Write `security-agent/outputs/01_PROP.json` as UTF‑8 **pure JSON** (no comments):

```json
{
  "metadata": {
    "project_name": "<PROJECT_NAME>",
    "generated_at": "<RFC3339 timestamp>",
    "spec_generated_at": "<SPEC_TIMESTAMP>",
    "stale": false,
    "sources": [
      {"title":"<TITLE>","url":"<URL>","accessed_at":"<RFC3339>"}
    ],
    "schema_version": "1.1.0-properties",
    "language": "english",
    "exclude_globs": ["**/node_modules/**","**/build/**","**/dist/**",".git/**",".venv/**"],
    "generator": {
      "runner": "/serena",
      "prompt_digest": "<short-hash-of-this-prompt>"
    }
  },
  "coverage": { /* see Coverage Index */ },
  "properties": [
    {
      "property_id": "PROP-MESSAGING-EXACTLY-ONCE-DELIVERY",
      "domain": "messaging",
      "property": "Every inbound GUID executes exactly once after the commitment slot is tombstoned.",
      "anti_property": "Execution can succeed without marking the commitment as consumed, enabling replay or double-spend.",
      "state_predicate": "forall guid: committed(guid) -> executed_once(guid) and tombstoned(guid)",
      "enforcement_scope": {
        "entrypoints": ["MessageEndpoint.execute"],
        "storage_keys": ["commitments[guid]","tombstones[guid]"],
        "events": ["MessageDelivered(guid, channel_id, nonce)"]
      },
      "falsification": {
        "tests": [
          {
            "tool": "echidna",
            "harness": "test/invariants/ExactlyOnce.sol",
            "scenario": "Drive execution before tombstone write"
          }
        ],
        "static_queries": [
          {"tool":"slither","rule":"reentrancy-eth-sends","notes":"Detect external calls before tombstoning"}
        ],
        "expected_counterexample_signal": "Execution succeeds while commitments[guid] remains set",
        "budget": {"timeout_s": 900, "max_cases": 100000, "seed": "0x01"},
        "environment_matrix": {"networks":["devnet"],"tool_versions":{"foundry":"latest"}}
      },
      "observability": {
        "signals": [
          {"type":"event","name":"MessageDelivered","fields":["guid","channel_id","nonce"],
           "expectation":"Exactly once per GUID after tombstone write"}
        ],
        "alert_rules": [
          "count_over_time(MessageDelivered{guid=<g>}[24h]) != 1 -> alert: 'duplicate-delivery'"
        ],
        "evidence_requirements": [
          "Consumption marker persisted before dispatcher call","Retry metrics monotonic"
        ]
      },
      "testing_hooks": [
        {"tool":"echidna","command":"echidna-test test/invariants/ExactlyOnce.sol --test-limit 100000","environment":"FOUNDRY_PROFILE=ci"},
        {"tool":"cairo-fuzzer","command":"poetry run cairo-fuzz --target starknet/endpoint.cairo::execute_guid_once","environment":"FUZZ_GUID=0xabc"}
      ],
      "parity_vectors": [
        {
          "vector_id":"PV-GUID-001",
          "input_description":"GUID 0xabc... with payload hash 0x123...",
          "expected_outputs":{"evm":"hash_evm(guid||payload)","starknet":"hash_sn(guid||payload)"},
          "verification_method":"scripts/parity/check_guid_hash.py",
          "status":"ready"
        }
      ],
      "spec_refs": ["FLOW-DELIVERY-003"],
      "signals": ["org/repo#173"],
      "trust_scope": "untrusted",
      "criticality": {"impact":"high","likelihood":"medium"},
      "confidence": "high",
      "status": "verified",
      "notes": "See src[2] for replay class; matched with architecture diagram A-3."
    }
  ]
}
```

**Rules**

* No empty arrays: omit fields instead.
* Enumerations:

  * `trust_scope ∈ {"trusted","conditionally_trusted","untrusted"}`
  * `status ∈ {"verified","pending-detail","needs-refresh","error"}`
  * `confidence ∈ {"low","medium","high"}`
  * `criticality.impact ∈ {"low","medium","high","critical"}`, `criticality.likelihood ∈ {"low","medium","high"}`
* Deterministic order: `properties` sorted by `property_id`.

---

## 6) Success Criteria (updated)

* **Determinism:** Stable `property_id` generation and sorted output; re-runs do not reshuffle IDs.
* **Coverage:** All domains/flows/algorithms/state‑machines covered; uncovered items listed under `coverage.gaps`.
* **Testability:** Each property has both dynamic and static falsification with budgets and environment hints.
* **Observability:** Signals, thresholds, and alert rules enable runtime detection.
* **Parity:** Cross‑implementation vectors exist or are explicitly `pending-detail` with blockers.
* **Schema hygiene:** Enumerations enforced; no empty arrays; valid UTF‑8 JSON.

---

## 7) Post‑Generation Guidance

* `property_id` is the stable primary key; keep invariant across regenerations.
* Store parity fixtures under `security-agent/outputs/parity_vectors/…`.
* When new architecture artefacts appear or spec freshness is flagged (`metadata.stale=true`), rerun `/01_prop`.
