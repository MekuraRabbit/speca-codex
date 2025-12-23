
---
Description: Generate a high-fidelity audit checklist for the most critical security properties: those that cover trust boundary edges. This is Stage 1 of the checklist generation.
Usage: `/02a_checklist`
Language: English only.
Execution hint: Run after `/01c_prop`. This is the first verification-focused step.
---
**Always use /serena for these development tasks to maximize token efficiency:**

# **Checklist Generation Prompt (Stage 1: Trust Boundaries)**

**Goal**
Generate a high-fidelity audit checklist for the **most critical** security properties: those that cover **trust boundary edges**. This prompt focuses exclusively on properties where `covers.is_boundary_edge == true`.

**Output (required file):** `outputs/02a_CHECKLIST_BOUNDARIES.json`

---

## 1) Inputs

1.  **Property Catalog (Authoritative):** `outputs/01c_PROP.json`
2.  **System Specification (Context):** `outputs/01_SPEC.json`
3.  **Trust Model (Context):** `outputs/01b_TRUSTMODEL.json`

---

## 2) Checklist Generation Logic: Verifying Trust Boundaries

**CRITICAL FILTERING LOGIC:**

**Step A: Extract ALL Boundary Properties**
1. Parse `01c_PROP.json` completely.
2. Create a list of **ALL** properties where `property.covers.is_boundary_edge == true`.
3. **MANDATORY VERIFICATION:** Before proceeding, you **MUST** output a list of all boundary property IDs found. This list should include properties covering edges such as:
   - User transaction submission edges (e.g., `EDGE-USER-SUBMIT-TX`)
   - Consensus-to-Execution communication edges (e.g., `EDGE-CL-SENDS-FORKCHOICE`, `EDGE-CL-SENDS-NEWPAYLOAD`, `EDGE-CL-SENDS-GETPAYLOAD`)
   - Any other trust boundary edges defined in the trust model

4. **COMPLETENESS CHECK:** Cross-reference your extracted list against `01b_TRUSTMODEL.json` to ensure **no boundary edges are missing**. If the trust model defines a boundary edge that has a corresponding property in `01c_PROP.json`, it **MUST** be included.

**Step B: Process Each Boundary Property**
You will process **EVERY** property in the filtered list. Missing even one boundary property is a critical failure.

For each property in this filtered list, you must perform the following tasks:

#### **Task 1: Generate a Check for the Boundary Edge**
1.  You **MUST** generate one dedicated check for the primary graph element, which will be the boundary edge itself (e.g., `EDGE-CL-SENDS-NEWPAYLOAD`).
2.  **Title Convention:** The title **MUST** be "Verify Trust Boundary Integrity for [Edge ID]".
3.  **Goal:** The check must verify the security of the trust boundary edge. Focus on data validation, authentication, transport security, and preventing unauthorized data from crossing the boundary.

#### **Task 2: Generate Checks for Associated Nodes**
1.  Look at the `graph_elements` array for the same property.
2.  If there are any `Action` or `State` nodes associated with the boundary crossing, generate additional checks for them, focusing on how they support the security of the boundary.

### **How to Design Each Checklist Item**

*   **`id`**: `CL-<PROP_ID>-<NODE/EDGE_ID>`.
*   **`property_id`**: The ID of the property being checked.
*   **`graph_element_under_test`**: The specific Node or Edge ID being audited.
*   **`title`**: **MUST** focus on implementation verification.
    *   **Boundary Edge Check:** "Verify Trust Boundary Integrity for [Edge ID]: [Brief description of the check's goal]."
    *   **Action Node Check:** "Verify that the implementation of `[Action Node Label]` correctly enforces [Security Guarantee] to protect the boundary."
*   **`bug_class`**, **`risk_category`**, **`severity_hint`**: Provide accurate and specific values. Boundary checks are almost always `Critical`.
*   **`detection_procedure`**: A detailed, step-by-step guide for a human auditor. Reference specific Go files and functions where possible.
*   **`executable_checks`**: An array of structured, machine-runnable steps (`tool`, `command`, `assertion`).
*   **`notes`**: **MANDATORY** - Must provide full traceability to the formal model.
    *   **Required Format:** `"Traceability: Property [property_id] → Edge [graph_element_under_test]. This check verifies the implementation of the critical trust boundary [Edge ID], which is essential for [Property ID] to hold true in the code."`
    *   **Example:** `"Traceability: Property PROP-EDGE-CL-SENDS-GETPAYLOAD-001 → Edge EDGE-CL-SENDS-GETPAYLOAD. This check verifies the implementation of the critical trust boundary EDGE-CL-SENDS-GETPAYLOAD, which is essential for PROP-EDGE-CL-SENDS-GETPAYLOAD-001 to hold true in the code."`
    *   **CRITICAL:** Every `notes` field **MUST** begin with `"Traceability: Property [property_id]"` to ensure audit trail completeness.

---

## 3) Required Output Format (JSON)

**File:** `outputs/02a_CHECKLIST_BOUNDARIES.json`

*   The output file **MUST** contain a `metadata` object and a `checklist` array.
*   The `metadata` object **MUST** include:
    *   `boundary_properties_processed`: An array listing **ALL** property IDs that were processed (for verification).
    *   `boundary_edges_covered`: An array listing **ALL** edge IDs that have corresponding checks.
    *   `total_checks`: The total number of checklist items generated.
*   The `checklist` array will contain the generated checklist items for the **boundary edge properties only**.

**Example `metadata` structure:**
```json
{
  "metadata": {
    "generated_at": "2025-01-15T10:30:00Z",
    "stage": "02a_boundaries",
    "boundary_properties_processed": [
      "PROP-EDGE-USER-SUBMIT-TX-001",
      "PROP-EDGE-CL-SENDS-FORKCHOICE-001",
      "PROP-EDGE-CL-SENDS-NEWPAYLOAD-001",
      "PROP-EDGE-CL-SENDS-GETPAYLOAD-001"
    ],
    "boundary_edges_covered": [
      "EDGE-USER-SUBMIT-TX",
      "EDGE-CL-SENDS-FORKCHOICE",
      "EDGE-CL-SENDS-NEWPAYLOAD",
      "EDGE-CL-SENDS-GETPAYLOAD"
    ],
    "total_checks": 38
  },
  "checklist": [...]
}
```

**FINAL VERIFICATION:** Before writing the output file, confirm that the number of unique boundary edges in `boundary_edges_covered` matches the number of boundary edges defined in `01b_TRUSTMODEL.json`.
