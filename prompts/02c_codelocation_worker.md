---
Description: [WORKER] Pre-resolve code locations for checklist items
Usage: `/02c_worker WORKER_ID=... QUEUE_FILE=... [TIMESTAMP=...] [ITERATION=...] [BATCH_SIZE=...] [OUTPUT_FILE=...]`
Language: English only.
---

<task>
  <goal>For each checklist item in the batch, find the relevant code locations in the target repository and extract code excerpts.</goal>
  <input type="file" id="queue">{{QUEUE_FILE}}</input>
  <output type="file" id="results">{{OUTPUT_FILE}}</output>

  <critical_requirements>
    1. Process ALL items in the batch — do not skip or truncate
    2. Write output JSON even if some items fail resolution
    3. Handle errors per item gracefully and continue
  </critical_requirements>

  <instructions>
    ## Step 1: Setup

    Read `outputs/02c_TARGET_INFO.json` to get `target_repo` and detect target layer:

    - Consensus layer clients: prysm, lighthouse, teku, nimbus, lodestar
    - Execution layer clients: geth, go-ethereum, nethermind, besu, erigon, reth

    Register the cloned repository at `target_workspace/` with Tree-sitter MCP.

    ## Step 2: Layer Scope Check (per item)

    Extract the EIP number from the item's `notes` field and check layer:

    - Execution layer EIPs: 7623, 7691, 7702, 7823, 7825, 7883, 7917, 7920
    - Consensus layer EIPs: 7251, 7549, 7594, 7685, 7692, 7716, 7732, 7742, 7840, 7892

    If target layer and spec layer are both known and do **not** match → mark as `out_of_scope` and skip to next item.

    ## Step 3: Code Resolution (per in-scope item)

    **Primary — Tree-sitter MCP call graph:**
    Use Tree-sitter MCP to identify entry point functions matching `reachability.entry_points`, then traverse the call graph (depth ≤ 3) to find functions whose names or logic match keywords extracted from `test_procedure`. Extract file path, symbol name, and line range for the top matches.

    **Fallback — Glob + Grep:**
    If MCP fails or returns no results, use the standard Glob and Grep tools to search `target_workspace/` directly. Extract keywords (PascalCase, snake_case, ALL_CAPS, domain terms) from `test_procedure` and search for function/type definitions matching those keywords. Narrow the search path using the entry point category:

    | Entry point | Search path hint |
    |-------------|-----------------|
    | P2P | `**/p2p/**`, `**/sync/**` |
    | Transaction | `**/txpool/**`, `**/core/types/**` |
    | EngineAPI / Engine API | `**/engine/**`, `**/beacon/**` |
    | Consensus | `**/consensus/**`, `**/forkchoice/**` |
    | Internal / Internal API | `**/core/**`, `**/internal/**` |

    Read the matched file sections with the Read tool to extract code excerpts (max 50 lines per location).

    If both MCP and Grep find nothing → mark as `not_found`.

  </instructions>

  <output>
    <format>JSON object with "checklist_with_code" array</format>
    <schema>
      {
        "checklist_with_code": [
          {
            // ALL original fields from the input item must be preserved as-is

            "code_scope": {
              "locations": [           // empty list if out_of_scope or not_found
                {
                  "file": "relative/path/from/workspace/root.go",
                  "symbol": "FunctionOrTypeName",
                  "line_range": { "start": 42, "end": 78 },
                  "role": "primary" | "caller" | "callee" | "related"
                }
              ],
              "resolution_status": "resolved" | "out_of_scope" | "not_found" | "error",
              "resolution_error": "",   // empty string unless status is "error"
              "resolution_method": "mcp_callgraph" | "mcp_simple" | "grep_fallback"  // only when resolved
            },
            "code_excerpt": "// PRIMARY: path/to/file.go:FunctionName (lines 42-78)\n..."
          }
        ]
      }
    </schema>
    <stdout>Max 10 lines: processed count and per-status breakdown.</stdout>
    <final_line>Output File: {{OUTPUT_FILE}}</final_line>
  </output>
</task>
