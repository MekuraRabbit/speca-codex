---
Description: Review and validate existing @audit annotations.
Usage: `/04_review <TARGET_FOLDER>`
Example: `/04_review crates/net/`
Arguments:
- TARGET_FOLDER: Folder path that scopes the review
---
Review all existing @audit comments, confirm validity, and update reports
**Always use /serena for these development tasks to maximize token efficiency:**


# 🎯 Goal
For every **@audit** in `{{TARGET_FOLDER}}`, decide with rigorous reasoning
whether it is a **real, exploitable issue**.
If disproved, transform it into `@audit-ok` with a brief rationale.
If confirmed (or partially confirmed), keep `@audit`, expand insight, and
categorise the exact risk.

Finally, synchronise results into
`security-agent/outputs/03_OUDITMAP.json`
and increment `review_rounds` in `security-agent/outputs/02_ORDER.json`

# 📥 Input
1. Source code (rec.): `{{TARGET_FOLDER}}`
2. Audit map:         `security-agent/outputs/02_ORDER.json`
3. Project spec:      `security-agent/outputs/01_SPEC.json`
4. Ethereum specs:    `security-agent/docs/ethereum/spec_*.json`
5. Bug DB:            `security-agent/docs/ethereum/bugs_*.json`
6. External context:  Use web search to locate related PRs or documentation and weigh them alongside `01_SPEC.json` when interpreting intent.

# 📤 Output
1. **Inline updates** — replace / append comments directly in‐file:
   ```solidity
   // @audit Reentrancy: external call precedes state update
   // ↳ After review: guard `nonReentrant` present → no exploit
   // @audit-ok: nonReentrant modifier ensures single execution
```

2. **Updated** `03_AUDITMAP.json`

   ```jsonc
   {
     "audit_items": [
       {
         "id": "03523523",
         "file": "src/Vault.sol",
         "line": 152,
         "snippet": "call{value: amount}();",
         "risk_category": "Reentrancy",
         "description": "External transfer before buffer update; nonReentrant missing",
         "status": "Vuln",               // or "ok"
         "proof_trace": [
           "Vault.withdraw (L140‑170)",
           "↳ _transfer (L95‑112)"
         ],
         "review_round": 2
       }
     ],
     "summary": {
       "rounds": 4,
       "total_audit_flags": 21,
       "high_risk_hotspots": ["src/Vault.sol:withdraw"],
       "next_focus": "Permission bypass on src/Admin.rs:setConfig"
     }
   }
   ```

# 🧮 Evaluation Framework  (apply to every finding)

1. **Core‑Logic** — depth ≤ 2 & critical TVL / mint / pricing paths
2. **Permissionless Reachability** — prove lack of owner / role guard
3. **Guard Bypass & State Reachability** — enumerate *all* checks, find gaps
4. **Non‑self Attack** — impact > attacker alone
5. **Bug Bounty Scope** — verify in‑scope via `01_SCOPE.json` (if exists)

# 🔍 Review Procedure

```
FOR each @audit in TARGET_FOLDER ordered by file→line:
    IF already re-labelled `@audit-ok` → skip
    1. Derive execution path (AST + callgraph).
       ‑ Show line-number trace in proof_trace.
    2. Research spec alignment: run a web search for related PRs or product documentation and combine those findings with `01_SPEC.json` to understand expected behaviour.
    3. Apply Evaluation Framework (§🧮).
    4. Cross-check similar bugs in bugs_*.json → note variant attacks.
    5. Decide:
        a) Exploitable ⇒ keep @audit, enrich description, set status="Vuln"
        b) Non-exploitable ⇒ transform to @audit-ok, set status="ok"
    6. Update 03_AUDITMAP.json & security-agent/outputs/02_ORDER.json.review_rounds++
REPEAT until no unchecked @audit remain.
```

# 🧠 Required Deep-Dive Tests

* **Step-by-step execution trace** — include in `proof_trace` (file:line)
* **Logical contradiction check** — ensure premises stay jointly satisfiable
* **Guard enumeration** — list modifiers / require / ACL that could block
* **Independent verification** — rely on own reading, not external scanner verdicts
* **Exploitability demonstration** — if doubtful, mark *Need further investigation*

# 📝 Comment Syntax (strict)

```rust
// @audit <Category>: <Short>
// ↳ <Multi‑line detail, ≤120 words>
//
// @audit-ok: <Reason, ≤80 chars>
```

# 🛠️ Methodology

* **Depth‑first within function**: validate inner‑most dangerous ops first.
* Use *internal* chain‑of‑thought; divulge **only** final comments & JSON.
* Limit new annotations per run to 15 for readability.

# ⛔ Constraints

* Do not alter executable logic.
* No duplicate audit entries for identical location.
* Validate JSON & timestamps (RFC3339) before write.

# ✅ Success Criteria

* Every prior @audit reviewed once.
* 03_AUDITMAP.json parses & mirrors code state.
* High‑risk hotspots surfaced.
* summary.next\_focus suggests concrete next steps.

# ==========  PROMPT END  ==========
