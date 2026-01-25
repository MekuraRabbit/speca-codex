
---
Description: Integrate all individually extracted sub-graph files into a single, cohesive, and complete system specification. This final stage consolidates all distributed knowledge into the authoritative 01_SPEC.json file.
Usage: `/01c_integrate`
Language: English only.
Execution hint: Run after `/01b_extract` has completed (i.e., the work queue is empty). This produces the final specification.
---

# **System Specification - Stage 3: Integration**

**Goal**
Integrate all the individually extracted `sub_graph` files into a single, cohesive, and complete system specification. This final stage consolidates all the distributed knowledge into the authoritative `01_SPEC.json` file.

**Output (required file):** `outputs/01_SPEC.json`

---

## 1) Inputs

1.  **All Sub-Graph Files:** The entire contents of the `outputs/01b_SUBGRAPHS/` directory.

---

## 2) Integration Logic

### **Task 2.1: Consolidate Graphs**

1.  Initialize a new, empty `program_graph` with `nodes` and `edges` arrays.
2.  Iterate through every `spec_*.json` file in the `01b_SUBGRAPHS` directory.
3.  For each file:
    a.  **Merge Nodes:** Add all nodes from the `sub_graph.nodes` array to the main `program_graph.nodes` array. You **MUST** handle ID conflicts. If two different specs define a node with the same ID, they should be merged if they are semantically identical, or one should be renamed if they are different. Add a note about the merge in the node's description.
    b.  **Merge Edges:** Add all edges from the `sub_graph.edges` array to the main `program_graph.edges` array. Ensure `source` and `target` IDs are consistent with the final, merged node list.

### **Task 2.2: Consolidate Ambiguities and Assumptions**

1.  Initialize empty `ambiguities` and `implicit_assumptions` arrays.
2.  Iterate through every `spec_*.json` file.
3.  Append all items from the file's `ambiguities` and `implicit_assumptions` arrays into the main arrays.
4.  Add the `source_url` to each item for traceability.

### **Task 2.3: Define System Boundaries**

1.  Based on the complete graph, define the `system_under_audit` object. This is the core system being analyzed.
2.  Identify all `external_entities` that interact with the system. These are the sources of input and sinks of output.

### **Task 2.4: Finalize the Specification**

1.  Assemble the final `01_SPEC.json` file, including:
    *   `metadata`
    *   `system_under_audit`
    *   `external_entities`
    *   `ambiguities`
    *   `implicit_assumptions`
    *   `program_graph`

---

## 3) Required Output Format (JSON)

**File:** `outputs/01_SPEC.json`

```json
{
  "metadata": {
    "generated_at": "2025-01-16T14:00:00Z",
    "source_specs_count": 152,
    "total_nodes": 261,
    "total_edges": 294
  },
  "system_under_audit": {
    "id": "SYSTEM-EL-CLIENT",
    "name": "Execution Client (EL)",
    "internal_components": [
      { "id": "COMP-ENGINE-API", "name": "Engine API Handler" },
      { "id": "COMP-EVM", "name": "EVM Interpreter" }
    ]
  },
  "external_entities": [
    { "id": "EXT-CL", "name": "Consensus Client", "description": "..." },
    { "id": "EXT-USER", "name": "End User", "description": "..." }
  ],
  "ambiguities": [
    {
      "id": "AMB-EIP4844-01",
      "source_url": "https://eips.ethereum.org/EIPS/eip-4844",
      "type": "Semantic",
      "text": "The term 'valid blob' is used without a precise definition.",
      "resolution_strategy": "..."
    }
  ],
  "implicit_assumptions": [
    {
      "id": "ASSUM-EIP4844-01",
      "source_url": "https://eips.ethereum.org/EIPS/eip-4844",
      "type": "Attacker Capability",
      "description": "...",
      "impact_if_false": "..."
    }
  ],
  "program_graph": {
    "id": "GRAPH-EL-INTEGRATED",
    "title": "Integrated Execution Layer Behavior Model",
    "nodes": [ /* All nodes from all sub-graphs, de-duplicated */ ],
    "edges": [ /* All edges from all sub-graphs */ ]
  },
  "sub_graphs": []
}
```
