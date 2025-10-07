---

**Description:** Audit **local implementation** corresponding to one or more `normative_spec.id` values (from `security-agent/outputs/01_SPEC.json`). Use `02_ORDER.json` to drive the **exact function order**. Add inline `@audit / @audit-ok` comments; produce/merge `03_AUDITMAP.json`; increment `review_count` in `02_ORDER.json`.

**Strict rules:**
• **Workspace only** — never reference spec repos or external sources inside findings. Do **not** cite `execution-specs` / `consensus-specs` / EIPs in code annotations.
• **Fusaka scope only** — Osaka (EL) normatives map to **local EL code**; Fulu (CL) normatives map to **local CL code**.
• **Source of truth** — Always load `security-agent/outputs/01_SPEC.json` (v2.0.0‑nl) at start. Treat it as the single normative and threats registry (use its `forks[].normative_spec`, `constants`, `invariants`, `algorithms`, and `threats.attack_paths`).
• **Attack‑path priority** — You MUST evaluate all relevant entries under `threats.attack_paths` from `01_SPEC.json` for each audited normative. For every applicable AP, check each listed **checkpoint** against the code and annotate with `@audit` or `@audit-ok`.
• **No drift** — If `01_SPEC.json` is missing, malformed, or schema ≠ `2.0.0-nl`, **abort with a retryable error** (do not annotate or write outputs).

**Usage:** `/02_order <NORMATIVE_IDS>`
**Arguments:**
* **NORMATIVE_IDS**: Comma‑separated list of `normative_spec.id` present in `01_SPEC.json` (e.g., `OSK-PEERDAS-CELL-PROOFS,FULU-CUSTODY-CALC`)

**Always use `/serena` for these development tasks to maximize token efficiency.**

---

# 🎯 Goal

Given `NORMATIVE_IDS`, **sequentially audit** the corresponding local functions (as ordered in `02_ORDER.json`) and annotate source with `@audit` / `@audit-ok`, while updating `03_AUDITMAP.json` and `02_ORDER.json`. **Consider every plausible risk** using checklists and knowledge in `security-agent/docs/**`, and **must** cover all applicable `threats.attack_paths` (from `security-agent/outputs/01_SPEC.json`) with their checkpoints.

---

# 📥 Inputs

1. **Normatives:** `NORMATIVE_IDS` (comma‑separated).
2. **Spec (source of truth for IDs & threats):** `security-agent/outputs/01_SPEC.json` (v2.0.0‑nl).
3. **Order/map:** `security-agent/outputs/02_ORDER.json` (must contain one `audit_chunk` per normative ID with **local** `functions`).
4. **Risk knowledge base:** `security-agent/docs/**` (all files). Use as checklists and references for *every* audit decision.
5. **Known bugs DB (mandatory reconnaissance):** `security-agent/docs/ethereum/bugs_ethereum.json`.
6. **Static call‑graph (optional):** `{{STATIC_CALLGRAPH}}` (`NONE` to derive).

---

## 🔒 Bounty Scope — Resolution & Enforcement (workspace‑wide)

* **Resolve scope** for this repository using, in order:
  1. `01_SPEC.json` → `bug_bounty.scope` / `forks[].bug_bounty.scope`,
  2. local `SECURITY.md` / `BUG_BOUNTY.md`,
  3. this repo’s official bounty page,
  4. official docs naming **this repo’s** scope.

* **Materialize rules**: explicit **include globs** (e.g., EL: `./core/**`, `./execution/**`, `./eth/**`, `./rpc/**`; CL: `./beacon/**`, `./consensus/**`, `./p2p/**`, `./gossip/**`, `./builder/**`, `./engine/**`) and **exclude globs** (`vendor/`, `third_party/`, `generated/`, `out/`, `dist/`, `build/`, `target/`, `mocks/`, `test/`, `docs/`, `spec/`, `eips/`, `execution-specs/`, `consensus-specs/`).

* **Fail closed**: If scope cannot be uniquely resolved, **abort with a retryable error** (do **not** annotate or write outputs).

---

## 🧭 Layer & Normative Matching

* Detect repo layer(s) from local tree (EL indicators: `core/`, `execution/`, `txpool/`, `core/vm/`, `rpc/`; CL indicators: `beacon/`, `fork_choice/`, `gossip/`, `ssz/`, `builder/`, `engine/`).

* For each `normative_spec.id` in `NORMATIVE_IDS`:
  * If **Osaka (Execution)** → only consider **local EL** paths (ignore CL code).
  * If **Fulu (Consensus)** → only consider **local CL** paths (ignore EL code).
  * If **layer mismatch** (e.g., CL normative in an EL‑only repo), add to “Unmapped IDs (layer mismatch)” and **skip**.

---

## 🔎 Function Selection (from 02_ORDER.json)

* Load `security-agent/outputs/02_ORDER.json`.
* For each requested normative ID, find the matching `audit_chunk` (title must start with `§ <ID> —`).
* Use its `functions` list (each with `file` and `line`) as the **authoritative order of review**.
* **Filter to bounty scope**; drop any out‑of‑scope entries.
* If an ID is **missing** from `02_ORDER.json`:
  * Attempt a fallback local search (AST + heuristics) within bounty scope for likely matches.
  * If still empty, record under “Unmapped IDs (no local functions found)” and **skip**.

---

## 🧪 Audit & Annotation Procedure (per function, in order)

1. **Context load from 01_SPEC.json**
   Retrieve the normative’s `summary`, `procedure`, `errors`, `constants`, `edge_cases`, `invariants`, and locate any **applicable attack paths** under `threats.attack_paths[*]` that reference this normative or its area (EL/CL).

2. **Open local file** and read the function body + immediate callers/callees (from call‑graph or grep).

3. **Risk sweep (two phases)** using `security-agent/docs/**` and `01_SPEC.json`:

   **3a. Generic sweep** — Apply checklists: DoS (CPU/IO/mem), consensus split, economic invariants, auth bypass, integer over/underflow, RLP/SSZ bounds, signature/KZG proof handling, blob fee math, engine/beacon API contracts, race conditions, replay, time/slot drift, subnet routing. Map findings to CWE where useful. Consult `security-agent/docs/ethereum/bugs_ethereum.json` for analogous exploits and log hypotheses (e.g., malformed precompile inputs, refund drift, handshake desync) before concluding the sweep.

   **3b. Attack‑Path Focused sweep (MANDATORY):**
   For every **applicable AP** in `01_SPEC.json.threats.attack_paths` (e.g., **AP‑1 … AP‑11**), evaluate **each checkpoint** against the code.
   • If a checkpoint is met with clear guards → add `@audit-ok (AP‑x.Cy): <why OK>` and tie to constants/invariants/procedure IDs.
   • If missing/ambiguous → add `@audit (AP‑x.Cy): <short risk>` with a one‑line exploit sketch.
   • Prefer early‑exit validations (e.g., wrong‑subnet drop) over heavy checks (e.g., batch KZG) when annotating flows.

4. **Decide**
   * If suspicion remains or proof is found → `@audit <category>: <short>` (+ optional multi‑line details; link to AP id and checkpoint).
   * If proven safe relative to the normative and AP checkpoints → `@audit-ok: <reason (tie to constants/invariants/procedure/AP)>`.

5. **Record**
   * Append/merge `security-agent/outputs/03_AUDITMAP.json` (schema below).
   * Increment `review_count` for this function in `security-agent/outputs/02_ORDER.json`.

6. **Self‑reflection loop (3 rounds) for each new `@audit`**
   * Step‑by‑step execution trace (line‑numbered).
   * Logical coherence check (premises satisfiable simultaneously?).
   * Guard surface audit (fork flags, ACL, bounds, invariants).
   * Independence (own reasoning).
   * Feasibility proof (state transitions that make exploit run). If inconclusive → status `needs-investigation`.

**Annotation syntax (strict):**
```rust
// @audit <category> (AP-<n>.C<k>): <short description>
// ↳ details; cite constants/invariants/procedure IDs from 01_SPEC.json; mention affected normative_spec.id
//
// @audit-ok (AP-<n>.C<k>): <reason linked to Osaka/Fulu normative + constants/invariants/procedure>
````

---

## 🔬 Advanced Attack Exploration

Before finalising any checkpoint, use `security-agent/docs/ethereum/bugs_ethereum.json`
to drive proactive, derivative exploit hunts:

- **Precompiles & cryptography** — ALTBN128, ModExp, BLS, and KZG weaknesses
  show fragile curve checks. Search for custom deserialisation, pairing
  optimisations, or bigint helpers (`rg "deserialize"`, `rg "BLS"`); attempt
  malformed group elements or builder→EL→CL payloads.
- **Gas accounting / blob economics** — Fee or refund drift can split consensus.
  Inspect bespoke gas math, blob fee comparisons, refund caps, and interactions
  with fork-specific pricing constants.
- **Handshake & networking** — ForkID, chain-ID width, ping flood, and partial
  eclipse flaws recur. Review handshake validation, replay tolerance, timeout
  symmetry, and uncommon p2p message flows reachable from the audited code.
- **Resource exhaustion** — Slow-input, goroutine floods, huge RPC queries,
  SSE underruns highlight unbounded work. Identify loops without bounds,
  dynamic allocations, or rate-limit bypasses, and model EL↔CL propagation.
- **Sync / reorg / recovery** — Deep reorg, history truncation, checkpoint and
  snap stalls indicate fragile unwind logic. Stress partial database states,
  rollback paths, and divergent engine responses with mocked payloads.
- **API / schema drift** — Prysm regressions reveal nil-vs-empty arrays, path
  typos, and schema mismatches. Audit JSON tags, SSE streams, REST routers for
  similar cracks and tooling desynchronisation.
- **Data availability / PeerDAS** — Column mis-indexing and custody subnet
  attrition suggest checking shard mappings, cache invalidation, and index math.

Capture emergent hypotheses in the audit record—even without immediate proof—so
future rounds can pursue the leads.

---

## 📤 Outputs

1. **Inline source comments** (`@audit`, `@audit-ok`) in local files (one per evaluated checkpoint where code intersects).

2. **Updated order map** — write back to `security-agent/outputs/02_ORDER.json`

   * Increment `review_count` for each function touched.
   * Append a textual summary to `ordering_strategy.top_attack_paths` (see below).

3. **Audit report** — create/merge `security-agent/outputs/03_AUDITMAP.json` (**extended schema**):

```jsonc
{
  "audit_items": [
    {
      "id": "auto-uuid",
      "normative_id": "FULU-SUBNET-ASSIGNMENT",
      "ap_id": "AP-1",
      "checkpoint": "C1", // e.g., "Reject on wrong subnet before heavy checks"
      "file": "beacon/gossip/subnet_router.go",
      "line": 142,
      "snippet": "if msg.SubnetID != computeSubnet(colIndex) { return ErrWrongSubnet }",
      "risk_category": "DoS",
      "description": "Wrong-subnet early reject missing for fallback path.",
      "status": "Vuln"  // or "ok" or "needs-investigation"
    }
  ],
  "summary": {
    "rounds": 3,
    "total_audit_flags": 7,
    "ap_coverage": { "AP-1": "4/4", "AP-2": "3/5", "AP-3": "2/3" },
    "high_risk_hotspots": ["p2p/gossip/sidecar_validate.rs:batch_kzg", "engine/reqresp/serve_sidecars.go:range"],
    "next_focus": "Stress KZG batch limits and RS recover_matrix abort paths"
  }
}
```

4. *(Optional)* Per‑ID roll‑up: `security-agent/outputs/03_AUDITMAP_<ID>.json`.

5. **Top Attack Paths (from audited functions only)** — produce ≥3 entry→sink paths with `risk_reason` ≤40 words; append to `ordering_strategy` inside `02_ORDER.json`.

---

## ⚡ Top Attack Paths (construction rules)

* Build/extend `top_attack_paths` using only functions actually audited in this run.
* Link each path to `ap_id` (e.g., AP‑1 / AP‑6 / AP‑9) and list key guards missing or hit.
* Example (textual):

  * `AP-1`: `gossip.Receive` → `validateSidecar` (no early subnet check) → `batchKZG` (CPU spike). *risk\_reason:* Missing wrong-subnet drop; unbounded batch leads to DoS.
  * `AP-2`: `reconstruct()` trusts unsorted cells → `recover_matrix` → `markAvailable()`; *risk\_reason:* no index dedup; inconsistent KZG abort missing.
  * `AP-9`: `txpool/acceptBlobTx` skips per‑tx blob cap → `block_builder`; *risk\_reason:* >6 blobs/tx bypass.

---

## ✅ Success Criteria

* Every requested `normative_spec.id` either audited (with inline comments + 03\_AUDITMAP updates) or explicitly listed as **Unmapped** (layer mismatch / no local functions found).
* **100%** of functions listed for those IDs in `02_ORDER.json` are processed exactly once.
* `03_AUDITMAP.json` validates; `02_ORDER.json` `review_count` incremented accordingly.
* **AP coverage:** For every **applicable** `threats.attack_paths` item from `01_SPEC.json`, at least one checkpoint is annotated (@audit or @audit-ok). If none apply, note reason under `ap_coverage` as `"N/A"` with rationale.
* Risk reasoning cites relevant entries from `security-agent/docs/**` (e.g., CWE‑400 for resource exhaustion) in comment text where useful.
* At least **3** attack paths are produced across the audited set.

---

## 🔧 Notes & Hints

* If the repo is EL (e.g., Geth/Erigon/Reth), prefer paths like: `core/txpool/*`, `core/blockchain/*`, `core/types/*`, `core/vm/*`, `execution/*`, `eth/*`, `rpc/*`.
* If CL (e.g., Lighthouse/Lodestar/…): `beacon/*`, `fork_choice/*`, `p2p/*`, `gossip/*`, `builder/*`, `engine/*`.
* New PeerDAS‑related normatives expected in `01_SPEC.json`:
  `OSK-PEERDAS-CELL-PROOFS`, `FULU-CUSTODY-CALC`, `FULU-RS-RECONSTRUCTION`, `FULU-SUBNET-ASSIGNMENT`, `FULU-DISTRIBUTED-BLOB-PUBLISHING`.
* Command examples:

```
/serena
/02_order OSK-PEERDAS-CELL-PROOFS,FULU-CUSTODY-CALC,FULU-RS-RECONSTRUCTION,FULU-SUBNET-ASSIGNMENT,FULU-DISTRIBUTED-BLOB-PUBLISHING
```

```
/serena
/02_order OSK-TX-VALIDATION,OSK-BLOCK-HASHING,FULU-PEERDAS-SAMPLING
```

---
