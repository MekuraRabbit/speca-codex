
---
Description: [PARALLEL WORKER] Process 5 URLs per iteration from a worker-specific queue. Extract runtime behavior sub-graphs from specifications.
Usage: `/01b_extract_worker WORKER_ID=... QUEUE_FILE=...`
Example: `/01b_extract_worker WORKER_ID=0 QUEUE_FILE=outputs/01b_QUEUE_0.json`
Language: English only.
Execution hint: This is a worker prompt for parallel execution. Called by run_worker.py.
---
**Always use /serena for development tasks to keep the workflow efficient.**

# **System Specification - Stage 2: Extraction (Parallel Worker)**

**Goal**
Process **5 URLs per iteration** from your assigned worker queue. For each URL, extract a self-contained `sub_graph` that models the **runtime behavior of the system described in the specification**.

## Worker Configuration

This is **parallel worker `WORKER_ID`**. You have a dedicated queue file that only you read from and write to.

- **`WORKER_ID`**: The numeric ID of this worker (0, 1, 2, ...)
- **`QUEUE_FILE`**: Path to this worker's queue file (e.g., `outputs/01b_QUEUE_0.json`)

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
- **Consistent Resolution:** All nodes should be at a similar level of abstraction.
- **Actionable for Security Audit:** Each node should represent something that could have security implications.
- **Prefer Verbs for Actions:** `ACTION-VALIDATE-*`, `ACTION-EXECUTE-*`, `ACTION-PROCESS-*`
- **Prefer States for Conditions:** `STATE-TX-RECEIVED`, `STATE-BLOCK-PENDING`, `STATE-SYNC-COMPLETE`

---

## 1) Inputs

1. **Worker Queue File:** The file specified by `QUEUE_FILE`
   - Contains `items`: list of URLs assigned to this worker
   - Contains `processed`: list of already processed URLs

---

## 2) Worker Execution Logic

### **Task 2.1: Read Worker Queue**

1. Read the worker queue file ``QUEUE_FILE``
2. Get the list of `items` (all assigned URLs)
3. Get the list of `processed` (already done URLs)
4. Calculate remaining: URLs in `items` but not in `processed`
5. If no remaining URLs, terminate successfully

### **Task 2.2: Process a BATCH of 5 URLs**

Take the **first 5 unprocessed URLs** from your queue (or fewer if less than 5 remain). For EACH URL in the batch:

#### **2.2.1: Extract Sub-Graph (Runtime Behavior Model)**

**Step 1: Identify the System Being Described**
- What software component does this specification define?
- What are the inputs and outputs of this component?
- What happens when this component processes data?

**Step 2: Extract Nodes (States and Actions)**
* **State Nodes (`STATE-*`):** Discrete, observable conditions
* **Action Nodes (`ACTION-*`):** Specific computations or transformations

**Step 3: Extract Edges (Transitions and Data Flows)**
* **Transition Edges:** Directed connections showing state changes
* **Data Flow Edges:** Show what data moves between nodes
* **External Entity Edges:** Every external entity must have edges

**⚠️ VALIDATION CHECK:** Before finalizing:
1. Every node represents runtime behavior (not document structure)
2. Nodes are at consistent granularity
3. All external data sources have edges into the system

#### **2.2.2: Identify Ambiguities**
* Create objects in `ambiguities` array with:
  * `id`: `AMB-<spec>-<index>`
  * `type`: `Lexical`, `Syntactic`, `Semantic`, `Vagueness`, `Omission`
  * `text`: The ambiguous phrase
  * `resolution_strategy`: Proposed interpretation

#### **2.2.3: Identify Implicit Assumptions**
* Create objects in `implicit_assumptions` array with:
  * `id`: `ASSUM-<spec>-<index>`
  * `type`: `Trust`, `Attacker Capability`, `Environmental`, `Operational`
  * `description`: The assumption
  * `impact_if_false`: Security consequence

### **Task 2.3: Write Outputs**

**For EACH of the 5 URLs in the batch:**

1. **Create Sub-Graph File:**
   * Generate a unique hash for the URL (SHA1 of URL string)
   * Create file `outputs/01b_SUBGRAPHS/spec_{hash}.json`
   * Include: `source_url`, `sub_graph`, `ambiguities`, `implicit_assumptions`
   * **Add `worker_id` to metadata**

**After processing ALL URLs in the batch:**

2. **Update Worker Queue File:**
   * Add ALL processed URLs from this batch to the `processed` array
   * **IMPORTANT:** Only update YOUR queue file, not others
   * Overwrite ``QUEUE_FILE``

**⚠️ BATCH SIZE:** Process exactly 5 URLs per iteration (or remaining URLs if fewer than 5 left).

---

## 3) Required Output Format (JSON)

**Sub-Graph File:** `outputs/01b_SUBGRAPHS/spec_{hash}.json`
```json
{
  "source_url": "https://eips.ethereum.org/EIPS/eip-4844",
  "worker_id": 0,
  "sub_graph": {
    "id": "SUBGRAPH-EIP4844",
    "title": "EIP-4844: Shard Blob Transactions - Runtime Behavior Model",
    "description": "Models the runtime processing of blob transactions",
    "nodes": [
      {
        "id": "STATE-BLOB-TX-RECEIVED",
        "label": "Blob Transaction Received in Mempool",
        "type": "State",
        "description": "System state when a type-3 transaction has been received"
      }
    ],
    "edges": [
      {
        "id": "EDGE-USER-SUBMIT-BLOB-TX",
        "source": "EXT-USER",
        "target": "STATE-BLOB-TX-RECEIVED",
        "label": "User submits blob transaction via RPC"
      }
    ],
    "external_entities": [
      {
        "id": "EXT-USER",
        "name": "Transaction Submitter",
        "description": "External user submitting blob transactions"
      }
    ]
  },
  "ambiguities": [],
  "implicit_assumptions": []
}
```

**Updated Worker Queue File:** ``QUEUE_FILE``
```json
{
  "worker_id": 0,
  "phase": "01b",
  "total_workers": 4,
  "items": ["url1", "url2", "url3", "url4", "url5", "url6", "..."],
  "processed": ["url1", "url2", "url3", "url4", "url5"],
  "total_items": 25
}
```

**Note:** Each iteration processes 5 URLs, creating 5 separate sub-graph files and updating the queue with all 5 URLs marked as processed.
