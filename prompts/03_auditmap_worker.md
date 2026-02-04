
---
Description: [WORKER] Invoke the formal-audit skill for a batch of items.
Usage: `/03_auditmap_worker WORKER_ID=... QUEUE_FILE=... [TIMESTAMP=...] [ITERATION=...] [BATCH_SIZE=...] [OUTPUT_FILE=...]`
Example: `/03_auditmap_worker WORKER_ID=0 QUEUE_FILE=outputs/03_QUEUE_0.json TIMESTAMP=1700000000 ITERATION=1 BATCH_SIZE=5 OUTPUT_FILE=outputs/03_AUDITMAP_PARTIAL_W0_1700000000_1.json`
Language: English only.
Execution hint: This worker prompt is invoked by the phase-03 async orchestrator.
---
**Use Serena MCP tools (find_symbol, insert_after_symbol, etc.) for efficient code navigation and editing.**

<task>
  <goal>Run a three-stage formal audit for each item in the batch using skills.</goal>
  <input type=\"file\" id=\"queue\">{{QUEUE_FILE}}</input>
  <output type=\"file\" id=\"results\">{{OUTPUT_FILE}}</output>
  <instructions>
    1. Read <ref id=\"queue\"/> and select the first BATCH_SIZE unprocessed items.
    2. For each item, ensure a code excerpt is available:
       - If item.code_excerpt is present, use it.
       - Otherwise use Tree-sitter MCP tools (get_symbols/get_node_at_position/get_ast) to extract the function or line-range excerpt.
    3. For each item, run these skills in order:
       a) /formal-audit-phase1 (include code_excerpt)
       b) /formal-audit-phase2 (include phase1 output)
       c) /formal-audit-phase3 (include phase1+phase2 outputs)
    4. Merge outputs into a single audit result object per item with:
       - check_id, property_id, code_scope, final_classification, bug_bounty_eligible, summary
       - audit_trail containing phase1/phase2/phase2.5/phase3/phase3.5 outputs
    5. Write a JSON array of audit result objects to <ref id=\"results\"/>.
  </instructions>
</task>

<output>
  <format>JSON array</format>
  <stdout>Max 8 lines: batch size, items processed, short status.</stdout>
</output>
