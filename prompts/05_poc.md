---
Description: Phase 05 PoC Generator from reviewed SPECA findings
Usage: `/05_poc CANDIDATE_ID=... [OUTPUT_DIR=outputs] [TYPE=unit|it|e2e] [OUTPUT_PATH=...]`
Example: `/05_poc CANDIDATE_ID="POC-truster-unauthorized-token-approval-76774102" OUTPUT_DIR="outputs/rehearsal_dvd"`
Arguments:
- **$CANDIDATE_ID**: value of `candidates[].candidate_id` in `05_POC_CANDIDATES.json`.
- **$OUTPUT_DIR**: SPECA output directory containing `TARGET_INFO.json` and `05_POC_CANDIDATES.json`.
- **$TYPE**: optional override for the candidate's `recommended_type`.
- **$OUTPUT_PATH**: optional override for the candidate's `recommended_output_path`.
---

Create and validate a minimal Proof-of-Concept test for a reviewed Phase 04 finding.

# Inputs
1. Read `$OUTPUT_DIR/05_POC_CANDIDATES.json`.
2. Locate the entry where `candidates[].candidate_id == $CANDIDATE_ID`.
3. If `$CANDIDATE_ID` is omitted and exactly one candidate is provided in context, use that candidate. Otherwise abort with a clear error.
4. Read `$OUTPUT_DIR/TARGET_INFO.json` and use its `local_checkout` as the target repository root.
5. Resolve `target_local_checkout`, `recommended_output_path`, and any override paths relative to the current workspace.

# Scope And Safety
* Use SPECA only inside the authorized local checkout from `TARGET_INFO.local_checkout`.
* Read target code only under that local checkout.
* Do not read sibling directories such as another target checkout or `target_workspace/contracts`.
* Do not fetch external GitHub, raw GitHub, registry, explorer, RPC, deployment, account, or website infrastructure links.
* Do not run package installation commands (`npm install`, `npm ci`, `pip install`, `forge install`, etc.) unless the operator explicitly asks.
* Do not modify production code. Write only the PoC test/scenario file under the target checkout and Phase05 result JSON under `$OUTPUT_DIR`.
* If `rg` is unavailable or returns Windows `Access denied`, immediately fall back to PowerShell `Get-ChildItem` plus `Select-String`.
* If the local checkout is missing, or the pinned commit does not match `TARGET_INFO.target_commit`, stop and report the mismatch.

# Candidate Fields To Use
Use the candidate as the source of truth:
* `representative_property_id`
* `covered_property_ids`
* `challenge`
* `attack_family`
* `target_files`
* `primary_file`
* `primary_symbol`
* `attack_summary`
* `recommended_type`
* `recommended_output_path`
* `run_command`

# Goals
1. Generate the PoC in the target project's native stack.
2. Reuse nearby tests, fixtures, helpers, mocks, and package scripts.
3. The PoC should pass while the vulnerability exists and fail once the bug is fixed.
4. Keep the artifact focused and self-verifying.
5. Prefer one representative PoC per root cause; mention the covered Phase04 property IDs in the result JSON.

# TYPE Guidelines
* `unit`: smallest available module-level or package-level test.
* `it`: integration test using the existing project test harness.
* `e2e`: highest available workflow/CLI/API scenario.
* If the candidate has a `recommended_type`, use it unless `$TYPE` overrides it.

# Build And Run
1. Inspect local project metadata only (`package.json`, `Cargo.toml`, `pytest.ini`, `go.mod`, `foundry.toml`, Makefiles, etc.).
2. Use the candidate `run_command` when it is suitable; otherwise derive a command that runs only this PoC.
3. Run commands from `target_local_checkout`.
4. If dependencies are missing and cannot be installed under the scope rules, record `status: "blocked"` rather than weakening the PoC.
5. Use a self-repair loop up to 3 times for import, fixture, typing, or harness issues that do not change the exploit.

# Output Artifacts
1. PoC file:
   * Default path: candidate `recommended_output_path`.
   * Override path: `$OUTPUT_PATH`, if provided.
   * File name should start with `poc_` and describe the attack family, not the property ID.
2. Phase05 result JSON:
   * Write `$OUTPUT_DIR/05_POC_RESULT_<candidate_id>.json`.
   * Use this shape:
     ```json
     {
       "candidate_id": "<candidate_id>",
       "representative_property_id": "<property_id>",
       "covered_property_ids": ["<property_id>"],
       "type": "unit|it|e2e",
       "file": "<path>",
       "run_command": "<command>",
       "status": "passed|failed|blocked",
       "attempts": 1,
       "test_passed_when_bug_present": true,
       "notes": "",
       "created_at": "<ISO-8601 timestamp>"
     }
     ```
3. Final response:
   * Summarize the PoC file, run command, status, attempts, and any blocker.
   * Include the candidate's covered property count and IDs.

# Success Criteria
* Candidate located in `05_POC_CANDIDATES.json`.
* Target checkout verified against `TARGET_INFO`.
* PoC file created under the authorized target checkout.
* Targeted test command executed, or a precise local dependency blocker recorded.
* `05_POC_RESULT_<candidate_id>.json` written with accurate status.
