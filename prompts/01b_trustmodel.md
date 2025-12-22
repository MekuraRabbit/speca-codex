
---
Description: Build a formal trust model from the Program Graph specification. This involves assigning trust levels to actors and, critically, mapping trust boundaries to the specific EDGES of the program graph where data flows between actors of different trust levels.
Usage: `/01b_trustmodel`
Language: English only.
Execution hint: Run after `/01_spec`.
---
**Always use /serena for these development tasks to maximize token efficiency:**

# **Trust Model Generation Prompt**

**Goal**
Using the Program Graph from `01_SPEC.json`, create a formal trust model. This model must define the trust status of each actor and, most importantly, identify the specific **edges** in the graph that represent a **trust boundary crossing**.

**Output (required file):** `outputs/01b_TRUSTMODEL.json`

---

## 1) Inputs

1.  **System Specification (Authoritative):** `outputs/01_SPEC.json`
    *   Use `trusted_entities` to classify actors.
    *   Use `program_graph.nodes` and `program_graph.edges` to identify trust boundaries.

---

## 2) Trust Model Generation Logic

### **Task 2.1: Classify Actor Trust Levels (`actors`)**

*   For each entity from `01_SPEC.json`'s `trusted_entities`, create a corresponding actor object. Use the `id` from the spec as the actor's `id`. Then, assign a `trust_level` (`TRUSTED`, `UNTRUSTED`, `SEMI_TRUSTED`) and provide a `rationale`.

### **Task 2.2: Identify Trust Boundary Edges (`boundary_edges`)**

*   **CRITICAL:** A trust boundary is crossed on an **edge**, not a node.
*   **Logic:**
    1.  Iterate through every `edge` in `program_graph.edges`.
    2.  For each `edge`, look up the `id` of its source actor and its target actor.
    3.  Look up the `trust_level` of the source actor and the target actor.
    4.  If `trust_level(source_actor) != trust_level(target_actor)`, then this edge is a **trust boundary crossing**.
*   **Action:** For each such edge, create an object in the `boundary_edges` array.
    *   `edge_id`: The `id` of the edge from the program graph.
    *   `description`: A clear description of the boundary crossing event.
    *   `source_id`, `source_trust_level`
    *   `target_id`, `target_trust_level`
    *   `data_flows_across`: The `data_involved` from the edge, representing the data that is being passed from a less-trusted to a more-trusted domain (or vice-versa).
    *   `security_assumption`: State the core assumption that must hold true for this specific transition to be secure.

---

## 3) Required Output Format (JSON)

**File:** `outputs/01b_TRUSTMODEL.json`

```json
{
  "metadata": { /* ... */ },
  "actors": [
    {
      "id": "ACTOR-CL-CONSENSUS-CLIENT",
      "name": "Consensus Client (CL)",
      "trust_level": "SEMI_TRUSTED",
      "rationale": "Trusted to follow protocol, but is a separate software component."
    },
    {
      "id": "ACTOR-EL-EXECUTION-CLIENT",
      "name": "Execution Client (EL)",
      "trust_level": "TRUSTED",
      "rationale": "The system under audit."
    }
  ],
  "boundary_edges": [
    {
      "edge_id": "EDGE-CL-SENDS-REQUEST",
      "description": "The Engine API interface where the CL sends a request to the EL.",
      "source_id": "ACTOR-CL-CONSENSUS-CLIENT",
      "source_trust_level": "SEMI_TRUSTED",
      "target_id": "ACTOR-EL-EXECUTION-CLIENT",
      "target_trust_level": "TRUSTED",
      "data_flows_across": ["DATA-JWT-REQUEST"],
      "security_assumption": "The EL must not trust the content or validity of DATA-JWT-REQUEST until it has been fully authenticated and validated by the ACTION-EL-VALIDATE-JWT node. The integrity of this edge relies solely on the strength of the validation action that follows."
    }
    // ... other edges that cross trust boundaries
  ]
}
```
