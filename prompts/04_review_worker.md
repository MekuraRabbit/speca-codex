
---
Description: "[WORKER] Review Phase 03 audit findings — filter FPs, verify exploitability, calibrate severity."
Usage: /04_review_worker WORKER_ID=... QUEUE_FILE=... [TIMESTAMP=...] [ITERATION=...] [BATCH_SIZE=...] [OUTPUT_FILE=...]
Example: /04_review_worker WORKER_ID=0 QUEUE_FILE=outputs/04_QUEUE_0.json TIMESTAMP=1700000000 ITERATION=1 BATCH_SIZE=5 OUTPUT_FILE=outputs/04_PARTIAL_W0_1700000000_1.json
Language: English only.
Execution hint: This worker prompt is invoked by the phase-04 async orchestrator.
---

<task>
  <goal>Filter false positives from Phase 03 findings, calibrate severity.</goal>
  <input type="file" id="queue">{{QUEUE_FILE}}</input>
  <input type="file" id="context">{{CONTEXT_FILE}}</input>
  <output type="file" id="results">{{OUTPUT_FILE}}</output>

  <critical_requirements>
    1. Process ALL items in the batch.
    2. After processing, write JSON to <ref id="results"/>. **FAILURE TO WRITE IS A CRITICAL ERROR.**
    3. The JSON file MUST be written even if all items are disputed.
    4. **RECALL PROTECTION**: Only the 3 gates below may produce DISPUTED_FP.
       Each gate has a narrow, specific check — do NOT expand the scope of a gate.
       - Gate 1: caller count only (grep result). No code logic analysis.
       - Gate 2: data source trust level only (lookup in trust_assumptions). No code analysis.
       - Gate 3: scope exclusion list only (lookup in BUG_BOUNTY_SCOPE). No code analysis.
       If none of the 3 gates triggers, the finding MUST survive (CONFIRMED_* or NEEDS_MANUAL_REVIEW).
       Reasoning about code correctness, design intent, or security impact is NOT a gate check.
  </critical_requirements>

  <instructions>

  ## 1. Setup (once per batch)

  Read <ref id="queue"/> for `item_ids` and `context_file`. Read <ref id="context"/> for item data.
  Each context item contains:
  - `property_id`
  - `audit_result`: the Phase 03 finding with fields such as `classification`,
    `code_path`, `proof_trace`, `attack_scenario`, and `checklist_id`
  - original property context fields (`text`, `assertion`, `covers`, `severity`, `type`)

  Whenever this prompt says "Phase 03's classification", "finding", "code path",
  "proof trace", or "attack scenario", read it from the item's `audit_result`
  object unless the field is explicitly present at top level.

  Derive `OUTPUT_ROOT` from the directory containing the absolute queue/context/output
  paths. Whenever this prompt says `outputs/...`, read from that `OUTPUT_ROOT`;
  do not probe repository-root `outputs/` as a fallback.

  Then read and cache these files from `OUTPUT_ROOT`:
  - `BUG_BOUNTY_SCOPE.json` - scope rules, `trust_assumptions`, severity thresholds. **Required.**
  - `TARGET_INFO.json` - target repo metadata, including `local_checkout`. **Required.**

  Resolve the target checkout root from `TARGET_INFO.local_checkout`:
  - If `local_checkout` is absolute, use it as-is.
  - If `local_checkout` is relative, resolve it relative to the worker's current
    workspace/cwd, not relative to `OUTPUT_ROOT`.
  - Never construct `OUTPUT_ROOT/local_checkout`, `OUTPUT_ROOT/target_workspace`,
    `outputs/target_workspace`, or `outputs/rehearsal_dvd/target_workspace`.

  Treat the resolved checkout as the exact target code root. All source
  reads/searches must stay under that checkout. Do not list or search the
  `target_workspace` parent, sibling checkouts, the SPECA repository root, live
  URLs, RPC endpoints, registries, explorers, or deployment/account infrastructure.

  ## 2. For each item — FP Filter Pipeline (3 gates)

  Process each item through the gates below **in order**. If a gate triggers DISPUTED_FP,
  record the reason and **skip remaining gates**. This is a filter — exit early when possible.

  Items with `audit_result.classification` = not-a-vulnerability, out-of-scope, or informational → **PASS_THROUGH** (skip all gates).

  **Only these 3 gates may produce DISPUTED_FP. No other reasoning may dispute a finding.**

  ---

  ### Gate 1: Dead Code (catches bugs in unreachable code)

  Grep for call sites of the flagged function (exclude `*_test.*` / `test_*.*` files).
  If `rg` is unavailable or fails with "Access is denied" on Windows, do not
  retry `rg`; immediately fall back to PowerShell `Get-ChildItem` plus
  `Select-String` under the resolved checkout.
  - **Zero non-test callers** → DISPUTED_FP: "dead/unreachable code"
  - Function no longer exists in the file → DISPUTED_FP: "code removed"
  - Skip this gate for "missing validation" findings (the issue is that something is NOT called).
  - **Public/exported API exception**: If the function is `pub`, `public`, `exported`, or part
    of a library's public interface → passes gate regardless of internal caller count.
    External consumers may call it even if the current repo does not.

  ---

  ### Gate 2: Trust Boundary (catches findings whose attack path relies on a trusted data source)

  Read `trust_assumptions` from BUG_BOUNTY_SCOPE.json.
  Look up the **data source name** that Phase 03's `audit_result.attack_scenario`
  or `audit_result.proof_trace` depends on
  (e.g., "Engine API", "local IPC", "P2P gossip", "execution layer").

  **Decision is purely a lookup — match Phase 03's entry point against trust_assumptions:**
  1. Find which data source Phase 03 lists as the entry point / attack vector.
  2. Look up that source in `trust_assumptions`.
  3. If trust level is `TRUSTED` or `SEMI_TRUSTED` **and** no untrusted (e.g., P2P) path
     also reaches the same code → DISPUTED_FP: "entry point [source] is [TRUSTED|SEMI_TRUSTED]"
  4. If an untrusted path also reaches the same code → passes gate.

  **This gate does NOT read or analyze source code.** Do not reason about whether
  the code is "correct", "by design", or "a misinterpretation". The only question is:
  does the attack path go through a trusted data source? Yes/no.

  ---

  ### Gate 3: Scope Check

  Check `out_of_scope`, `conditional_scope`, and `in_scope.scope_restriction` in BUG_BOUNTY_SCOPE.json.
  - Finding falls under an excluded category → DISPUTED_FP: "[category] is out of scope"
  - Issue predates the audit scope (e.g., not introduced in the target fork) → DISPUTED_FP: "pre-existing, out of scope"

  ---

  ## 3. Severity Calibration (for items that passed all gates)

  Apply `severity_classification` from BUG_BOUNTY_SCOPE.json:
  1. Read impact thresholds for each severity level.
  2. If `deployment_context.client_diversity` exists, find the target's network share.
     This share caps the maximum severity for a single-component bug.
  3. If original severity exceeds the cap, keep the substantive `review_verdict`
     (`CONFIRMED_VULNERABILITY` or `CONFIRMED_POTENTIAL`), set
     `severity_action` to `DOWNGRADED`, and set `adjusted_severity` to the capped
     severity. Do not use `DOWNGRADED` as a `review_verdict` for new outputs.
  4. If the finding depends on a semi-trusted integration choice or a non-standard
     underlying asset (for example fee-on-transfer, deflationary, rebasing, or
     otherwise short-delivering tokens), do not dispute it solely for that reason
     when an untrusted user can still reach the code. Keep it as
     `CONFIRMED_POTENTIAL`, cap `adjusted_severity` at `Low` unless
     `BUG_BOUNTY_SCOPE.json` explicitly says otherwise, set `severity_action` to
     `DOWNGRADED` when applying the cap, and state the conditional integration
     prerequisite in `reviewer_notes`.

  ## 4. Verdict

  For items that passed all gates:
  - Clear spec deviation + attacker-triggered + concrete attack path
    → **CONFIRMED_VULNERABILITY**
    (reviewer_notes MUST include: "An attacker can trigger this via [entry point]
    by [action], causing [impact].")
  - Spec deviation exists but attack path is uncertain → **CONFIRMED_POTENTIAL**
  - Cannot determine → **NEEDS_MANUAL_REVIEW**

  **Consistency rule**: The verdict must be consistent with the gate outcomes.
  - If a gate triggered DISPUTED_FP, the verdict is DISPUTED_FP.
  - If all gates passed, the verdict MUST NOT be DISPUTED_FP.
    Use CONFIRMED_POTENTIAL or NEEDS_MANUAL_REVIEW for uncertain cases that passed all gates.

  ## 5. Write Output

  Write a single JSON object to <ref id="results"/>:
  ```json
  {
    "reviewed_items": [
      {
        "property_id": "...",
        "review_verdict": "CONFIRMED_VULNERABILITY | CONFIRMED_POTENTIAL | DISPUTED_FP | NEEDS_MANUAL_REVIEW | PASS_THROUGH",
        "severity_action": "NONE | DOWNGRADED",
        "original_classification": "vulnerability | potential-vulnerability",
        "adjusted_severity": "Critical | High | Medium | Low | Informational",
        "reviewer_notes": "2-3 sentences: gate that triggered + evidence, or severity reasoning",
        "spec_reference": ""
      }
    ],
    "metadata": { "phase": "04", "worker_id": "{{WORKER_ID}}", "item_count": N, "timestamp": N, "processed_ids": [...] }
  }
  ```

  Print summary and end with: `Output File: {{OUTPUT_FILE}}`

  </instructions>

  <quality_gates>
    1. Every item has exactly the 7 keys shown in the schema.
    2. DISPUTED_FP always states WHICH gate (1, 2, or 3) triggered and WHY.
    3. CONFIRMED_VULNERABILITY always includes a concrete attack sentence.
    4. adjusted_severity is justified against BUG_BOUNTY_SCOPE.json thresholds.
    5. Verdict is consistent with gate outcomes — no DISPUTED_FP if all 3 gates passed.
    6. Severity caps use `severity_action: "DOWNGRADED"` and never
       `review_verdict: "DOWNGRADED"` in new outputs.
  </quality_gates>
</task>

<output>
  <format>JSON object with "reviewed_items" key (NOT a JSON array)</format>
  <stdout>Max 8 lines: batch size, items processed, short status.</stdout>
  <final_line>Output File: {{OUTPUT_FILE}}</final_line>
</output>
