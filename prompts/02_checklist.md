
---
Description: Generate a high-fidelity audit checklist by translating formal security properties into concrete verification tasks. The checklist focuses on verifying the implementation of the nodes and edges defined in the Program Graph, especially those identified as trust boundaries.
Usage: `/02_checklist`
Language: English only.
Execution hint: Run after `/01c_prop`. This is the final, verification-focused step.
---
**Always use /serena for these development tasks to maximize token efficiency:**

# **Checklist Generation Prompt**

**Goal**
Translate the formal properties from `01c_PROP.json` into a concrete audit checklist. The checklist's purpose is not to re-verify the logic of the graph, but to **verify that the source code correctly implements the behavior defined by the graph's nodes and edges**.

**Output (required file):** `outputs/02_CHECKLIST.json`

---

## 1) Inputs

1.  **Property Catalog (Authoritative):** `outputs/01c_PROP.json`
2.  **System Specification (Context):** `outputs/01_SPEC.json`
3.  **Trust Model (Context):** `outputs/01b_TRUSTMODEL.json`

---

## 2) Checklist Generation Logic: Verifying the Graph Implementation

For each **in-scope** property from `01c_PROP.json`, generate checklist items that focus on auditing the implementation of the referenced `graph_elements`.

**CRITICAL: Sub-Graph Analysis:** Your checklist generation must be recursive. You MUST generate checks for the `graph_elements` of properties related to the main graph, and ALSO for properties related to each `sub_graph`.

### **Core Logic: From Formal Model to Implementation Audit**

The previous step (`01c_prop`) established the *logical* security of the system based on the graph model. This step verifies that the *code* actually matches the model.

1.  **For each property, identify the critical graph elements:** Look at the `graph_elements` array and the `reachability_rationale`.
2.  **Generate checks for critical `Action` nodes:** If the rationale relies on an `Action` node (e.g., `ACTION-EL-VALIDATE-JWT`) to enforce security, create a check to audit the implementation of that action.
3.  **Generate checks for critical `Edge` transitions:** If the rationale relies on data being passed securely across an `edge` (especially a `boundary_edge`), create a check to audit the code that handles that specific data transition.

### **How to Design Each Checklist Item**

*   **`id`**: `CL-<PROP_ID>-<NODE/EDGE_ID>`.
*   **`title`**: **MUST** focus on implementation verification.
    *   **Action Node Check:** "Verify that the implementation of `[Action Node Label]` correctly enforces [Security Guarantee]."
    *   **Edge Transition Check:** "Verify that the code handling the `[Edge Label]` transition correctly protects the integrity of `[Data Involved]`."

*   **`detection_procedure`**: Guide the auditor to the specific code that implements the node or edge.
    *   "1. Locate the source code corresponding to the `ACTION-EL-VALIDATE-JWT` node. 2. Review the function to ensure it rejects tokens with the 'none' algorithm. 3. Confirm all possible failure cases result in a transition to the `STATE-EL-REQUEST-REJECTED` state."

*   **`executable_checks`**: An array of structured steps that a human or machine can execute to verify the property.
    *   `step`: Sequence number (1, 2, ...).
    *   `description`: What to do in this step.
    *   `tool`: The tool to use (e.g., "manual", "curl", "grep", "go test").
    *   `command`: The exact command to run (if applicable).
    *   `assertion`: The expected result (e.g., "response.status == 401").

*   **`notes`**: **MUST** link back to the formal model.
    *   **Format:** `"This check verifies the implementation of the node/edge [ID], which is the critical element ensuring the reachability conclusion for property [Property ID] holds true in the actual code."`

---

## 3) Required Output Format (JSON)

**File:** `outputs/02_CHECKLIST.json`

```json
{
  "metadata": { /* ... */ },
  "checklist": [
    // Checklist items for PROP-GRAPH-AUTH-PATH-INTEGRITY
    {
      "id": "CL-PROP-GRAPH-AUTH-PATH-INTEGRITY-ACTION-EL-VALIDATE-JWT",
      "property_id": "PROP-GRAPH-AUTH-PATH-INTEGRITY",
      "graph_element_under_test": "ACTION-EL-VALIDATE-JWT",
      "title": "Verify that the implementation of the 'EL Validates JWT' action correctly enforces HS256 and expiry validation.",
      "bug_class": "Authentication Bypass",
      "risk_category": "integrity",
      "severity_hint": "Critical",
      "detection_procedure": [
        "1. Locate the Go function(s) that implement the JWT validation logic.",
        "2. Manually review for common JWT vulnerabilities: algorithm confusion ('none'), lack of expiry check, improper signature validation.",
        "3. Confirm that any failure in this action leads to a state equivalent to STATE-EL-REQUEST-REJECTED and does not proceed."
      ],
      "executable_checks": [
        {
          "step": 1,
          "description": "Run the JWT handler unit tests with coverage for 'none' algorithm and expiration.",
          "tool": "go test",
          "command": "go test -v ./node -run TestJWTHandler",
          "assertion": "Tests pass and output indicates rejection of invalid tokens."
        },
        {
          "step": 2,
          "description": "Attempt to decode a token with 'none' alg manually to verify rejection.",
          "tool": "manual",
          "command": "N/A",
          "assertion": "Function returns error 'invalid algorithm'"
        }
      ],
      "notes": "This check verifies the implementation of the ACTION-EL-VALIDATE-JWT node. The formal model's conclusion that the anti-property is unreachable depends entirely on this action being implemented correctly."
    },
    {
      "id": "CL-PROP-GRAPH-AUTH-PATH-INTEGRITY-EDGE-CL-SENDS-REQUEST",
      "property_id": "PROP-GRAPH-AUTH-PATH-INTEGRITY",
      "graph_element_under_test": "EDGE-CL-SENDS-REQUEST",
      "title": "Verify that the data 'DATA-JWT-REQUEST' is protected during the 'CL sends RPC request' transition.",
      "bug_class": "Man-in-the-Middle (MitM)",
      "risk_category": "integrity",
      "severity_hint": "Critical",
      "detection_procedure": [
        "1. Confirm the Engine API is only exposed over a secure channel (e.g., localhost IPC or TLS-encrypted TCP).",
        "2. Review client and server configurations to ensure they do not allow insecure connections for the Engine API."
      ],
      "notes": "This check verifies the security of the trust boundary edge EDGE-CL-SENDS-REQUEST. While the JWT provides application-level security, the transport-level security of the edge itself must also be confirmed."
    }
  ]
}
```
