
---
Description: Iteratively generate a complete audit checklist for all properties not covered in Stage 1. This prompt is designed to be run multiple times (Stage 2).
Usage: `/02b_checklistrem`
Language: English only.
Execution hint: Run after `/02a_checklist`. Run this multiple times until the state file is empty.
---
**Always use /serena for these development tasks to maximize token efficiency:**

# **Checklist Generation Prompt (Stage 2: Remaining Properties - Iterative)**

**Goal**
Iteratively generate a complete audit checklist for all properties **not** covered in Stage 1. This prompt is designed to be run multiple times. It reads a state file to determine which properties are left to process, generates checks for a small batch, and then writes the remaining work back to the state file for the next run.

**Output (required files):**
1.  `outputs/02b_CHECKLIST_PARTIAL_<N>.json`: A partial checklist for the current batch. `<N>` is the run number.
2.  `outputs/02b_STATE.json`: An updated state file for the next run.

---

## 1) Inputs

1.  **Property Catalog (Authoritative):** `outputs/01c_PROP.json`
2.  **Boundary Checklist (for exclusion):** `outputs/02a_CHECKLIST_BOUNDARIES.json`
3.  **State File (for resuming):** `outputs/02b_STATE.json` (This file may not exist on the first run).

---

## 2) Iterative Checklist Generation Logic

Your task is to manage a queue of properties and process a small batch in each run.

### **Task 1: Determine the Work Queue (List of Properties to Process)**

1.  **On the VERY FIRST RUN (`/02b` is executed for the first time):**
    *   The state file `outputs/02b_STATE.json` will **not** exist.
    *   **Step 1.1:** Read all property IDs from `01c_PROP.json`.
    *   **Step 1.2:** Read all `property_id` values from `02a_CHECKLIST_BOUNDARIES.json` (these are the ones already processed).
    *   **Step 1.3:** Create a final list of **unprocessed property IDs** by subtracting the list from 1.2 from the list from 1.1. This is your master work queue (should be ~180 properties).

2.  **On ALL SUBSEQUENT RUNS (`/02b` is executed again):**
    *   The state file `outputs/02b_STATE.json` **will** exist.
    *   **Step 2.1:** Read the list of `unprocessed_property_ids` directly from this JSON file. This is your current work queue.

### **Task 2: Process a Batch of Properties**

1.  **Take a Batch:** From your current work queue, take the **first 20 property IDs**. This is your batch for this run.
2.  **Generate Checks (Sampling Approach):** For each of the 20 properties in your batch, you **MUST** generate **exactly one** checklist item.
    *   This single check should focus on the property's `primary_element` as defined in its `covers` object.
    *   **CRITICAL:** Do NOT iterate through all `graph_elements` for a property. Generate only one check per property to keep the output manageable.
3.  **Design each checklist item** using the same high-quality standards as in Stage 1 (detailed `id`, `title`, `bug_class`, `severity_hint`, `detection_procedure`, `executable_checks`, `notes`).

### **Task 3: Update and Write Output Files**

1.  **Generate Partial Checklist:**
    *   Create a file named `outputs/02b_CHECKLIST_PARTIAL_<N>.json`, where `<N>` is the run number (1 for the first run, 2 for the second, and so on).
    *   This file will contain the `metadata` and a `checklist` array with the ~20 items you just generated.

2.  **Update and Write State File:**
    *   **Step 3.1:** Remove the 20 property IDs you just processed from your work queue.
    *   **Step 3.2:** Create a new state file `outputs/02b_STATE.json`.
    *   **Step 3.3:** This file **MUST** contain a JSON object with one key, `unprocessed_property_ids`, whose value is the list of remaining, unprocessed property IDs.
    *   **CRITICAL:** If the list of remaining IDs is empty, you have finished. The `unprocessed_property_ids` array should be empty `[]`.

---

## 3) Required Output Format (JSON)

**Partial Checklist File:** `outputs/02b_CHECKLIST_PARTIAL_<N>.json`
```json
{
  "metadata": { /* ... */ },
  "checklist": [ /* ~20 checklist items from the current batch */ ]
}
```

**State File:** `outputs/02b_STATE.json`
```json
{
  "unprocessed_property_ids": [
    "PROP-NODE-STATE-TX-INVALID-001",
    "PROP-NODE-ACTION-EL-PROCESS-BLOCK-001",
    "... remaining property IDs ..."
  ]
}
```

This iterative process ensures that even if a single run is interrupted or hits a token limit, the next run can seamlessly continue from where the last one left off, guaranteeing the eventual generation of a complete checklist.
