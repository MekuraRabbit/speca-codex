## 🚀 Claude Code Prompt ― “WHITEHAT PoC Generator & Self‑Verifying Test”

````
# 🏷️ VULN_NAME        = {{VULN_NAME}}
# 🏷️ OUTPUT_TEST_PATH = {{OUTPUT_TEST_PATH}}
# ==========  PROMPT START  ==========
# Task Name
Create & validate a minimal PoC test that reproduces VULN_NAME

# 📥 Auto-load from WHITEHAT_02_AUDITMAP.json
1. **First, read** `security-agent/outputs/WHITEHAT_02_AUDITMAP.json`
2. **Search for** the vulnerability where:
   - `audit_items[].risk_category` or `audit_items[].description` contains `{{VULN_NAME}}`
   - OR a dedicated `vuln_name` field equals `{{VULN_NAME}}`
3. **Extract the following**:
   - `VULN_SNIPPET`: from `audit_items[].snippet`
   - `TARGET_FILE`: from `audit_items[].file` + `:L` + `audit_items[].line`
4. **If not found**: abort with error "Vulnerability '{{VULN_NAME}}' not found in WHITEHAT_02_AUDITMAP.json"

# 🎯 Goal
Produce a **single Rust test file** that:
1. Compiles and runs under `cargo test` (or Foundry, if Solidity).
2. **Passes only when the vulnerability is exploitable**.
3. Requires *no* external binary patching or network deps.

# 📥 Input
- Vulnerability DB:    `security-agent/outputs/WHITEHAT_02_AUDITMAP.json`
- Project spec:        `security-agent/outputs/WHITEHAT_01_SPEC.json`
- Ethereum bug corpus: `security-agent/docs/ethereum/bugs_*.json`
- Ethereum specs:      `security-agent/docs/ethereum/spec_*.json`
- Source code:         Auto-loaded `TARGET_FILE` from JSON (and neighbours)

# 🧩 Pre‑work (internal)
1. **Locate exact code** containing auto-loaded `VULN_SNIPPET` → capture line range.
2. **Read existing tests / mocks** under the target directory → identify helpers to reuse.
3. **Formulate exploit scenario** using:
   - State pre‑conditions from spec & audit comment.
   - Similar known bugs for edge‑case inspiration.
4. **Plan test steps** as *Arrange‑Act‑Assert*:
   1. Arrange: construct minimal structs / mocks.
   2. Act: call vulnerable function with crafted inputs.
   3. Assert: program panics / returns wrong value / invariant broken.

# 📤 Output Artifacts
1. **PoC test file** → `{{OUTPUT_TEST_PATH}}`
2. **Command to run**:
   ```bash
   cargo test --test poc_{{VULN_NAME}} -- --nocapture
````

3. **Status JSON** (append to `WHITEHAT_02_AUDITMAP.json`):

   
   Add a new field `poc_tests` to the matching vulnerability entry:
   ```jsonc
   {
     "audit_items": [{
       // ... existing fields ...
       "poc_tests": [{
         "type": "unit",
         "file": "{{OUTPUT_TEST_PATH}}",
         "build_passed": true,
         "test_result": "fail_before_fix_pass_after_fix|pass_when_exploitable",
         "attempts": 1,
         "created_at": "<timestamp>"
       }]
     }]
   }
   ```

# 🔍 PoC Generation Algorithm

```
PLAN = global‑plan()
FOR attempt in 1..=4:
    CREATE test skeleton (using existing mocks if any)
    TRY compile
        IF success:
            RUN test
            IF passes by reproducing bug: BREAK ✅
            ELSE IF false‑positive suspected:
                → Insert “negative‑control” branch (e.g. patched struct) to verify
        ELSE:
            IF attempt == 4: REPORT compile failure, await user guidance 🆘
            ADAPT (import missing crate / tweak types) and retry
```

# 🛡️ False‑Positive Mitigation

* **Invariant double‑check**: compute expected vs actual result and assert inequality.
* **Patched‑code control**: within test, create local wrapper that fixes the bug; assert wrapper passes while original fails.
* **No silent unwrap()**: all error paths must `assert!(is_err())` or `should_panic`.

# 🧠 Self‑Reflection Loop (max 3)

1. Run `cargo test`; capture stderr.
2. If failure unrelated to exploit (type mismatch, orphan rules, etc.)
   → Auto‑fix imports/types **without changing scenario**.
3. After each fix, re‑evaluate exploit assertion consistency.
4. On persistent blockers ➜ print “Need guidance: \<error\_snip>”.

# 📝 Test Style Guide

```rust
#[test]
fn poc_{{VULN_NAME}}() {
    // -- Arrange --
    /* minimal setup */

    // -- Act --
    let res = import_transactions(/* crafted args */);

    // -- Assert --
    assert!(matches!(res, Err(_)), "Vulnerability reproduced: zero‑div allowed");
}
```

* Use `#[should_panic]` only if panic = bug.
* Keep < 120 LOC. No dead code.

# ⛔ Constraints

* Do **not** rewrite production logic.
* Do **not** add external crates unless already in Cargo.toml.
* Stay within folder of vulnerable code for tests.
* If unit scope insufficient, escalate to integration test under `tests/`.

# ✅ Success Criteria

* Vulnerability found in WHITEHAT_02_AUDITMAP.json using VULN_NAME.
* File exists, compiles, and test passes **only** when bug present.
* Status JSON appended to matching vulnerability entry & valid.
* If hindered >3 compile failures → ask user.

# ==========  PROMPT END  ==========
