---

**Description:** Build a complete function ordering and call-graph view for the current workspace by mapping selected `normative_spec.id` entries from `security-agent/outputs/01_SPEC.json` to in-scope implementation code. Use the supplied documentation paths as supporting context while traversing the call graph exhaustively. Emit `security-agent/outputs/02_ORDER.json` only.

**Usage:** `/02_order <NORMATIVE_IDS> <DOC_PATH_LIST>`

**Example:** `/02_order "OSK-TX-VALIDATION,ZK-PROVER-PIPELINE" "docs/specs/**/*.md,notes/design/overview.md"`

**Language:** English instructions and outputs.

**Execution hint:** Always run with `/serena` to maximize token efficiency.

**NORMATIVE_ID source:** Values supplied in `NORMATIVE_IDS` must exactly match the `id` fields under `domains[].normative_spec[]` in `security-agent/outputs/01_SPEC.json`. Work from a fresh branch created off `master` for each ID (or cohesive set of IDs) to keep audit artifacts isolated.

---

**Goal**

Produce an ordered audit map that:

1. Covers every in-scope local function related to the requested normative IDs.
2. Assembles a deterministic call graph (caller → callee) that has been traversed exhaustively within scope, including boundary nodes for out-of-scope callees.
3. Records one `audit_chunk` per normative ID, listing local functions (with file paths and line numbers) in caller-to-callee order.
4. Documents traversal strategy, scope rules, documentation references, coverage statistics, and unmapped IDs at the end of `ordering_strategy`.

---

**Arguments**

- `NORMATIVE_IDS`: Comma-separated list of `normative_spec.id` values to process. Use `*` to indicate all IDs in `01_SPEC.json`.
- `DOC_PATH_LIST`: Comma-separated list of workspace-relative documentation paths or glob patterns (Markdown, HTML, code comments, etc.) that must be consulted while assembling keywords, architectural hints, and expected call flows.

If `DOC_PATH_LIST` is empty, derive supporting context from `metadata.reference_urls` in `01_SPEC.json` and local README/SECURITY files. Reject non-existent paths unless the bounty scope explicitly excludes them.

---

**Primary Inputs**

1. Workspace root (current repository).
2. `security-agent/outputs/01_SPEC.json` (version `3.0.0-generic`).
3. Optional static call graph file `{{STATIC_CALLGRAPH}}` (set to `NONE` to auto-derive).
4. Documentation set indicated by `DOC_PATH_LIST` (and any additional scope-approved references).
5. Bounty scope artefacts: `SECURITY.md`, `BUG_BOUNTY.md`, `SECURITY_POLICY`, `.well-known/security.txt`, official program pages.

---

**Bounty Scope Resolution**

1. Resolve scope using the first definitive source in this order:
   - `01_SPEC.json` → `bug_bounty.scope` or `domains[*].bug_bounty.scope`.
   - Local security policy files (`SECURITY.md`, `BUG_BOUNTY.md`, etc.).
   - Official bug bounty program page for this repository or organization.
   - Other official documentation that enumerates scope.
2. Translate scope into explicit include and exclude globs (language-specific paths, infrastructure directories, etc.).
3. Honor branch, tag, and commit restrictions if provided.
4. Fail closed: if scope cannot be uniquely resolved, abort with a retryable error.
5. Append the final scope rules and source citations to `ordering_strategy`.

---

**Domain & Layer Detection**

- Inspect repository structure to determine applicable domains (execution, consensus, zk, smart-contract, web, devops, infrastructure, etc.).
- Filter `NORMATIVE_IDS` by matching `domains[*].layer_or_scope` and `domains[*].genre` from `01_SPEC.json` to detected local domains.
- Record any mismatches (e.g., normative IDs targeting components absent from this repo) under “Unmapped normative IDs” in `ordering_strategy`.

---

**Documentation Cross-Referencing**

- Ingest all files matching `DOC_PATH_LIST` before code traversal.
- Extract terminology, component names, module boundaries, and API references to seed search heuristics.
- When documentation conflicts with code, defer to code but record the discrepancy in `ordering_strategy`.

---

**Function Discovery & Call-Graph Construction**

- Enumerate all in-scope source files (respecting include/exclude globs).
- Parse ASTs or symbol tables to list functions, methods, handlers, tasks, and entry points relevant to the selected normative IDs.
- Build or merge a call graph starting from all entry points identified for each normative, tracing through synchronous and asynchronous invocations, callbacks, trait/ interface implementations, and generated code stubs where resolvable.
- Treat out-of-scope callees as boundary nodes; record their names but do not expand them further.
- Ensure every reachable in-scope function appears exactly once across all chunks.
- Do not include external specification repositories or third-party packages as function entries; reference them only as boundary notes if necessary.

---

**Iterative Deepening Loop**

- Execute up to five passes over discovery, mapping, and call-graph expansion.
- After each pass, compare newly observed edges, functions, and documentation cues against prior iterations.
- Continue to the next pass only if additional in-scope functions, alternative branches, or unresolved attack-path checkpoints remain.
- Record per-pass deltas (new functions, edges, unresolved items) in `ordering_strategy`; stop early when no incremental depth is achieved.

---

**Normative Mapping**

For each requested normative ID:

1. Gather keywords from `normative_spec.summary`, `procedure`, `inputs`, `errors`, `rationale`, `security_requirements`, and relevant `threat_catalog.attack_vectors` entries.
2. Match keywords against documentation tokens and code identifiers to locate candidate modules.
3. Rank candidates using structural cues (module ownership, dependency direction, file naming, test fixtures).
4. Select the minimal function set that fully implements the normative behavior, ensuring coverage of validation, state mutation, error handling, and telemetry hooks.
5. Order functions from external entry point to deepest callee following the constructed call graph.

---

**Call-Graph Coverage Expectations**

- Traverse all call edges reachable from normative entry points, including error paths, retries, feature-flag branches, and asynchronous continuations where code is present in scope.
- Document any intentionally skipped branches (e.g., platform-specific stubs) with justification in `ordering_strategy`.
- If the call graph cannot be completed due to missing symbols, mark the normative as partially mapped and describe blockers.

---

**Top Attack Paths**

- Produce at least three plausible entry → sink paths drawing exclusively from functions listed in `audit_chunks[].functions`.
- Each path must include `entry_function`, `sink_function`, and a concise `risk_reason` (≤40 words) describing potential misuse or failure.
- Align attack paths with threats cited in `01_SPEC.json` or observed during traversal.

---

**Output Format**

Write a single JSON file `security-agent/outputs/02_ORDER.json` matching the schema below (unchanged):

```jsonc
{
  "metadata": {
    "target_folder": "<WORKSPACE_ROOT>",
    "static_callgraph": "{{STATIC_CALLGRAPH}}",
    "spec_loaded": true,
    "generated_at": "<RFC3339 timestamp>",
    "schema_version": "1.0.0"
  },
  "audit_chunks": [
    {
      "chunk_title": "§ OSK-TX-VALIDATION — Transaction Validation [Execution]",
      "rationale": "Local transaction admission gate; enforces intrinsic bounds before execution.",
      "functions": [
        {"name": "txpool.validateTransaction", "file": "core/txpool/txpool.go", "line": 312},
        {"name": "core.checkTransaction", "file": "core/tx_validator.go", "line": 87}
      ]
    }
  ],
  "top_attack_paths": [
    {
      "entry_function": "rpc.eth_config",
      "sink_function": "core.blockchain.InsertChain",
      "risk_reason": "Misvalidated params influence block import and state transitions."
    }
  ],
  "ordering_strategy": "Describe traversal order, scope rules, documentation sources, coverage stats, and unmapped normative IDs."
}
```

Do not alter key names. Append human-readable summaries (scope rules, document references, coverage, unmapped IDs) to the tail of `ordering_strategy` as plain text.

---

**Methodology Checklist**

1. Load `01_SPEC.json`; validate schema version and extract requested normative IDs (expand `*` to all IDs).
2. Resolve bounty scope; build include/exclude globs.
3. Verify every path in `DOC_PATH_LIST`; ingest contents for heuristic seeding.
4. Detect repository domains; filter normative IDs accordingly.
5. Iterate up to five deepening passes: enumerate in-scope files, parse ASTs, construct/merge call graphs, and expand frontier nodes until no new in-scope edges appear.
6. Map each normative ID to its ordered function list with supporting rationale, excluding non-workspace code paths.
7. Generate ≥3 attack paths referencing mapped functions only.
8. Populate `ordering_strategy` with traversal notes (including per-pass deltas), scope rules, documentation references (relative paths), coverage metrics, and unmapped IDs with reasons.
9. Emit JSON with RFC3339 timestamp; validate against schema.

---

**Success Criteria**

- JSON parses successfully and retains schema `1.0.0`.
- Every requested normative ID has an `audit_chunk`; mismatches are recorded with justification.
- Each in-scope function appears in exactly one chunk.
- Call graph traversal is exhaustive within scope; skipped edges are documented.
- At least three top attack paths are provided.
- `ordering_strategy` concludes with scope rules, documentation list, coverage summary, and unmapped IDs.
- Iterative deepening loop executes up to five passes (or stops early) with per-pass deltas captured in `ordering_strategy`.

---

**Notes & Hints**

- Leverage language-specific tools (`go list`, `cargo metadata`, `tsc --listFiles`, etc.) to assist with symbol discovery when available.
- For frameworks with inversion of control (e.g., dependency injection, event-driven systems), include registration sites and callbacks in the call graph.
- When documentation paths include architectural diagrams or ADRs, extract function/module names and compare against code to avoid omissions.
- If generated code is in scope, ensure the source templates or generators are represented; otherwise mark them as boundary nodes and explain why.

---
