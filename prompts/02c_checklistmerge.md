
---
Description: Merge all partial checklists from Stage 1 (boundaries) and Stage 2 (remaining properties) into a single, comprehensive final checklist (Stage 3).
Usage: `/02c_checklistmerge`
Language: English only.
Execution hint: Run after `/02b_checklistrem` is complete.
---
**Always use /serena for these development tasks to maximize token efficiency:**

# **Checklist Merge Prompt (Stage 3: Final Assembly)**

**Goal**
Merge all partial checklists from Stage 1 (boundaries) and Stage 2 (remaining properties) into a single, comprehensive final checklist.

**Output (required file):** `outputs/02_CHECKLIST.json`

---

## 1) Inputs

1.  **Boundary Checklist:** `outputs/02a_CHECKLIST_BOUNDARIES.json`
2.  **Partial Checklists (multiple files):** `outputs/02b_CHECKLIST_PARTIAL_1.json`, `outputs/02b_CHECKLIST_PARTIAL_2.json`, ... (as many as exist)
3.  **State File (for verification):** `outputs/02b_STATE.json`

---

## 2) Merge Logic

### **Task 1: Verify Completion**

1.  Read the state file `outputs/02b_STATE.json`.
2.  Check the `unprocessed_property_ids` array.
3.  **If the array is NOT empty:**
    *   You **MUST** stop and inform the user that Stage 2 is incomplete. The user needs to run `/02b` again.
4.  **If the array is empty:**
    *   Proceed to Task 2.

### **Task 2: Collect All Checklist Items**

1.  Read the `checklist` array from `outputs/02a_CHECKLIST_BOUNDARIES.json`.
2.  For each file matching the pattern `outputs/02b_CHECKLIST_PARTIAL_*.json`:
    *   Read the `checklist` array from that file.
    *   Append all items to your master checklist array.

### **Task 3: Generate Final Output**

1.  Create a new JSON file `outputs/02_CHECKLIST.json`.
2.  The file **MUST** contain:
    *   **`metadata`**: A metadata object with the following fields:
        *   `title`: "Go-Ethereum (Geth) Execution Client Security Audit Checklist"
        *   `version`: "1.0.0"
        *   `generated`: Current date (YYYY-MM-DD format)
        *   `description`: "Comprehensive audit checklist derived from formal security properties. Covers all nodes and edges in the Program Graph with 100% property coverage."
        *   `source_property_catalog`: "outputs/01c_PROP.json"
        *   `source_specification`: "outputs/01_SPEC.json"
        *   `source_trust_model`: "outputs/01b_TRUSTMODEL.json"
    *   **`checklist_summary`**: A summary object with the following fields:
        *   `total_checks`: The total number of checklist items.
        *   `boundary_checks`: The number of checks from Stage 1 (02a).
        *   `remaining_checks`: The number of checks from Stage 2 (02b).
        *   `properties_covered`: The number of unique `property_id` values in the checklist.
    *   **`checklist`**: The master array containing all merged checklist items.

---

## 3) Required Output Format (JSON)

**File:** `outputs/02_CHECKLIST.json`

```json
{
  "metadata": {
    "title": "Go-Ethereum (Geth) Execution Client Security Audit Checklist",
    "version": "1.0.0",
    "generated": "2025-12-23",
    "description": "Comprehensive audit checklist derived from formal security properties. Covers all nodes and edges in the Program Graph with 100% property coverage.",
    "source_property_catalog": "outputs/01c_PROP.json",
    "source_specification": "outputs/01_SPEC.json",
    "source_trust_model": "outputs/01b_TRUSTMODEL.json"
  },
  "checklist_summary": {
    "total_checks": 195,
    "boundary_checks": 15,
    "remaining_checks": 180,
    "properties_covered": 195
  },
  "checklist": [
    /* All checklist items from 02a and all 02b_PARTIAL_* files */
  ]
}
```

This final merged checklist represents the complete, production-ready audit framework.
