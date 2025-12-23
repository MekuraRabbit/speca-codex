
---
Description: Fully autonomous, iterative, **static-only** audit based on formal methods. This prompt **automatically discovers and merges** all `02a` and `02b` outputs, **automatically determines which source files to audit**, and processes the checklist in batches to generate a complete audit map. Dynamic analysis and fuzzing are explicitly excluded.
Usage: `/03_auditmap`
Language: English only.
---

**Core Doctrine: Formal Static Verification as Audit**

Your mission is to perform a comprehensive **static audit** by applying principles from formal methods. You will not execute code or run dynamic tests. Your entire analysis will be based on the static structure of the codebase. You will **prove or disprove formal properties** through static analysis alone.

**The Predicate:**

Each checklist item you process must be interpreted as a formal Predicate with this structure:

```typescript
interface Predicate {
  id: string; // Checklist ID
  property: string; // The property that must hold true
  anti_property: string; // The property that must be proven false
  scope: { files: string[]; functions: string[]; }; // The code under verification
  invariant: string; // An invariant condition that must always be true within the scope
  evidence: { type: "event" | "log" | "metric"; value: string; }; // Observable proof
}
```

---

## Fully Autonomous, Iterative Execution Doctrine

**THIS IS YOUR CORE LOGIC. EXECUTE IT PRECISELY.**

1.  **Automatic Input Discovery & Merging (Run 1 Only):**
    -   On your first run (when `outputs/03_STATE.json` does not exist), you **MUST** perform the following one-time setup:
    -   Scan the `outputs/` directory for all files matching `02a_*.json` and `02b_*.json`.
    -   Load every discovered file and merge their `checklist` arrays into a single, master checklist in memory.
    -   From this master list, extract all unique `id` fields to create the initial `unprocessed_checklist_ids` queue.

2.  **Automatic Scope Discovery (Run 1 Only):**
    -   From the master checklist created above, parse every entry.
    -   Aggregate all file paths and globs found in `file_globs` and `detection_procedure` fields.
    -   Create a unique, comprehensive set of source code files to be audited. This is your audit scope.

3.  **State-Driven Batch Processing (All Runs):**
    -   Your workload is determined by `outputs/03_STATE.json`. You will process the first `batch_size` (default: 20) items from the `unprocessed_checklist_ids` list.

4.  **Append-Only Partial Output:**
    -   Append your findings for the current batch to `outputs/03_AUDITMAP_PARTIAL_<N>.json`, where `<N>` is the current `run_number`.

5.  **State Update and Continuation:**
    -   Your final output **MUST** include a `next_state` object in the metadata, containing the list of remaining `unprocessed_checklist_ids`.
    -   You will also overwrite `outputs/03_STATE.json` with this `next_state` object to ensure the next run continues correctly.

---

## Inputs

1.  **Checklist Parts (discovered automatically):** `outputs/02a_*.json` and `outputs/02b_*.json`.
2.  **State File (managed automatically):** `outputs/03_STATE.json`.
3.  **Source Code (discovered automatically):** Files determined from the checklist content.

---

## Strict Rules for Fully Autonomous Execution

- **No Manual Merging:** You are responsible for finding and merging the `02a` and `02b` files.
- **No Path Argument:** You are responsible for determining the audit scope from the checklist.
- **Honor the Batch:** Process **ONLY** the checklist items assigned to your batch (size 20).
- **Read the State:** On startup, read `outputs/03_STATE.json`. If it doesn't exist, perform the automatic discovery and setup for Run 1.
- **Execute Audit:** Perform the "Two-Phase Static Verification" for **your batch only**, against the files you determined are in scope for those checklist items.
- **Append to Partial File:** Append findings to `outputs/03_AUDITMAP_PARTIAL_<RUN_NUMBER>.json`. Check for duplicates against all existing partial files.
- **Update State and Exit:** Your primary JSON output's `metadata` **MUST** contain a `next_state` object. Overwrite `outputs/03_STATE.json` with this object before finishing your run.

---

## Output: `outputs/03_AUDITMAP_PARTIAL_<N>.json`

Your output is a **partial** file. It must be a valid JSON object containing the findings for your batch and the metadata for the next run.

```json
{
  "metadata": {
    "generated_at": "YYYY-MM-DDTHH:MM:SSZ",
    "stage": "03_static_audit_mapping",
    "run_number": <N>,
    "batch_size": 20,
    "checklist_ids_processed_this_run": [ ... ],
    "next_state": {
      "unprocessed_checklist_ids": [ ... (remaining IDs) ... ],
      "unprocessed_count": <number_of_remaining_ids>
    }
  },
  "audit_items": [
    {
      "check_id": "CHECK-001",
      "file": "path/to/file.go",
      "line": 123,
      "snippet": "code snippet",
      "classification": "vuln" | "needs-investigation",
      "reason": "short explanation",
      "property": "property name",
      "anti_property": "anti-property name",
      "static_detector": "detector ID",
      "evidence_probe": "event or metric name",
      "tags": ["property:slug", "anti:slug"]
    }
  ]
}
```

---

## Procedure (Step-by-step for one autonomous run)

1.  **Preflight & State Management**
    -   Check for `outputs/03_STATE.json`.
    -   **If it exists:** Load `unprocessed_checklist_ids`.
    -   **If it does not exist (Run 1):**
        -   Find and merge all `02a` and `02b` files into a master checklist.
        -   From the master list, create the initial `unprocessed_checklist_ids` queue.
        -   From the master list, determine the full set of source files to audit.
    -   Define your `current_batch` by taking the first 20 IDs from the queue.
    -   Load all existing `03_AUDITMAP_PARTIAL_*.json` files to build a set of existing composite keys for deduplication.

2.  **Execute the Two-Phase Static Verification (for the current batch)**
    -   For each `check_id` in your `current_batch`, audit the relevant source files using the two-phase procedure below.

3.  **Emit / Append**
    -   For every new `@audit` comment, create a corresponding JSON entry.
    -   Check for and discard duplicates.
    -   Collect all new, unique findings in the `audit_items` list.
    -   Calculate the `next_unprocessed_ids` by removing your `current_batch` from the queue.
    -   Construct the final JSON output including the `metadata` and `next_state` objects.
    -   Write the result to `outputs/03_AUDITMAP_PARTIAL_<RUN_NUMBER>.json`.
    -   Overwrite `outputs/03_STATE.json` with the `next_state` object.

---

## Two-Phase Static Verification Procedure

**Execute this entire procedure for EACH checklist item in your batch.**

### **Phase 1: Static Analysis**

*Objective: Analyze the code's structure and data flow without executing it.*

1.  **Predicate Mapping:**
    -   From the current checklist item, formally construct the **Predicate** object.
    -   Identify the exact files and functions defined in `Predicate.scope` (from `file_globs` and `detection_procedure`).
    -   Map the `Predicate.invariant` to the specific lines of code where it must hold.

2.  **Static Detection:**
    -   Execute the `detection_procedure` (e.g., Semgrep, regex, grep) from the checklist item.
    -   If a match is found, immediately create an `@audit` annotation. This is a potential violation of the `Predicate.property`.

3.  **Data Flow Analysis:**
    -   Trace all data flows originating from external inputs (RPC calls, user transactions, etc.) that reach the `Predicate.scope`.
    -   Formally verify if any data flow path could lead to a violation of the `Predicate.invariant`.
    -   Look for missing validation, sanitization, or access control checks.

4.  **Call Graph Analysis:**
    -   Construct the call graph for functions within `Predicate.scope`.
    -   Verify that security-critical functions (validation, access control) are called **before** state-changing operations.
    -   Identify any execution paths that bypass these checks.

### **Phase 2: Evidence Verification**

*Objective: Statically verify the system's observability claims.*

1.  **Evidence Existence:**
    -   Statically search the codebase to confirm that the `Predicate.evidence` (e.g., the event `event Transfer(...)`, log statement, metric increment) is defined.

2.  **Evidence Correlation:**
    -   Using static analysis (call graphs, data flow), prove that a valid execution path that satisfies `Predicate.property` **must** lead to the generation of `Predicate.evidence`.
    -   If a path exists where the property is satisfied but the evidence is not generated, this is a finding (lack of observability).

---

## Inline Commenting Standard

Insert comments **directly above** the relevant code span. Use one-line tokens with explicit tagging:

-   **Flag:**
    `// @audit <CHECK_ID> [vuln|needs-investigation] -- <short reason>; property=<name>; anti_property=<name>; static_detector=<id>; evidence_probe=<event|metric>; tags=property:<slug>,anti:<slug>`

-   **Safe:**
    `// @audit-ok <CHECK_ID> -- <safety rationale>; property=<name>; ok_condition=<identifier>; evidence_probe=<event|metric>; tags=property:<slug>,ok:true`

---

## Finding Classification

-   **`vuln`** — Property fails; exploit is demonstrated or highly confident through static analysis.
-   **`needs-investigation`** — Property or anti-property is suspected but impact or reachability needs further confirmation.

---

## Deduplication & Append Policy

-   **Composite key:** `<check_id>|<file>|<line>|<hash(snippet)>`.
-   Skip entries with existing composite keys; never edit prior items.
