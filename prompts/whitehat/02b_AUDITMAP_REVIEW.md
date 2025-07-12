**Task – Refine `@audit` Comments (WHITEHAT \_02 Review)**

Save the result to **`security-agent/outputs/WHITEHAT_02_AUDITMAP.json`** and print *only* that JSON in the chat when finished.

---

### 1  Load your workspace

| File                                               | Purpose                                                          |
| -------------------------------------------------- | ---------------------------------------------------------------- |
| `security-agent/outputs/WHITEHAT_01_SPEC.json`     | Specs: user-flows, requirements, architecture, critical assets.  |
| `security-agent/outputs/callgraphs/*.dot`          | Graphviz call-graphs – reachability, layer ordering, guard hops. |
| `security-agent/outputs/WHITEHAT_02_AUDITMAP.json` | Current `@audit` / `@audit-ok` metadata to be re-examined.       |

---

### 2  White-hat mental model to apply

* **Suspicion by default** – assume a bug exists.
* **Defense pyramid** – Core-Logic ➜ Guard ➜ Permission ➜ Economic checks.
* **Call-graph layering** – Entry (EOA) ➜ Mid-tier ➜ Sensitive sinks; confirm that every hop has an appropriate guard.
* **Attacker ROI** – focus on shortest, profit-positive path.
* **Combination mindset** – safe modules can break in combination.
* **Trust boundary clarity** – functions gated by `onlyOwner`, `onlyRole`, etc. are trusted and skipped unless that guard is missing or wrong.

---

### 3  Evaluation frame (logic + layered defense)

1. **Core-Logic** – TVL, liquidation, mint-burn, interest, or any value-critical path.
2. **Permissionless reachability** – prove via call-graph that the path lacks owner/role checks.
3. **Guard bypass & state reachability** – list all `modifier`/`require`/`if-revert`, show how a bad state can still be reached.
4. **Non-self attack** – impact extends beyond the attacker.
5. **Bug-bounty scope** – confirm item is in scope (`01_SCOPE.json`).

> `onlyOwner` etc. are treated as trusted unless the guard is absent or faulty.

---

### 4  Comment syntax (write directly in code)

```
// @audit     <SpecID|N/A> | <UF-ID|N/A> | <Var/Fn> | <攻撃一歩目要約>（80–120 日本語字）
```

```
// @audit-ok  <根拠>（60–100 日本語字）
```

Include at least two of: Spec ID, UF-ID, state variable, attack scenario.
Never finish with vague words like “危険”.

---

### 5  Three-round Tree-of-Thought review

```
for round in 1..3:
    • Prioritise functions reachable from EOA within call-graph depth ≤ 2.
    • For each existing @audit line:
         INTERNAL_THINK (no output):
             1. Match spec requirement / invariant.
             2. Traverse .dot graph → confirm Guard/Permission layering.
             3. Draft attacker steps + profit.
             4. ROI positive?
         Update comment → @audit-ok or deeper @audit.
    • Discover new risky lines by scanning call-graphs for unguarded sinks; add @audit.
    • META_REFLECTION: score depth 1-5; if <3, rewrite.
```

---

### 6  Output JSON schema

```json
{
  "review_round": 3,
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
    "total_audit_flags": <int>,
    "high_risk_hotspots": ["..."],
    "next_focus": "..."
  }
}
```

---

### 7  Completion rules

1. Save all updated source files with comments.
2. Write the JSON object above to `security-agent/outputs/WHITEHAT_02_AUDITMAP.json`.
3. **Reply in chat with that JSON only — no extra text.**

Begin.
