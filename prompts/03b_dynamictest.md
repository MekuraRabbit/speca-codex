---

**Description:** Design, implement, and execute local tests that exercise specific `normative_spec.id` objectives defined in `security-agent/outputs/01_SPEC.json`. Leverage `02_ORDER.json` to resolve precise implementation targets, generate exactly one new test file per requested normative, run the relevant test subset, and publish structured results without disturbing existing artifacts.

**Usage:** `/03b_dynamictest <NORMATIVE_IDS>`

**Example:** `/03b_dynamictest "OSK-TX-VALIDATION,FULU-DATA-AVAILABILITY"`

**Language:** English instructions, comments, and summaries.

**Execution hint:** Always run with `/serena` for token efficiency.

**NORMATIVE_ID hygiene:** Provide IDs exactly as emitted in `security-agent/outputs/01_SPEC.json` under `domains[].normative_spec[].id`, and craft tests from branches cut off `master` per ID set to simplify reviews and merges.

---

**Strict Rules**

• **Workspace only** — Do not embed external specification references, URLs, or third-party code in generated tests. Rely solely on local documents and the canonical spec JSON.
• **Scope fidelity** — Confine all changes to bounty-approved directories. Respect include/exclude globs derived from security policy; ignore off-scope modules unless explicitly allowed.
• **Source of truth** — Load `security-agent/outputs/01_SPEC.json` (schema `3.0.0-generic`) before any work. Treat it as the authoritative registry for normatives, algorithms, invariants, and threat catalog entries. Abort with a retryable error if the file is missing, malformed, or mismatched schema.
• **Attack-path coverage** — For each generated test, cover every applicable checkpoint from `threats.attack_paths` that intersects with the targeted components. Encode checkpoints as assertions, fuzz oracles, negative cases, or runtime guards.
• **One ID → one file** — Each `normative_spec.id` must yield exactly one new test file placed in the most appropriate existing test location.

---

**Goal**

For every requested `normative_spec.id`:
1. Map normative context and local functions.
2. Create a focused test file aligned with local conventions (naming, tooling, fixtures).
3. Install any missing dependencies via the repo’s established package manager only.
4. Execute the new test (or narrowed suite) and capture logs.
5. Merge results into `security-agent/outputs/04_TESTMAP.json` and increment `review_count` for exercised functions in `02_ORDER.json`.

---

**Inputs**

1. `NORMATIVE_IDS`: Comma-separated list. `*` expands to all normatives in `01_SPEC.json`.
2. `security-agent/outputs/01_SPEC.json` (schema `3.0.0-generic`).
3. `security-agent/outputs/02_ORDER.json` (schema `1.0.0`).
4. Optional risk references: `security-agent/docs/**`, architecture notes, runbooks.
5. Optional bug datasets (if relevant to test design).
6. Static call graph (`{{STATIC_CALLGRAPH}}`) when available (`NONE` to derive on the fly).

---

**Bounty Scope — Resolution & Enforcement**

1. Resolve scope via (first definitive source wins):
   - `01_SPEC.json` → `bug_bounty.scope` / `domains[*].bug_bounty.scope`
   - Local `SECURITY.md`, `BUG_BOUNTY.md`, `SECURITY_POLICY`
   - Official bounty or security documentation for the project
2. Materialize include/exclude globs per language/domain (e.g., execution `./core/**`, `./txpool/**`; consensus `./beacon/**`, `./consensus/**`; web `./apps/**`, `./api/**`; zk `./circuits/**`, `./prover/**`).
3. Exclude default directories (`vendor/`, `third_party/`, `generated/`, `dist/`, `build/`, `docs/`, etc.) unless explicitly in scope.
4. Fail closed if scope remains ambiguous.

---

**Domain & ID Matching**

* Detect repository domains using directory structure, build manifests, and language indicators.
* Associate each normative ID with relevant domains (execution, consensus, zk, smart-contract, web, infrastructure, devops, etc.).
* Record mismatches as “Unmapped IDs (layer mismatch)” in the final report.
* Load normative context (summary, procedure, inputs, errors, invariants, security requirements, attack paths, related algorithms).

---

**Function Selection (via `02_ORDER.json`)**

1. Locate the `audit_chunk` whose title begins with `§ <NORMATIVE_ID> —` tied to the test objective.
2. Use the chunk’s `functions` list to choose primary entry points and determine the best existing test module/folder.
3. If the ID is absent, perform bounded discovery (AST queries, call graph hints) within scope. If still unresolved, note under “Unmapped IDs (no local functions found)”.

---

**Test Design Workflow**

1. **Prototype**: Outline test scenarios that satisfy normative procedures and attack-path checkpoints. Include success, failure, boundary, fuzzing, property-based, and stress cases as appropriate. Decide which testing technique (unit, fuzz, property, integration) best fits the normative.
2. **Placement**: Identify the canonical test location (language-specific). Respect module/package structure and naming conventions.
3. **Implementation**: Generate one test file per normative ID with:
   - Metadata comments (`@normative-id`, `@ap-id`, etc.).
   - Setup/teardown aligned with existing frameworks.
   - Assertions or property checks covering every applicable checkpoint.
   - Stubs/mocks limited to local fixtures or existing helpers.
4. **Dependencies**: Install missing tools via the project’s package manager (e.g., `cargo`, `go`, `pnpm`, `pip`). Avoid global installations.
5. **Execution**: Run the new test file or targeted subset (single module, filtered command). Capture pass/fail/flake status and relevant logs.
6. **Automation**: Update scripts if necessary to ensure repeatable runs, but do not modify CI configuration unless explicitly requested.

---

**Attack-Path Driven Enhancements**

* Translate `threats.attack_paths[*]` checkpoints into subtests or parameterized cases.
* Typical categories:
  - **Untrusted input rejection** (size, format, replay).
  - **Resource exhaustion** (CPU, memory, disk, network) with bounded work checks.
  - **State divergence** (consensus, ledger, storage) detection via invariants.
  - **Interface misuse** (timeout, auth, schema drift) validated through simulation.
  - **Economic/game-theoretic** edge cases (fee calculation, incentive alignment).
* Document any checkpoint deemed inapplicable with concise rationale in the test file and result map.

---

**Execution & Result Capture**

1. Run the newly generated test(s) using the project’s native runner (`cargo test`, `go test`, `npm test -- <filter>`, `pytest`, etc.).
2. Capture exit codes, runtimes, failure diagnostics, fuzz corpus seeds (if applicable).
3. Write/merge `security-agent/outputs/04_TESTMAP.json` with per-test entries:
   ```jsonc
   {
     "tests": [
       {
         "normative_id": "OSK-TX-VALIDATION",
         "ap_coverage": {"AP-1": "C1,C2", "AP-4": "C1"},
         "status": "pass",
         "file": "tests/execution/osk_tx_validation_spec.rs",
         "runner": "cargo test osk_tx_validation_spec",
         "duration_ms": 512,
         "techniques": ["boundary", "fuzz", "negative"],
         "fuzz_corpus": "corp/osk_tx_validation_seed" // optional
       }
     ],
     "summary": {"pass": 1, "fail": 0, "flake": 0}
   }
   ```
4. Increment `review_count` in `02_ORDER.json` for each function exercised.
5. Append top attack paths (entry → sink with ≤40-word `risk_reason`) to `ordering_strategy.top_attack_paths` in `02_ORDER.json`, avoiding duplicates from prior runs.
6. Optionally emit per-ID result files `security-agent/outputs/04_TESTMAP_<ID>.json` for granular debugging.

---

**Success Criteria**

* Every requested `normative_spec.id` either results in a new test file and executed run or is documented as unmapped (layer mismatch, no functions, runner unavailable).
* Each test exercises all relevant checkpoints from attack paths; non-applicable steps are justified.
* Test files adhere to local style and compile/execute successfully with the workspace toolchain.
* `04_TESTMAP.json` remains valid JSON with appended entries; no overwrites of unrelated tests.
* `02_ORDER.json` accurately reflects updated `review_count` values and newly observed attack paths.
* Logs highlight failures, flakes, or follow-up actions where needed.

---

**Retryable Errors**

* `ERR_SPEC_INVALID` — Spec missing or schema mismatch.
* `ERR_LAYER_MISMATCH` — Normative domain does not exist in this repo.
* `ERR_NO_LOCAL_FUNCTIONS` — No candidate functions found even after bounded search.
* `ERR_RUNNER_UNAVAILABLE` — Required test runner or dependency unavailable after attempting local installation.
* `ERR_SCOPE_AMBIGUOUS` — Bounty scope cannot be resolved; abort before writing files.

---

**Command Examples**

```
/serena
/02_order OSK-TX-VALIDATION,FULU-DATA-AVAILABILITY
/03b_dynamictest OSK-TX-VALIDATION,FULU-DATA-AVAILABILITY
```

```
/serena
/03b_dynamictest ZK-PROVER-PIPELINE,NORM-WEB-AUTH
```

---
