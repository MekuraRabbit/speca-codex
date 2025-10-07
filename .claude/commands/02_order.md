---

**Description:** Generate an ordered audit map for the **current workspace** (repo root), mapping each `normative_spec.id` from `security-agent/outputs/01_SPEC.json` to **local implementation files & functions** only. **Do not reference spec repositories**.
**Usage:** `/02_order`
**Arguments:** *None*
**Always use `/serena` for these development tasks to maximize token efficiency.**

Generate `security-agent/outputs/02_ORDER.json` from **local sources only**.

> **Critical requirement — Bounty Scope Enforcement (workspace‑bound):**
> Analyze **only files explicitly in bug‑bounty scope** for this repository. Build concrete include/exclude rules and **ignore everything outside scope**. If scope cannot be unambiguously resolved, **abort with a retryable error**.

---

# 🎯 Goal

Produce an *ordered* audit map that:

1. Covers **every in‑scope local function** in the **current repository** related to **Fusaka** (Osaka=EL, Fulu=CL).
2. For **each** `normative_spec.id` in `security-agent/outputs/01_SPEC.json`, **exhaustively lists the corresponding local implementation files & functions** at the finest granularity (include line numbers when possible), **restricted by layer**:

   * **Execution (Osaka)** normatives → map **only to local EL client code** in this repo.
   * **Consensus (Fulu)** normatives → map **only to local CL client code** in this repo.
   * **Never** record spec‑repo paths (e.g., `execution-specs`, `consensus-specs`) in `functions`.

> **Schema note:** Do **not** change the JSON schema. Create **one `audit_chunk` per `normative_spec.id`**; place all mapped **local** functions for that normative into that chunk’s `functions`. Put scope notes, coverage, and any unresolved IDs at the **end of `ordering_strategy`**.

---

# 📥 Input

1. **Workspace root:** current repository (scan recursively).
2. **Static call‑graph (optional):** `{{STATIC_CALLGRAPH}}` (`NONE` to self‑derive).
3. **Project specification (normatives):** `security-agent/outputs/01_SPEC.json` (v2.0.0‑nl).
4. **Ethereum canonical specs (optional hints only):** `security-agent/docs/ethereum/spec_*.json` (do **not** record these paths in `functions`).
5. **Bounty scope sources (for this repo):**

   * Local: `SECURITY.md`, `SECURITY_POLICY`, `BUG_BOUNTY.md`, README “Scope”, `/.well-known/security.txt`.
   * Remote (if needed): official program page for **this client** (Immunefi/Code4rena/Sherlock/HackerOne), EF security page.
   * Prefer sources that list **paths/globs**, **branches/tags**, **commit ranges**.

---

## 🧭 Workspace & Layer Auto‑Detection (mandatory)

1. Detect **client type** and **layer(s)** from local files (no spec repos):

   * **EL candidates (Osaka mapping)**: presence of `go.mod` + `core/`, `eth/`, `execution/`, `miner/`, `txpool/`, `core/vm/` (Go); or `crates/{evm,interpreter,payload}/` (Rust); or `ethereum/eth/*` (Java/C#); JSON‑RPC servers (`rpc/`, `ethapi/`).
   * **CL candidates (Fulu mapping)**: `beacon/`, `consensus/`, `fork_choice/`, `attestation/`, `p2p/`, `gossip/`, `ssz/`, `builder/`.
2. Filter `normative_spec` by **layer match**:

   * If repo is **EL‑only**, build chunks **only for Osaka** normatives; list Fulu IDs as “out of repo scope (layer mismatch)” in `ordering_strategy`.
   * If **CL‑only**, do the inverse.
   * If monorepo, include both but map each normative to its **own local sub‑trees**.

---

## 🔒 Bounty Scope — Resolution & Enforcement (workspace‑wide)

**Resolution hierarchy (first definitive match wins):**

1. `01_SPEC.json` → `bug_bounty.scope` / `forks[].bug_bounty.scope` (repo‑specific)
2. Local `SECURITY.md` / `BUG_BOUNTY.md` (this repo)
3. Official bounty page for **this client**
4. Official docs explicitly naming **this repo’s** scope

**Materialize scope into rules (applied globally):**

* **Include globs** (examples; adapt to current repo):

  * **EL (Go)**: `./core/**/*.go`, `./eth/**/*.go`, `./execution/**/*.go`, `./miner/**/*.go`, `./rpc/**/*.go`, `./cmd/**`.
  * **EL (Rust)**: `./crates/**/src/**/*.rs`.
  * **EL (Java/C#)**: `./**/src/main/**/(java|cs)/**`.
  * **CL**: `./beacon/**`, `./consensus/**`, `./fork_choice/**`, `./p2p/**`, `./gossip/**`, `./ssz/**`, `./builder/**`, `./api/**`.
* **Exclude globs** unless explicitly in scope: `vendor/`, `third_party/`, `lib/`, `generated/`, `out/`, `dist/`, `build/`, `target/`, `mocks/`, `test/`, `docs/`, `spec/`, `eips/`, `execution-specs/`, `consensus-specs/`.
* **Branch/commit filters**: honor constraints from bounty scope.
* **Fail‑closed**: if ambiguity remains, **abort** with a clear, retryable error.

Append the final rule set and sources at the end of `ordering_strategy`.

---

## 🔍 Fusaka Matching Heuristics (workspace‑only)

Use `01_SPEC.json`’s **`forks[].normative_spec[]`** to drive matching. For each `normative_spec.id`:

* **Osaka examples (EL)**

  * **OSK‑TX‑VALIDATION**: tx admission & validation (intrinsic/calldata cost, gas cap 2^24, signature/nonce/balance, blob count/price). Likely in `txpool/`, `core/`, `execution/`, `eth/`.
  * **OSK‑RLP‑BLOCK‑SIZE**: block serialization & import guards (RLP length checks). Likely in `core/types`, `rlp/`, `blockchain/`, `miner/`.
  * **OSK‑CLZ**: opcode table & VM interpreter (`OP_CLZ` dispatch; bit‑ops helpers). Likely `core/vm/`, `interpreter/`, `evm/`.
  * **OSK‑P256**: precompile registry/dispatch (`0x0100`), scalar/point checks, success‑word. Likely `core/vm/precompile/`.
  * **OSK‑MODEXP‑LIMITS/PRICING**: ModExp length checks & pricing. Likely `core/vm/precompile/modexp`.
  * **OSK‑ETH\_CONFIG**: JSON‑RPC method handler. Likely `rpc/`, `ethapi/`, `cmd/rpcdaemon/`.
  * **OSK‑BLOB‑FEE‑LOWER‑BOUND**: blob fee math; `calcExcessBlobGas`, base fee floor. Likely `blobpool/`, `fee/`, `core/`.

* **Fulu examples (CL)**

  * **FULU‑PEERDAS**: gossip topics, DataColumnSidecar encode/verify, KZG checks, req/resp handlers, custody assignment. Likely `p2p/`, `gossip/`, `network/`, `das/`, `kzg/`.
  * **FULU‑PROPOSER‑LOOKAHEAD**: next‑epoch schedule computation/storage; beacon transitions. Likely `beacon/`, `state/`, `fork_choice/`.
  * **FULU‑ENGINE‑INTERFACE**: BlobsBundleV2, requests hashing expectations to EL. Likely `builder/`, `engine/`, `api/`.

**Mapping method (fine‑grained):**

1. From each normative, derive keywords (EIP numbers, constants, API names, procedure verbs).
2. Enumerate local candidates per include globs; parse AST to list all defs (functions/methods).
3. Score matches (name/doc/comment/constant usage/import proximity/call‑graph proximity).
4. Keep only branches **executed under Fusaka feature gates** (fork timestamp, feature flags).
5. Record as `<qualified_name>` with `file` (repo‑relative) and `line`.
6. **Deduplicate** globally so each local function appears **once** across all chunks.

> **Never** output spec‑repo paths in `functions`.

---

## 🧠 Function Discovery (language‑aware, workspace‑only)

* **Go**: list `func` (pkg & methods w/ receivers), `init`; detect line via parser/scan.
* **Rust**: `fn`, impl methods, trait impls; include module path; lines.
* **Java/C#**: methods/constructors; module path; lines.
* **TS/Nim**: procs/functions/methods; route handlers.
* Normalized key: `<normalized_path>#<qualified_name>#L<line>`.

---

## 🧩 Chunking & Ordering

* **One `audit_chunk` per `normative_spec.id`**:
  `chunk_title = "§ <ID> — <Short Title> [Osaka|Fulu]"`
  `rationale` (≤ 60 words): why these **local** functions implement that normative.
* **Global order** (threat‑driven):

  1. Untrusted inputs (RPC/gossip)
  2. Crypto/validation gates (P‑256, KZG, ModExp)
  3. State mutation hubs (state transition / fork choice)
  4. Bridges/external deps
  5. Utilities
* Within each chunk, order **caller → callee**; tie‑break by path then line.

---

## 🕸️ Call‑Graph Construction

* If `{{STATIC_CALLGRAPH}}` provided, merge; else derive locally (ignore std‑lib edges).
* Show edges to out‑of‑scope callees as **boundary nodes** (not expanded).

---

## ⚡ Top Attack Paths

* Provide **≥ 3** plausible entry→sink paths **using only local functions** listed in `audit_chunks[].functions`.
* Each `risk_reason` ≤ 40 words; focus on how untrusted input could reach a sensitive sink under Fusaka rules.

---

## 📤 Output

Write **one** JSON file: `security-agent/outputs/02_ORDER.json`

```jsonc
{
  "metadata": {
    "target_folder": "<WORKSPACE_ROOT>",         // always this value (no TARGET_FOLDER arg)
    "static_callgraph": "{{STATIC_CALLGRAPH}}",  // "AUTO" or "NONE" if self-derived
    "spec_loaded": true,
    "generated_at": "<RFC3339 timestamp>",
    "schema_version": "1.0.0"
  },
  "audit_chunks": [
    {
      "chunk_title": "§ OSK-TX-VALIDATION — Transaction Validation [Osaka]",
      "rationale": "Local tx admission gate for Osaka; rejects over-gas/malformed tx before execution.",
      "functions": [
        {"name": "txpool.validateTransaction", "file": "core/txpool/txpool.go", "line": 312},
        {"name": "core.checkTransaction", "file": "core/tx_validator.go", "line": 87}
      ]
    }
    // …one chunk per normative_spec.id with only local functions…
  ],
  "top_attack_paths": [
    {
      "entry_function": "rpc.eth_config",
      "sink_function": "core.blockchain.InsertChain",
      "risk_reason": "Misvalidated params influence building/import decisions."
    }
    // ≥ 3 paths
  ],
  "ordering_strategy": "Boundary-inward (RPC/gossip → validation → state). Caller→callee within chunks. Append here: (1) Bounty-scope include/exclude rules; (2) Sources/links; (3) Coverage stats; (4) Unmapped normative IDs with reasons (layer mismatch / not present in this repo)."
}
```

> **Do not change the JSON schema.** Put the **scope rule set**, **citations**, **coverage**, and **unmapped IDs** as plain text at the end of `ordering_strategy`.

---

## 🛠️ Methodology (deterministic, workspace‑wide)

1. Load `01_SPEC.json`; collect Fusaka normatives; tag each with **Osaka** or **Fulu**.
2. Resolve bounty scope (workspace globs & branch filters); **fail‑closed** if ambiguous.
3. Auto‑detect repo layer(s); filter normatives accordingly (EL, CL, or both).
4. Enumerate **local** files by include globs; parse AST; list functions; build/merge call‑graph.
5. For each normative: derive keywords; match & score; restrict to **Fusaka‑gated** branches; record `file` + `line`.
6. Build one chunk per normative; global ordering threat‑driven; intra‑chunk caller→callee.
7. Construct ≥ 3 **local** attack paths.
8. Validate: **every in‑scope local function appears exactly once**; RFC3339 timestamp; deterministic ordering.
9. Write only `security-agent/outputs/02_ORDER.json`.

---

## ✅ Success Criteria

* JSON exists & parses.
* **100% coverage** of in‑scope **local** functions; **no spec paths**.
* Every `normative_spec.id` gets a dedicated chunk with **local** functions from the correct layer (Osaka or Fulu).
* ≥ 3 attack paths built from local functions.
* `ordering_strategy` ends with: **Scope summary & sources**, **Coverage stats**, **Unmapped IDs** (with reasons).

---

### Client directory hints (workspace examples)

* **Erigon (Go)**: `./core/**/*.go`, `./eth/**/*.go`, `./execution/**/*.go`, `./rpc/**/*.go`, `./cmd/**`
* **Geth (Go)**: `./core/**/*.go`, `./eth/**/*.go`, `./miner/**/*.go`, `./consensus/**/*.go`, `./internal/ethapi/**/*.go`
* **Reth (Rust)**: `./crates/**/src/**/*.rs` (e.g., `revm`, `interpreter`, `payload`, `rpc`)
* **Besu (Java)**: `./ethereum/**/src/main/java/**`
* **Nethermind (C#)**: `./src/**/Ethereum/**.cs`
* **Lighthouse/Teku/Prysm/Lodestar (CL)**: `./beacon_node/**`, `./consensus/**`, `./network/**`, `./fork_choice/**`, `./builder/**`, `./api/**`