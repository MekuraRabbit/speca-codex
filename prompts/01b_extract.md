
---
Description: Process one specification URL from the work queue in each run. Extract a sub-graph representing the RUNTIME BEHAVIOR of the system described in the specification, identify ambiguities, and list implicit assumptions.
Usage: `/01b_extract`
Language: English only.
Execution hint: Run after `/01a_crawl`. Run this multiple times until the work queue is empty.
---
**Always use /serena for development tasks to keep the workflow efficient.**

# **System Specification - Stage 2: Extraction (Iterative)**

**Goal**
Process one specification URL from the `work_queue` in each run. For the given URL, extract a self-contained `sub_graph` that models the **runtime behavior of the system described in the specification**, identify any `ambiguities` in the text, and list any `implicit_assumptions`.

## ⚠️ CRITICAL: Model Runtime Behavior, NOT Document Structure

**You are NOT modeling the specification document itself. You ARE modeling the system that the document describes.**

The specification is a **source of information** about a running system. Your task is to read the specification and extract a model of how the **actual system behaves at runtime**.

### Mental Model Check (Ask Yourself These Questions)
Before extracting nodes and edges, answer these questions:
1. **What are the key states the system can be in?** (e.g., "Transaction Pool Full", "Block Validated", "Syncing")
2. **What actions/computations change the system state?** (e.g., "Validate Signature", "Execute Transaction", "Apply State Transition")
3. **What data flows into the system from external sources?** (e.g., user transactions, peer messages, RPC calls)
4. **What are the trust boundaries where external data enters?** (e.g., network interface, RPC endpoint)

### ✅ CORRECT Node Examples (Runtime Behavior)
| Node ID | Label | Why It's Correct |
|---------|-------|------------------|
| `STATE-TX-PENDING` | Transaction Pending in Mempool | Describes an actual system state |
| `ACTION-VALIDATE-SIGNATURE` | Validate Transaction Signature | Describes a computation the system performs |
| `STATE-BLOCK-VALIDATED` | Block Passed All Validation | Describes a system state after processing |
| `ACTION-APPLY-STATE-TRANSITION` | Apply State Transition Function | Describes core EVM execution logic |

### ❌ INCORRECT Node Examples (Document Structure - DO NOT USE)
| Node ID | Label | Why It's Wrong |
|---------|-------|----------------|
| `STATE-SPEC-ENTRY` | Specification Entry Point | Models the document, not the system |
| `ACTION-NAVIGATE-SECTION` | Navigate to Section | Models reading the doc, not system behavior |
| `MODULE-ETHEREUM` | Ethereum Module | Too abstract, not a runtime state or action |
| `ACTION-CLICK-LINK` | Click Documentation Link | Models user interaction with docs |

### Granularity Guidelines
- **Consistent Resolution:** All nodes should be at a similar level of abstraction. Don't mix `MODULE-ETHEREUM` (very abstract) with `CONST-GAS-LIMIT` (very concrete).
- **Actionable for Security Audit:** Each node should represent something that could have security implications (a state that could be corrupted, an action that could be exploited).
- **Prefer Verbs for Actions:** `ACTION-VALIDATE-*`, `ACTION-EXECUTE-*`, `ACTION-PROCESS-*`
- **Prefer States for Conditions:** `STATE-TX-RECEIVED`, `STATE-BLOCK-PENDING`, `STATE-SYNC-COMPLETE`

**Output (required files):**
1.  `outputs/01b_SUBGRAPHS/spec_<hash>.json`: A detailed extraction from the processed URL.
2.  `outputs/01a_STATE.json`: The updated state file.

---

## 1) Inputs

1.  **State File (Authoritative):** `outputs/01a_STATE.json`

---

## 2) Iterative Extraction Logic

### **Task 2.1: Select URL and Read State**

1.  Read the `outputs/01a_STATE.json` file.
2.  If `work_queue` is empty, terminate successfully. The extraction stage is complete.
3.  Take the **first URL** from the `work_queue`. This is your target for this run.

### **Task 2.2: Analyze and Extract from Target URL**

For the selected URL, perform a deep analysis of the specification document **to understand the runtime system it describes**.

#### **2.2.1: Extract Sub-Graph (Runtime Behavior Model)**

**Step 1: Identify the System Being Described**
- What software component does this specification define? (e.g., EVM, transaction pool, state transition function)
- What are the inputs to this component? What are the outputs?
- What happens when this component processes data?

**Step 2: Extract Nodes (States and Actions)**
*   **State Nodes (`STATE-*`):** Discrete, observable conditions the system can be in.
    - Ask: "What state is the system in before/after this operation?"
    - Example: After a transaction is received, the system is in `STATE-TX-PENDING`.
*   **Action Nodes (`ACTION-*`):** Specific computations or transformations the system performs.
    - Ask: "What does the system DO when processing this input?"
    - Example: The EVM performs `ACTION-EXECUTE-OPCODE` for each instruction.

**Step 3: Extract Edges (Transitions and Data Flows)**
*   **Transition Edges:** Directed connections showing how states change via actions.
*   **Data Flow Edges:** Show what data moves between nodes, especially across trust boundaries.
*   **External Entity Edges:** Every external entity that sends data INTO the system MUST have an edge to an internal node.

**⚠️ VALIDATION CHECK:** Before finalizing, verify:
1. Every node represents runtime behavior (not document structure)
2. Nodes are at consistent granularity
3. All external data sources have edges into the system

#### **2.2.2: Identify Ambiguities**
*   Carefully read the text and identify any statements that are unclear, imprecise, or open to multiple interpretations.
*   For each, create an object in the `ambiguities` array:
    *   `id`: `AMB-<spec>-<index>` (e.g., `AMB-EIP4844-01`).
    *   `type`: One of `Lexical`, `Syntactic`, `Semantic`, `Vagueness`, `Omission`.
    *   `text`: The ambiguous phrase or sentence from the spec.
    *   `resolution_strategy`: Propose a concrete interpretation to use for the model, and state that it's an assumption.

#### **2.2.3: Identify Implicit Assumptions**
*   Identify any conditions or contexts that the specification assumes but does not explicitly state.
*   For each, create an object in the `implicit_assumptions` array:
    *   `id`: `ASSUM-<spec>-<index>`.
    *   `type`: One of `Trust`, `Attacker Capability`, `Environmental`, `Operational`.
    *   `description`: The assumption being made.
    *   `impact_if_false`: The potential security consequence if the assumption does not hold.

### **Task 2.3: Write Outputs**

1.  **Create Sub-Graph File:**
    *   Generate a unique hash for the URL (e.g., SHA1 of the URL string).
    *   Create a file `outputs/01b_SUBGRAPHS/spec_<hash>.json`.
    *   This file contains the `source_url`, the extracted `sub_graph`, `ambiguities`, and `implicit_assumptions`.
2.  **Update State File:**
    *   Remove the processed URL from `work_queue`.
    *   Add the processed URL to `processed_urls`.
    *   Overwrite `outputs/01a_STATE.json` with the updated state.

---

## 3) Required Output Format (JSON)

**Sub-Graph File:** `outputs/01b_SUBGRAPHS/spec_a1b2c3d4.json`
```json
{
  "source_url": "https://eips.ethereum.org/EIPS/eip-4844",
  "sub_graph": {
    "id": "SUBGRAPH-EIP4844",
    "title": "EIP-4844: Shard Blob Transactions - Runtime Behavior Model",
    "description": "Models the runtime processing of blob transactions in the execution layer",
    "nodes": [
      {
        "id": "STATE-BLOB-TX-RECEIVED",
        "label": "Blob Transaction Received in Mempool",
        "type": "State",
        "description": "System state when a type-3 (blob) transaction has been received but not yet validated"
      },
      {
        "id": "ACTION-VALIDATE-BLOB-COMMITMENT",
        "label": "Validate KZG Blob Commitment",
        "type": "Action",
        "description": "Cryptographic verification that blob data matches the KZG commitment in the transaction"
      },
      {
        "id": "STATE-BLOB-TX-VALIDATED",
        "label": "Blob Transaction Validated",
        "type": "State",
        "description": "System state after blob transaction passes all validation checks"
      },
      {
        "id": "ACTION-COMPUTE-BLOB-GAS",
        "label": "Compute Blob Gas Price",
        "type": "Action",
        "description": "Calculate the blob gas price using the excess_blob_gas from the parent header"
      }
    ],
    "edges": [
      {
        "id": "EDGE-USER-SUBMIT-BLOB-TX",
        "source": "EXT-USER",
        "target": "STATE-BLOB-TX-RECEIVED",
        "label": "User submits blob transaction via RPC",
        "data_involved": ["DATA-BLOB-TX", "DATA-BLOB-SIDECAR"]
      },
      {
        "id": "EDGE-VALIDATE-BLOB",
        "source": "STATE-BLOB-TX-RECEIVED",
        "target": "ACTION-VALIDATE-BLOB-COMMITMENT",
        "label": "Initiate blob validation"
      },
      {
        "id": "EDGE-BLOB-VALID",
        "source": "ACTION-VALIDATE-BLOB-COMMITMENT",
        "target": "STATE-BLOB-TX-VALIDATED",
        "label": "Blob commitment verified successfully"
      }
    ],
    "external_entities": [
      {
        "id": "EXT-USER",
        "name": "Transaction Submitter",
        "description": "External user or application submitting blob transactions via JSON-RPC"
      }
    ]
  },
  "ambiguities": [
    {
      "id": "AMB-EIP4844-01",
      "type": "Semantic",
      "text": "The term 'valid blob' is used without a precise definition.",
      "resolution_strategy": "Assume 'valid' implies cryptographic, format, and network rule correctness. This needs verification."
    }
  ],
  "implicit_assumptions": [
    {
      "id": "ASSUM-EIP4844-01",
      "type": "Attacker Capability",
      "description": "An attacker cannot create a valid blob transaction without paying gas fees.",
      "impact_if_false": "Potential for DoS attacks via free blob submission."
    }
  ]
}
```

**Updated State File:** `outputs/01a_STATE.json`
```json
{
  "metadata": { /* ... */ },
  "work_queue": [ /* remaining URLs */ ],
  "processed_urls": [ "https://eips.ethereum.org/EIPS/eip-4844" ]
}
```
