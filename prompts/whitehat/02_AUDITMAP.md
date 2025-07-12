**Task  – Annotate Code with `@audit` Comments (WHITEHAT\_02)**

Save the result to **`security-agent/outputs/WHITEHAT_02_AUDITMAP.json`** and print *only* that JSON in the chat when finished.

---

### 1  Load your workspace

| File                                                      | Purpose                                                              |
| --------------------------------------------------------- | -------------------------------------------------------------------- |
| `security-agent/outputs/WHITEHAT_01b_AUDITMAP_ORDER.json` | Ordered `function_chunks` + `done_index` for resume-safe processing. |
| `security-agent/outputs/WHITEHAT_01_SPEC.json`            | Specs: user-flows, requirements, architecture, critical assets.      |
| `security-agent/outputs/00_AST.json`                      | AST extract: `stateWrites`, `externalCalls`, `modifiers`.            |
| `security-agent/outputs/callgraphs/*.dot`                 | Contract call-graphs for reachability & layer checks.                |

---

### 2  White-hat mental model to apply

* **Suspicion by default** – assume a bug exists.
* **Defense pyramid** – Core-Logic → Guard → Permission → Economic checks.
* **Call-graph layering** – Entry (EOA) ➜ Mid-tier ➜ Sensitive sinks; confirm each layer.
* **Attacker ROI** – focus on shortest, profit-positive path.
* **Trust boundary clarity** – functions gated by `onlyOwner`/`onlyRole`/`onlyTimelock` are trusted and skipped unless the guard is missing or wrong.
* **Combination mindset** – “safe alone, dangerous together” is always possible.

---

### 3  Comment syntax (insert directly in source)

```
// @audit     <SpecID|N/A> | <UF-ID|N/A> | <Var/Fn> | <攻撃一歩目要約>（80–120 日本語字）
```

```
// @audit-ok  <根拠>（60–100 日本語字）
```

Include at least *two* of: Spec ID, UF-ID, state variable, attack scenario.
Never finish with vague words such as “危険”.

---

### 4  Three-round ToT loop with call-graph reasoning

Process each chunk whose `done_index` is still below `functions.length`.

```
for round in 1..3:
    for fn in chunk.functions[done_index:]:
        if fn has trusted modifier → skip
        INTERNAL_THINK (no output):
            1. Match spec requirement / invariant.
            2. Walk call-graph (.dot) two layers down:
               • verify Guard → Permission → Sink order.
               • list missing or bypassable checks.
            3. Draft attacker steps + profit source.
            4. Is ROI positive?
        Insert @audit or @audit-ok comment into code.
        Append entry to audit_items[].
        done_index += 1; save order file immediately.
    META_REFLECTION:
        self-score comment depth (1–5); if <3, rewrite.
```

Update `WHITEHAT_01b_AUDITMAP_ORDER.json` after every function so progress survives interruption.

---

### 5  Output JSON schema

```json
{
  "audit_items": [
    {
      "file": "src/Vault.sol",
      "line": 152,
      "snippet": "call{value: amount}();",
      "risk_category": "Reentrancy",
      "description": "UF-Withdraw-1 で buffer 更新前に外部送金が発生し totalBacking < totalSupply となる恐れ",
      "status": "Vuln" | "ok"
    }
  ],
  "summary": {
    "rounds": 3,
    "total_audit_flags": <int>,
    "high_risk_hotspots": ["..."],
    "next_focus": "..."
  }
}
```

---

### 6  Final rules

1. Save all source files with embedded comments.
2. Write the JSON object above to `security-agent/outputs/WHITEHAT_02_AUDITMAP.json`.
3. **Respond in the chat with that JSON only — no extra text.**

Begin.
