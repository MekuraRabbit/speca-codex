
---
Description: Generate a formal trust model based on the System Specification. Assign trust levels to all External Entities and identify Trust Boundary Edges where data enters the System Under Audit.
Usage: `/01d_trustmodel`
Language: English only.
Execution hint: Run after `/01c_integrate`. This provides the trust context for property generation.
---
**Always use /serena for development tasks to keep the workflow efficient.**

# **Trust Model Generation Prompt**

**Goal**
Using the System Specification from `01_SPEC.json`, create a formal trust model. This model must assign trust levels to all **External Entities** and identify the specific **edges** in the graph that represent a **Trust Boundary Crossing** (i.e., where data enters the System Under Audit).

**Output (required file):** `outputs/01d_TRUSTMODEL.json`

---

## 1) Inputs

1.  **System Specification (Authoritative):** `outputs/01_SPEC.json`

---

## 2) Trust Model Generation Logic

### **Mindset: Zero Trust Principle**

Adopt a **zero-trust security posture**. The `system_under_audit` is the entity evaluating trust. By default, assume all external entities are potentially hostile until proven otherwise. Trust levels are assigned conservatively based on cryptographic guarantees, authentication mechanisms, and operational controls.

### **Task 2.0: Validate External Entities (Pre-check)**

Before assigning trust levels, verify that each entity in `external_entities` is truly external:

**External Entity Criteria:**
- ✅ Resides outside the system boundary (separate process, network, or administrative domain)
- ✅ Sends data INTO the system under audit
- ✅ Not under the direct control of the system under audit

**Internal Component Indicators (Should NOT be in external_entities):**
- ❌ Described as "internal component" or "internal module"
- ❌ Runs within the same process/runtime as the system under audit
- ❌ Is a scheduler, manager, or controller that exists purely within the system

**If you find misclassified internal components in `external_entities`, note them in a `misclassified_entities` array and exclude them from trust analysis.**

### **Task 2.1: Classify External Entity Trust Levels (`trusted_external_entities`)**

*   For each **validated** external entity from `01_SPEC.json`'s `external_entities`, create a corresponding object.
*   Assign a `trust_level` and provide a `rationale` explaining why that level is appropriate.

| Trust Level | Meaning | When to Use |
|-------------|---------|-------------|
| `TRUSTED` | Data can be accepted with minimal validation. | **ONLY** for components with cryptographic attestation AND under the same administrative control. Example: A co-located HSM with verified firmware. **Almost never appropriate.** |
| `SEMI_TRUSTED` | Authenticated entity, but inputs MUST be validated. | Authenticated peers (e.g., JWT-authenticated API, TLS-verified peer). The authentication provides identity, NOT data integrity guarantees. |
| `UNTRUSTED` | All input is potentially malicious. Full validation required. | Default level. Network peers, user input, external APIs, any unauthenticated source. |

### ⚠️ Trust Level Guidelines (Zero Trust)

1. **Default to UNTRUSTED:** When in doubt, mark as `UNTRUSTED`.
2. **Authentication ≠ Trust:** An authenticated entity (e.g., Consensus Layer with JWT) is `SEMI_TRUSTED` at best. Authentication proves identity, not that the data is safe.
3. **Runtime Environments:** Language runtimes, OS, hardware are **out of scope** for this model. Do not list them as external entities. Security audits assume the execution environment is correct (this is a separate concern).
4. **Never TRUSTED for Network Peers:** Any entity communicating over a network (even authenticated) should be at most `SEMI_TRUSTED`.
5. **Consider Compromise Scenarios:** If this entity were compromised, what's the blast radius? High blast radius = lower trust level.

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

### **Task 2.3: MANDATORY Completeness Verification ⚠️**

This step is **CRITICAL**. The trust model is incomplete and invalid if boundary edges are missing.

**Verification Algorithm:**
```
FOR each entity E in trusted_external_entities:
    count = COUNT(boundary_edges WHERE source_entity_id == E.id)
    IF count == 0:
        ERROR: "External entity {E.id} has no boundary edges defined!"
        ACTION: Either (a) find missing edges in the graph, or (b) flag as coverage_gap
```

**Output `coverage_analysis`:** Include a coverage analysis object:
```json
{
  "coverage_analysis": {
    "total_external_entities": 5,
    "entities_with_boundary_edges": 5,
    "coverage_gaps": [],
    "verification_status": "COMPLETE"
  }
}
```

**If gaps exist:**
```json
{
  "coverage_analysis": {
    "total_external_entities": 5,
    "entities_with_boundary_edges": 3,
    "coverage_gaps": [
      {
        "entity_id": "EXT-NETWORK",
        "reason": "No edges from EXT-NETWORK found in program_graph. The specification may be incomplete or the graph extraction missed network entry points."
      }
    ],
    "verification_status": "INCOMPLETE - 2 entities have no boundary edges"
  }
}
```

**Why This Matters:** If an external entity exists but has no boundary edge, either:
1. The graph is incomplete (extraction error) - this should be fixed in `01b_extract`
2. The entity shouldn't be external (classification error) - move to `misclassified_entities`
3. The entity truly has no direct data flow (rare) - document why in `coverage_gaps`

---

## 3) Required Output Format (JSON)

**File:** `outputs/01d_TRUSTMODEL.json`

```json
{
  "metadata": {
    "generated_at": "2025-01-16T15:00:00Z",
    "source_spec": "outputs/01_SPEC.json"
  },
  "misclassified_entities": [
    {
      "id": "EXT-FORK-SCHEDULER",
      "original_description": "Internal component that schedules hard forks",
      "reason": "Described as 'internal component'. This is not an external entity but an internal scheduler module. It should be modeled as an internal node, not an external entity.",
      "recommendation": "Remove from external_entities in 01_SPEC.json and model as internal ACTION or STATE node."
    }
  ],
  "trusted_external_entities": [
    {
      "id": "EXT-CL",
      "name": "Consensus Client (CL)",
      "trust_level": "SEMI_TRUSTED",
      "rationale": "The CL communicates via Engine API with JWT authentication. Authentication provides identity verification but NOT data integrity. The CL is a separate process that could be compromised independently. All payloads must be validated."
    },
    {
      "id": "EXT-USER",
      "name": "End User / Transaction Submitter",
      "trust_level": "UNTRUSTED",
      "rationale": "Any user can submit arbitrary data via JSON-RPC. No authentication required for transaction submission. All input must be treated as potentially malicious."
    },
    {
      "id": "EXT-NETWORK",
      "name": "P2P Network Peers",
      "trust_level": "UNTRUSTED",
      "rationale": "Network peers are unauthenticated and potentially adversarial. Malicious nodes may send crafted messages to exploit vulnerabilities. All network input requires full validation."
    }
  ],
  "boundary_edges": [
    {
      "edge_id": "EDGE-CL-SENDS-FCU",
      "description": "Engine API endpoint receiving forkchoiceUpdated from Consensus Layer",
      "source_entity_id": "EXT-CL",
      "source_trust_level": "SEMI_TRUSTED",
      "target_node_id": "STATE-ENGINE-API-REQUEST-RECEIVED",
      "data_flows_across": ["DATA-FORKCHOICE-STATE", "DATA-PAYLOAD-ATTRIBUTES"],
      "security_assumption": "The EL must validate: (1) JWT token authenticity, (2) payload schema conformance, (3) referenced block hashes exist, (4) state root validity. Failure to validate enables consensus manipulation attacks."
    },
    {
      "edge_id": "EDGE-USER-SUBMIT-TX",
      "description": "JSON-RPC endpoint receiving transaction from user",
      "source_entity_id": "EXT-USER",
      "source_trust_level": "UNTRUSTED",
      "target_node_id": "STATE-TX-RECEIVED",
      "data_flows_across": ["DATA-SIGNED-TX"],
      "security_assumption": "Full transaction validation required: signature verification, nonce check, gas limit validation, balance check, intrinsic gas calculation. Invalid transactions must be rejected before entering mempool."
    },
    {
      "edge_id": "EDGE-NETWORK-RECEIVE-BLOCK",
      "description": "P2P network receiving block announcement/body from peers",
      "source_entity_id": "EXT-NETWORK",
      "source_trust_level": "UNTRUSTED",
      "target_node_id": "STATE-BLOCK-RECEIVED",
      "data_flows_across": ["DATA-BLOCK-HEADER", "DATA-BLOCK-BODY"],
      "security_assumption": "Block must be fully validated: PoW/PoS verification, transaction root, state root, uncle validation. Malformed blocks must be rejected and peer penalized."
    }
  ],
  "coverage_analysis": {
    "total_external_entities": 3,
    "entities_with_boundary_edges": 3,
    "coverage_gaps": [],
    "verification_status": "COMPLETE"
  }
}
```
