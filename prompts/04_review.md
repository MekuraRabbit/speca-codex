
---
Description: Reviews `audit_items` from the 03 stage in batches. This version introduces a formal verification mindset to minimize false positives and ensures a structured, repeatable review process.
Usage: `/04_review`
Language: English only.
---

**Core Doctrine: Formal Review & False Positive Reduction**

Your mission is to act as a skeptical, formal verification expert. For every `audit_item` presented, your default assumption is that it is a **false positive**. You must find **irrefutable evidence** to either confirm it as a `VULNERABILITY` or disprove it as a `FALSE_POSITIVE`. Ambiguity is not acceptable.

---

## Formal Verification Mindset (MANDATORY)

1.  **Counterexample is King**: To confirm a vulnerability, you must construct a plausible **counterexample** (a scenario, a set of inputs, or a sequence of calls) that demonstrates the `anti_property` of the corresponding checklist item. A vague description is not enough.
2.  **Invariant as a Shield**: To disprove a vulnerability, you must identify a specific **invariant** (a condition that always holds true, like `balance[user] >= amount`) or a **guard** (like a `nonReentrant` modifier) that makes the counterexample impossible.
3.  **Traceability is Non-Negotiable**: Every claim, whether confirming or disproving, must be backed by a `proof_trace`—a sequence of code locations (`file:line`) that logically supports your conclusion.

---

## Autonomous, Iterative Execution Doctrine

1.  **Automatic Input Discovery (Run 1 Only):**
    -   Scan `outputs/` for all `03_AUDITMAP_PARTIAL_*.json` files.
    -   Merge all `audit_items` from these files into a single master list.
    -   Create the initial queue and save it to `outputs/04_STATE.json`.

2.  **State-Driven Batch Processing (All Runs):**
    -   Load the `unprocessed_audit_items` queue from `outputs/04_STATE.json`.
    -   Process a batch of **20 items**.

3.  **Strict Output Formatting:**
    -   Generate a list of `reviewed_items`.
    -   Update `outputs/04_STATE.json` with the remaining items.

---

## Output: `outputs/04_REVIEW_PARTIAL_<N>.json`

```json
{
  "metadata": { ... },
  "reviewed_items": [
    {
      "original_item": { ... }, // The full audit_item from the 03 stage
      "verdict": "VULNERABILITY" | "FALSE_POSITIVE",
      "classification": "Reentrancy" | "DoS" | "...", // If verdict is VULNERABILITY
      "reasoning": "The nonReentrant modifier on line 85 makes the identified attack path impossible.",
      "proof_trace": [ // The logical steps to your conclusion
        "contract.sol:152", // The point of concern
        "lib.sol:85",       // The identified guard
        "contract.sol:140"  // The function entrypoint with the modifier
      ]
    }
  ]
}
```

---

## Procedure (Step-by-step for one autonomous run)

1.  **Preflight & State Management**
    -   Load or create the `unprocessed_audit_items` queue.
    -   Define your `current_batch`.

2.  **Execute Formal Review**
    -   For each `item` in your `current_batch`:
        -   **a. Analyze the Original Claim**: Understand the `summary` and `attack_vector` from the 03 stage.
        -   **b. Search for a Counterexample**: Attempt to construct a scenario where the attack is possible. Review the source code (`file:line`) and the corresponding checklist item from the `02_CHECKLIST` files.
        -   **c. Search for a Guard/Invariant**: Systematically look for code (`require` statements, modifiers, safe math libraries, etc.) that would block the counterexample.
        -   **d. Form a Verdict**: 
            -   If a plausible counterexample exists and no definitive guard is found, the `verdict` is `VULNERABILITY`.
            -   If a definitive guard or invariant is found, the `verdict` is `FALSE_POSITIVE`.
        -   **e. Construct Proof**: Build the `proof_trace` that justifies your verdict.
        -   **f. Generate Result**: Create the `reviewed_item` object in memory.

3.  **Emit Final JSON**
    -   Construct the final JSON output, including `metadata` and the list of `reviewed_items`.
    -   Write the result to `outputs/04_REVIEW_PARTIAL_<RUN_NUMBER>.json`.
    -   Overwrite `outputs/04_STATE.json` with the updated state.

---

## Constraints & Success Criteria

-   **No Source Code Modification**: Unlike the original prompt, you will **NOT** modify the source code to add `@audit-ok` comments. The review results will live exclusively in the `04_REVIEW` files.
-   **Success**: Every `audit_item` from the 03 stage is reviewed, and a clear, evidence-backed verdict is rendered for each one.
