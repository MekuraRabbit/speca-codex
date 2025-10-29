---
Description: PoC Generator & Self-Verifying Test
Usage: `/05_poc_unit <VULN_ID> <OUTPUT_TEST_PATH>`
Example: `/05_poc_unit 03523523 crates/net/network/src/transactions/poc_reentrancy.rs`
Arguments:
- **VULN_ID**: value of `audit_items[].id` in `03_AUDITMAP.json`
- **OUTPUT_TEST_PATH**: destination path for the generated test file
---

Create & validate a minimal PoC test that reproduces **VULN_ID**
**Always use /serena for these development tasks to maximize token efficiency:**


# 📥 Auto-load from 03_AUDITMAP.json
1. **Read** `security-agent/outputs/03_AUDITMAP.json`
2. **Find** the entry where `audit_items[].id == {{VULN_ID}}`
3. **Extract**
   - `VULN_SNIPPET` <- `audit_items[].snippet`
   - `TARGET_FILE` <- `audit_items[].file` + `:L` + `audit_items[].line`
   - `VULN_TITLE_RAW` <- `audit_items[].description`
   - `VULN_TITLE` <- text before the first colon (`:`) in `VULN_TITLE_RAW`, or the full string if no colon is present. If `VULN_TITLE` is empty, craft a concise fallback title (e.g., "Peer DAS sampling cache bypass") that still avoids embedding `VULN_ID`.
   - `TITLE_SLUG` <- `VULN_TITLE` transformed to lowercase snake_case containing only ASCII letters, digits, and underscores (convert spaces and punctuation to underscores, collapse repeats, strip leading/trailing underscores). If the slug exceeds 40 characters, remove filler words or truncate while preserving meaning so the final slug length ≤ 40.
4. **If not found** → abort with error
   `"Vulnerability '{{VULN_ID}}' not found in 03_AUDITMAP.json"`

# 🎯 Goal
Produce **one Rust test file** that:
1. Compiles & runs under `cargo test` (or Foundry, if Solidity)
2. **Passes only when the vulnerability is present (and must fail when it is absent)**
3. Requires *no* external binaries or network deps

# 📥 Input
- Vulnerability DB:    `security-agent/outputs/03_AUDITMAP.json`
- Project spec:        `security-agent/outputs/01_SPEC.json`
- Ethereum bug corpus: `security-agent/docs/ethereum/bugs_*.json`
- Ethereum specs:      `security-agent/docs/ethereum/spec_*.json`
- Source code:         Auto-load `TARGET_FILE` and nearby context

# 🧩 Pre-work (internal)
1. Locate exact code containing `VULN_SNIPPET`
2. Look for existing tests/mocks to reuse
3. Design exploit scenario (Arrange-Act-Assert)

# 📤 Output Artifacts
1. **PoC test file** → `{{OUTPUT_TEST_PATH}}`
   - `{OUTPUT_TEST_PATH}` must include `poc_{TITLE_SLUG}` (post-trimming) and must not include `VULN_ID`.
   - Keep the filename (without directories) ≤ 50 characters. If longer, shorten the slug or adjust wording before writing the file.
2. **Run command**
   ```bash
   cargo test --test poc_{{TITLE_SLUG}} -- --nocapture
````

3. **Status JSON** (append into same vulnerability entry)

   ```jsonc
   {
     "audit_items": [{
       // ... existing fields ...
       "poc_tests": [{
         "type": "unit",
         "file": "{{OUTPUT_TEST_PATH}}",
         "build_passed": true,
         "test_result": "pass_when_exploitable",
         "attempts": 1,
         "created_at": "<timestamp>"
       }]
     }]
   }
   ```

# 🔍 PoC Generation Algorithm

```
PLAN = global plan()
FOR attempt in 1..=4:
    generate skeleton using mocks
    if compile succeeds:
        run test
        if exploit reproduced: break ✅
    else:
        if attempt == 4: ask user 🆘
        adapt imports/types and retry
```

# 🛡️ False-Positive Mitigation

* Invariant double-check & patched-code control
* No silent `unwrap()`

# 📝 Test Style Guide (never embed VULN_ID in names)

```rust
#[test]
fn poc_{{TITLE_SLUG}}() {
    // Arrange
    /* minimal setup */

    // Act
    let res = import_transactions(/* crafted args */);

    // Assert
    assert!(res.is_ok(), "expected exploit to be reproducible");
}
```

- File names, module names, test function names, and any identifiers must use `TITLE_SLUG` and never include `VULN_ID`.
- If `VULN_TITLE` is empty after extraction, replace it with a descriptive fallback title (without `VULN_ID`), derive a slug from that value, and log the chosen title in the command output.

# ⛔ Constraints

* **Do not** touch production logic
* **Do not** add new crates (unless already in Cargo.toml)
* Keep test ≤ 120 LOC

# ✅ Success Criteria

* Entry with `id == VULN_ID` found
* Test passes only when bug present (and must fail once patched)
* Status JSON correctly appended
* > 3 compile failures → prompt user
