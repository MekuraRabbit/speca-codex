## 🚀 Claude Code Prompt ― “WHITEHAT Integration‑PoC Generator (DoS import)”

````
# 🏷️ UT_PATH      = {{UT_PATH}}
# 🏷️ IT_PATH       = {{IT_PATH}}
# 🏷️ VULN_NAME          = {{VULN_NAME}}
# ==========  PROMPT START  ==========
# Task Name
Create an **integration‑level PoC test** reproducing VULN_NAME
and failing only when the DoS vulnerability is present.

# 🎯 Goal
1. Generate `{{IT_PATH}}` that compiles under `cargo test`.
2. Reuse helpers / mocks from `{{UT_PATH}}` and sibling files to minimise boilerplate.
3. Test passes (✅) when the bug manifests (≥ 5 000 pending imports);
   fails (❌) after the fix (≤ 4 096).

# 📝 Attack Scenario (follow exactly)
| Step | Code Snippet |
| ---- | ------------ |
| ① **Testnet 起動** | `Testnet::create_with(1, provider)` *(1 in‑mem node)* |
| ② **大量 tx 生成** | use `TransactionGenerator` to create **1 000 tx** into `Vec<PooledTransactionVariant>` (~128 KB) |
| ③ **5 バッチ連続送信** | `node.network().send_transactions(*peer_id, txs_arc)` |
| ④ **少し待つ** | `tokio::time::sleep(std::time::Duration::from_secs(2))` |
| ⑤ **カウンタ確認** | `let count = pending_pool_imports_info.pending_pool_imports.load(Ordering::Relaxed);` |
| ⑥ **アサート** | `assert!(count >= 5_000, "DoS not reproduced");` |

# 📥 Input
- Unit PoC:          `{{UT_PATH}}`
- Audit report:      `security-agent/outputs/WHITEHAT_02_AUDITMAP.json`
- Project spec:      `security-agent/outputs/WHITEHAT_01_SPEC.json`
- Bug corpus / specs: `security-agent/docs/ethereum/{bugs_*,spec_*}.json`
- Source tree under the target directory

# 📤 Output Artifacts
1. **Test file** `{{IT_PATH}}`
2. **Run command**
   ```bash
   cargo test --test {{TEST_NAME}} -- --nocapture
````

3. **Status update** (append to WHITEHAT\_02\_AUDITMAP.json)

   ```jsonc
   {
     "file": "{{IT_PATH}}",
     "for_vuln": "{{VULN_NAME}}",
     "integration": true,
     "build_passed": true,
     "test_passed_when_bug_present": true,
     "attempts": 1
   }
   ```

# 🔍 Generation Algorithm

```
1. Scan sibling tests in the project's tests directory for reusable helpers.
2. Draft Arrange‑Act‑Assert skeleton per Attack Scenario table.
3. Import mocks or re‑export structs from UT_PATH to avoid duplication.
4. Compile (`cargo check`) and iterate ≤ 4 times:
      ‑ Fix missing deps / feature flags only (no scenario change).
5. Run test; ensure it **passes** on vulnerable codebase (simulate ≥ 5 000 count).
6. Embed negative‑control assertion (≤ 4 096) to catch false positives.
7. Append status JSON; write file.
```

# 🛡️ False‑Positive Guards

* Double assertion: `>= 5_000` *and* `> 4_096` to ensure threshold isn’t borderline.
* Log the `count` with `eprintln!` for manual review.
* Abort test early if `count == 0` (setup failure).

# 🤖 Self‑Repair Loop (max 3)

*On compile/test failure unrelated to scenario* → auto‑adjust imports/types.
If still blocked → print `"Need guidance: <stderr snippet>"` and stop.

# ⛔ Constraints

* Do **not** alter production code.
* Stay within the project's tests directory for new files.
* No external crates unless already in Cargo.toml.

# ✅ Success Criteria

* Test compiles & runs via provided command.
* Passes only when DoS remains.
* Status JSON appended & valid.

# ==========  PROMPT END  ==========
