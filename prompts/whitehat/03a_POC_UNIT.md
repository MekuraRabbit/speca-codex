## 🚀 Claude Code Prompt ― “WHITEHAT PoC Generator & Self‑Verifying Test”

````
# 🏷️ VULN_NAME        = DoSUnboundedImport
# 🏷️ VULN_SNIPPET     = "fn import_transactions("
# 🏷️ TARGET_FILE      = crates/net/network/src/transactions/mod.rs:L1326
# 🏷️ OUTPUT_TEST_PATH = crates/net/network/src/transactions/mod.rs or crates/net/network/src/transactions/poc_{{VULN_NAME}}.rs
# ==========  PROMPT START  ==========
# Task Name
Create & validate a minimal PoC test that reproduces VULN_NAME

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
- Source code:         `{{TARGET_FILE}}` (and neighbours)

# 🧩 Pre‑work (internal)
1. **Locate exact code** containing `{{VULN_SNIPPET}}` → capture line range.
2. **Read existing tests / mocks** under `crates/net/` → identify helpers to reuse.
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

   ```jsonc
   {
     "file": "{{OUTPUT_TEST_PATH}}",
     "for_vuln": "{{VULN_NAME}}",
     "build_passed": true,
     "test_result": "fail_before_fix_pass_after_fix|pass_when_exploitable",
     "attempts": 1
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

* File exists, compiles, and test passes **only** when bug present.
* Status JSON appended & valid.
* If hindered >3 compile failures → ask user.

# ==========  PROMPT END  ==========