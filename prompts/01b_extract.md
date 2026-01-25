
---
Description: Process one specification URL from the work queue in each run. Extract a self-contained sub-graph, identify ambiguities in the text, and list implicit assumptions. This iterative process breaks down specification analysis into manageable, fault-tolerant chunks.
Usage: `/01b_extract`
Language: English only.
Execution hint: Run after `/01a_crawl`. Run this multiple times until the work queue is empty.
---

# **System Specification - Stage 2: Extraction (Iterative)**

**Goal**
Process one specification URL from the `work_queue` in each run. For the given URL, extract a self-contained `sub_graph`, identify any `ambiguities` in the text, and list any `implicit_assumptions`. This iterative process breaks down the monumental task of specification analysis into manageable, fault-tolerant chunks.

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

For the selected URL, perform a deep analysis of the specification document.

#### **2.2.1: Extract Sub-Graph**
*   Identify the nodes (states, actions) and edges (transitions) described **only in this specific document**.
*   Model this as a `sub_graph` following the same schema as the main `program_graph`.
*   **Node Definition:** A node represents a discrete, observable state or a specific computational action within the system under audit.
*   **Edge Definition:** A directed edge represents a transition between two nodes, or a data flow from an external entity to an internal node.

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
    "title": "EIP-4844: Shard Blob Transactions",
    "nodes": [
      {
        "id": "STATE-BLOB-TX-RECEIVED",
        "label": "Blob Transaction Received",
        "type": "State"
      }
    ],
    "edges": [
      {
        "id": "EDGE-BLOB-TX-SUBMIT",
        "source": "EXT-USER",
        "target": "STATE-BLOB-TX-RECEIVED",
        "label": "User submits blob transaction"
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
