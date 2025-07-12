**Task: Build `WHITEHAT_01b_AUDITMAP_ORDER.json`**

You are a senior white-hat auditor.
Follow the instructions below exactly and save the resulting JSON file to
`security-agent/outputs/WHITEHAT_01b_AUDITMAP_ORDER.json`.
Respond with *nothing* in the chat—write only to the file.

---

### 1. Load the inputs

* `security-agent/outputs/WHITEHAT_01_SPEC.json` – project specs, user-flows, requirements.
* `security-agent/outputs/callgraphs/*.dot` – Graphviz call-graphs for each contract.

---

### 2. Build an exploration order

1. **Extract user-flows**
   Read every `user_flows[]` entry. Note its ID, description, and “criticality”.
2. **Locate entry functions**
   For each user-flow, identify the first external/public function(s) that start the flow.
3. **Expand call-graphs**
   Using the corresponding `.dot` file, breadth-first search outward (depth ≤ 3) from each entry function. Record every reachable function once.
4. **Group into “chunks”**

   * One chunk per user-flow (name it e.g. `UF-Deposit`).
   * Any function reached by multiple flows goes in an extra chunk called `Shared-Logic`.
5. **Annotate each chunk**
   For every chunk include:

   * `chunk_name` – the ID (`UF-…` or `Shared-…`).
   * `description` – one-sentence summary in Japanese.
   * `data_lifecycle` – how assets / state change (“ETH 入金 → share 発行 → buffer 更新”).
   * `call_sequence` – ordered list of functions from entry to deepest sink.
   * `permissions` – `anyone`, `role`, or `owner` (use modifier data from `00_AST.json`).
   * `criticality` – `High`, `Medium`, `Low` (based on TVL and user impact).
   * `done_index` – always `0` (used later for progress tracking).

---

### 3. Apply the white-hat mental model

Before finalising, run two internal reflection passes:

* **Pass A — Completeness check**
  Ask yourself: “Did I miss any user-flow or shared sink?” If yes, add them.
* **Pass B — Attacker priority re-ordering**
  Re-sort chunks so the most profitable or lowest-friction attack paths appear first.

Repeat passes until satisfied.

---

### 4. Write the file

Create a single JSON object with a top-level key `function_chunks` containing the ordered list.
Pretty-print with an indentation of two spaces.
Save to `security-agent/outputs/WHITEHAT_01b_AUDITMAP_ORDER.json`.

---

### 5. Final rule

Write **only** to the file; output nothing else.
