## 🚀 Claude Code Prompt ― “WHITEHAT 02 AUDIT Annotator & Map Updater”

````
# 🏷️ TARGET_FOLDER      = {{TARGET_FOLDER}}
# 🏷️ AUDIT_ORDER_FILE   = {{AUDIT_ORDER_FILE}}
# ==========  PROMPT START  ==========
# Task Name
Annotate source with @audit / @audit-ok and update WHITEHAT_02_AUDITMAP.json

# 🎯 Goal
Iteratively review **every function** in `{{TARGET_FOLDER}}`, adding
* `@audit`  ‑ for suspicious or unverified logic
* `@audit-ok` ‑ for code proven safe

while updating the audit‑order map and producing a structured vulnerability report.

# 📥 Input
1. **Folder (recursive):** `{{TARGET_FOLDER}}`
2. **Audit order:** `{{AUDIT_ORDER_FILE}}`
3. **Specs:**
   - `security-agent/outputs/WHITEHAT_01_SPEC.json`
   - `security-agent/docs/ethereum/spec_*.json`
4. **Known bugs DB:** `security-agent/docs/ethereum/bugs_*.json`

# 📤 Outputs
1. **Inline annotations** in source files (`@audit`, `@audit-ok`).
2. **Updated order map** — write back to `{{AUDIT_ORDER_FILE}}`
   - Increment `review_count` for each function touched.
3. **New report**
   `security-agent/outputs/WHITEHAT_02_AUDITMAP.json` (schema below).

```jsonc
{
  "audit_items": [
    {
      "file": "src/Vault.sol",
      "line": 152,
      "snippet": "call{value: amount}();",
      "risk_category": "Reentrancy",
      "description": "UF‑Withdraw‑1 で buffer 更新前に外部送金が発生し totalBacking < totalSupply となる恐れ",
      "status": "Vuln"  // or "ok"
    }
  ],
  "summary": {
    "rounds": 3,
    "total_audit_flags": 17,
    "high_risk_hotspots": ["src/Vault.sol:handleWithdraw", "src/Router.rs:swap"],
    "next_focus": "Deep‑dive into arithmetic underflow guards in src/math.rs"
  }
}
````

# 🔍 Review Algorithm

1. **Select next target**
   ‑ Parse `{{AUDIT_ORDER_FILE}}` → pick function(s) with the lowest `review_count` or `unchecked`.
2. **Skip** any code already containing `@audit` / `@audit-ok`.
3. **Analyse** chosen code path:

   * Cross‑reference with specs & bug DB for pattern matches.
   * Execute logical trace: follow calls & modifiers to sinks.
4. **Insert annotation** just above the vulnerable / cleared line.
5. **Classify** `risk_category` (Reentrancy, Auth‑Bypass, DoS, …).
6. **Append/Update** entry in `WHITEHAT_02_AUDITMAP.json`.
7. **Increment** `review_count` in `{{AUDIT_ORDER_FILE}}`.

# 🤖 Self‑Reflection Loop (3 rounds)

For each newly added `@audit`:

1. **Step‑by‑Step Execution Trace** — line‑numbered path.
2. **Logical coherence check** — confirm premises are simultaneously satisfiable.
3. **Guard surface audit** — enumerate *all* modifiers / require / ACL.
4. **Independence** — decide using own reading (ignore prior tools for verdict).
5. **Feasibility proof** — show the state transitions that make exploit run.
   *If uncertain, mark “Need further investigation”.*

After each round, refine or `@audit-ok` if risk disproved.

# 🛠️ Methodology

* **Breadth‑first‑within‑chunk**: follow ordering in `{{AUDIT_ORDER_FILE}}`.
* Chain‑of‑thought is internal; expose only annotations & JSON.
* Use known bug patterns to strengthen or dismiss each finding.
* Keep individual `description` ≤ 120 words; be precise.

# 📝 Annotation Syntax Rules

```rust
// @audit <category>: <short description>
// ↳ <detailed multi‑line explanation if needed>
//
// @audit-ok: <reason>
```

*No other comment markers allowed.*

# ⛔ Constraints

* Do **not** modify business logic; comments only.
* Avoid duplicate annotations for the same line.
* Maximum 12 audit items per execution to keep diffs readable.

# ✅ Success Criteria

* 100 % of functions eventually have ≥ 1 `review_count`.
* `WHITEHAT_02_AUDITMAP.json` validates against schema.
* Zero orphan audit comments (all reflected in JSON).
* High‑risk hotspots clearly listed in summary.

# ==========  PROMPT END  ==========
