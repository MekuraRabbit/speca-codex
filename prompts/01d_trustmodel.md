
---
Description: Generate a formal trust model based on the System Specification. Assign trust levels to all External Entities and identify Trust Boundary Edges where data enters the System Under Audit.
Usage: `/01d_trustmodel`
Language: English only.
Execution hint: Run after `/01c_integrate`. This provides the trust context for property generation.
---

# **Trust Model Generation Prompt**

**Goal**
Using the System Specification from `01_SPEC.json`, create a formal trust model. This model must assign trust levels to all **External Entities** and identify the specific **edges** in the graph that represent a **Trust Boundary Crossing** (i.e., where data enters the System Under Audit).

**Output (required file):** `outputs/01d_TRUSTMODEL.json`

---

## 1) Inputs

1.  **System Specification (Authoritative):** `outputs/01_SPEC.json`

---

## 2) Trust Model Generation Logic

### **Mindset: The System Under Audit as the Frame of Reference**

The `system_under_audit` is the entity evaluating trust. It does **not** receive a trust level itself. Trust levels are assigned to the entities it interacts with—the `external_entities`. This is the foundational principle of threat modeling.

### **Task 2.1: Classify External Entity Trust Levels (`trusted_external_entities`)**

*   For each entity from `01_SPEC.json`'s `external_entities`, create a corresponding object.
*   Assign a `trust_level` and provide a `rationale` explaining why that level is appropriate from the perspective of the `system_under_audit`.

| Trust Level | Meaning |
|-------------|---------|
| `TRUSTED` | Data and commands from this entity can be accepted without validation. (Use sparingly.) |
| `SEMI_TRUSTED` | The entity is authenticated/known, but its inputs must still be validated. |
| `UNTRUSTED` | All input from this entity must be treated as potentially malicious. |

### **Task 2.2: Identify Trust Boundary Edges (`boundary_edges`)**

*   **Definition:** A trust boundary is crossed on an **edge** where data or control flows from an `external_entity` into the `system_under_audit`.
*   **Logic:**
    1.  Iterate through every `edge` in `program_graph.edges` (and all `sub_graphs`).
    2.  Look up the `source` ID of the edge.
    3.  If the `source` ID matches an ID in the `external_entities` array, then this edge is a **trust boundary crossing**.
*   **Action:** For each such edge, create an object in the `boundary_edges` array.
    *   `edge_id`: The `id` of the edge from the program graph.
    *   `description`: A clear description of the boundary crossing event.
    *   `source_entity_id`: The `id` of the external entity.
    *   `source_trust_level`: The trust level assigned to that entity.
    *   `target_node_id`: The `id` of the first internal node that receives the data.
    *   `data_flows_across`: The `data_involved` from the edge.
    *   `security_assumption`: State the core assumption that must hold for this specific transition to be secure. This almost always relates to **input validation**.

---

## 3) Required Output Format (JSON)

**File:** `outputs/01d_TRUSTMODEL.json`

```json
{
  "metadata": {
    "generated_at": "2025-01-16T15:00:00Z",
    "source_spec": "outputs/01_SPEC.json"
  },
  "trusted_external_entities": [
    {
      "id": "EXT-CL",
      "name": "Consensus Client (CL)",
      "trust_level": "SEMI_TRUSTED",
      "rationale": "The CL is an authenticated and known peer, but it is a separate software component whose inputs must still be validated. It is not fully trusted."
    },
    {
      "id": "EXT-USER",
      "name": "End User",
      "trust_level": "UNTRUSTED",
      "rationale": "Any user can submit arbitrary data. All input must be treated as potentially malicious."
    }
  ],
  "boundary_edges": [
    {
      "edge_id": "EDGE-CL-SENDS-FCU",
      "description": "The Engine API interface where the CL sends a forkChoiceUpdated call to the EL.",
      "source_entity_id": "EXT-CL",
      "source_trust_level": "SEMI_TRUSTED",
      "target_node_id": "STATE-EL-AWAITING-REQUEST",
      "data_flows_across": ["DATA-FORKCHOICE-UPDATE"],
      "security_assumption": "The EL must validate the format, signature, and content of the forkChoiceUpdated payload before processing it. The integrity of the system depends on rigorous validation at this boundary."
    }
  ]
}
```
