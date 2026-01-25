
---
Description: Generate a comprehensive catalog of formal security properties with 100% coverage. Every node and edge within the system must have at least one corresponding property. Properties for boundary edges are highest priority.
Usage: `/01e_prop`
Language: English only.
Execution hint: Run after `/01d_trustmodel`. This produces the property catalog for checklist generation.
---

# **Security Property Catalog Generation Prompt**

**Goal**
From the System Specification (`01_SPEC.json`) and Trust Model (`01d_TRUSTMODEL.json`), generate a **comprehensive catalog of formal security properties with 100% coverage**. You MUST generate at least one property for **every node** and **every edge** within the `system_under_audit`'s graphs. Properties for **boundary edges** are the highest priority.

**Output (required file):** `outputs/01e_PROP.json`

---

## 1) Inputs

1.  **System Specification (Authoritative):** `outputs/01_SPEC.json`
2.  **Trust Model (Authoritative):** `outputs/01d_TRUSTMODEL.json`

---

## 2) Property Generation & Analysis Logic

### **Task 2.1: Generate Properties with Full Coverage**

**CRITICAL: 100% Coverage Requirement.** You **MUST** generate at least one property for **every single node** and **every single edge** in the `program_graph` and all `sub_graphs`. No internal element may be left without a corresponding property.

#### **2.1.1: Boundary Edge Priority (Highest Priority)**
*   For **each `boundary_edge`** defined in the `TRUSTMODEL` input, you **MUST** generate **multiple, high-priority properties**.
*   These properties must focus on **input validation** and formally state that the transition across the trust boundary is secure.
*   Example Properties for a Boundary Edge:
    *   **Input Validation:** "Data received on edge `EDGE-X` must be validated for correct format, length, and type before being processed by `ACTION-Y`."
    *   **Authentication/Authorization:** "The source of data for edge `EDGE-X` must be authenticated before the transition is allowed."
    *   **Sanitization:** "All string data within `DATA-Z` on edge `EDGE-X` must be sanitized to prevent injection attacks."

#### **2.1.2: Ambiguity and Assumption Coverage**
*   For **each `ambiguity`** in `01_SPEC.json`, generate a property that verifies the chosen `resolution_strategy` is correctly implemented.
*   For **each `implicit_assumption`** in `01_SPEC.json`, generate a property that verifies the assumption holds, or that the system handles the case where it does not.

#### **2.1.3: Internal Node and Edge Coverage**
*   For all other nodes and edges within the system, generate at least one property covering invariants, reachability, data integrity, or control flow.

### **Task 2.2: Perform Formal Reachability Analysis**

This is the core formal analysis task.

**Reachability Analysis Algorithm:**
1.  **Identify Attacker Starting Points:** The set of all attacker starting points is defined as **any `boundary_edge` originating from an `UNTRUSTED` or `SEMI_TRUSTED` external entity**.
2.  **Perform Graph Traversal:** Starting from the `target_node_id` of these boundary edges, perform a graph traversal to find all reachable nodes.
3.  **Check Anti-Property:** For a given `anti_property`, check if the target state is in the set of reachable nodes.
4.  **Verify Path Conditions:** If the target state is reachable, examine the path. If the path does *not* contain the required validation node/edge, then the anti-property is `REACHABLE`.
5.  **Conclude Unreachability:** If all possible paths are proven to pass through the required validation node, then the anti-property is `UNREACHABLE`.

---

## 3) Required Output Format (JSON)

**File:** `outputs/01e_PROP.json`

```json
{
  "metadata": {
    "generated_at": "2025-01-16T16:00:00Z",
    "total_properties": 198,
    "boundary_properties": 23,
    "ambiguity_properties": 15,
    "assumption_properties": 12
  },
  "coverage_summary": {
    "total_nodes": 261,
    "nodes_covered": 261,
    "total_edges": 294,
    "edges_covered": 294,
    "coverage_percentage": 100.0
  },
  "properties": [
    {
      "property_id": "PROP-BOUNDARY-FCU-VALIDATION",
      "covers": {
        "primary_element": "EDGE-CL-SENDS-FCU",
        "element_type": "edge",
        "is_boundary_edge": true
      },
      "property": "The data payload DATA-FORKCHOICE-UPDATE received on the boundary edge EDGE-CL-SENDS-FCU must be fully validated by the action ACTION-EL-VALIDATE-JWT before being used in any subsequent state.",
      "anti_property": "A malformed or malicious DATA-FORKCHOICE-UPDATE payload can propagate past the validation action and corrupt system state.",
      "graph_elements": [
        "EDGE-CL-SENDS-FCU",
        "ACTION-EL-VALIDATE-JWT",
        "DATA-FORKCHOICE-UPDATE"
      ],
      "reachability": "UNREACHABLE",
      "reachability_rationale": "The anti-property is unreachable because the graph structure mandates that any flow from EDGE-CL-SENDS-FCU must pass through ACTION-EL-VALIDATE-JWT.",
      "related_ambiguity_id": null,
      "related_assumption_id": null,
      "notes": "This is a critical boundary property."
    },
    {
      "property_id": "PROP-AMBIGUITY-EIP4844-01",
      "covers": {
        "primary_element": "AMB-EIP4844-01",
        "element_type": "ambiguity",
        "is_boundary_edge": false
      },
      "property": "The implementation must correctly interpret 'valid blob' as defined in the resolution strategy: cryptographic, format, and network rule correctness.",
      "anti_property": "The implementation uses a different interpretation of 'valid blob', leading to inconsistent behavior.",
      "graph_elements": ["STATE-BLOB-TX-RECEIVED", "ACTION-VALIDATE-BLOB"],
      "reachability": "UNKNOWN",
      "reachability_rationale": "This requires manual code review to verify the interpretation.",
      "related_ambiguity_id": "AMB-EIP4844-01",
      "related_assumption_id": null,
      "notes": "Derived from ambiguity in EIP-4844."
    }
  ]
}
```
