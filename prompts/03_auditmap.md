
---
Description: Fully autonomous, iterative, **static-only** audit. This version enforces strict output formats (`audit_items`, `verified_items`), correct state management, and **mandates source code annotation** using the `file` tool.
Usage: `/03_static_audit_v2`
Language: English only.
---

**Core Doctrine: Formal Static Verification & Annotation**

Your mission is to perform a comprehensive **static audit** and **annotate the source code** with your findings. You will not execute code. Your entire analysis will be based on the static structure of the codebase. Each checklist item is a formal **Predicate** to be verified.

**The Predicate:**

Each checklist item you process must be interpreted as a formal Predicate with this structure:

```typescript
interface Predicate {
  id: string; // Checklist ID
  property: string; // The property that must hold true
  scope: { files: string[]; functions: string[]; }; // The code under verification
  invariant: string; // An invariant condition that must always be true within the scope
}
```

---

## Autonomous, Iterative Execution Doctrine (V2)

**THIS IS YOUR CORE LOGIC. EXECUTE IT PRECISELY.**

1.  **Automatic Input Discovery (Run 1 Only):**
    -   On your first run (when `outputs/03_STATE.json` does not exist), you **MUST** scan the `outputs/` directory for all files matching the glob pattern `02[ab]_*.json`. This ensures both `02a` (boundaries) and all `02b` (remaining) files are included.
    -   Merge their `checklist` arrays into a single master list and create the initial `unprocessed_checklist_ids` queue.

2.  **State-Driven Batch Processing (All Runs):**
    -   Your workload is determined by `outputs/03_STATE.json`. You will process the first `batch_size` (default: 20) items from the `unprocessed_checklist_ids` list.

3.  **Source Code Annotation (MANDATORY):**
    -   For every item you analyze, you **MUST** add an `@audit` or `@audit-ok` comment to the corresponding source code file. You will use the `file` tool with the `edit` action for this. This is not optional.

4.  **Strict Output Formatting:**
    -   Your final JSON output **MUST** contain two top-level keys: `audit_items` for findings (`vuln`, `needs-investigation`) and `verified_items` for successful checks (`PASS`).
    -   **DO NOT** use the key `annotations`.

5.  **State Update and Continuation:**
    -   Your final JSON output's `metadata.next_state` object is the single source of truth for the next run. It **MUST** contain the correct remaining `unprocessed_checklist_ids`.

---

## Output: `outputs/03_AUDITMAP_PARTIAL_<N>.json`

Your output **MUST** follow this structure precisely.

```json
{
  "metadata": {
    "generated_at": "YYYY-MM-DDTHH:MM:SSZ",
    "stage": "03_static_audit",
    "run_number": <N>,
    "checklist_ids_processed_this_run": [ ... ],
    "next_state": {
      "unprocessed_checklist_ids": [ ... (remaining IDs) ... ],
      "unprocessed_count": <number_of_remaining_ids>
    }
  },
  "audit_items": [
    {
      "check_id": "...",
      "file": "...",
      "line": 123,
      "classification": "vuln" | "needs-investigation",
      "summary": "..."
    }
  ],
  "verified_items": [
    {
      "check_id": "...",
      "file": "...",
      "line": 456,
      "summary": "Property verified via static analysis."
    }
  ]
}
```

---

## Procedure

1.  **Preflight & State Management**
    -   Check for `outputs/03_STATE.json`.
    -   **If it exists:** Load `unprocessed_checklist_ids`.
    -   **If it does not exist (Run 1):**
        -   Find and merge all `outputs/02[ab]_*.json` files.
        -   Create the initial `unprocessed_checklist_ids` queue.
    -   Define your `current_batch` by taking the first 20 IDs from the queue.

2.  **Execute Two-Phase Static Verification (In Memory)**
    -   For each `check_id` in your `current_batch`, perform the two-phase static verification.
    -   Do not write to the final JSON yet. Instead, generate a list of analysis results in memory. Each result should contain the information needed for both the `@audit` comment and the final JSON output (e.g., file, line, classification, summary).

3.  **Apply Source Code Annotations (MANDATORY)**
    -   Iterate through the analysis results from the previous step.
    -   For each result, construct the appropriate `@audit` or `@audit-ok` comment string.
    -   Use the `file` tool's `edit` action to insert this comment string directly above the relevant line in the source code file. You may need to call the `file` tool multiple times, once for each annotation.

4.  **Emit Final JSON**
    -   After all source code annotations for the batch have been applied, iterate through your in-memory analysis results again.
    -   Sort each result into the `audit_items` list (if `vuln` or `needs-investigation`) or the `verified_items` list (if `PASS`).
    -   Construct the final JSON output object according to the strict format defined above, including the `metadata` and `next_state`.
    -   Write the result to `outputs/03_AUDITMAP_PARTIAL_<RUN_NUMBER>.json`.
    -   Overwrite `outputs/03_STATE.json` with the `next_state` object.

---

## Two-Phase Static Verification Procedure

(This procedure remains the same: Static Analysis and Evidence Verification)

### **Phase 1: Static Analysis**
1.  **Predicate Mapping**
2.  **Static Detection**
3.  **Data Flow Analysis**
4.  **Call Graph Analysis**

### **Phase 2: Evidence Verification**
1.  **Evidence Existence**
2.  **Evidence Correlation**

---

## Inline Commenting Standard

(This standard remains the same)

-   **Flag:** `// @audit <CHECK_ID> [vuln|needs-investigation] -- <short reason>`
-   **Safe:** `// @audit-ok <CHECK_ID> -- <safety rationale>` -- <safety rationale>` -- <safety rationale>` <safety rationale>` <safety rationale>`
<safety rationale>`
