---
Description: [WORKER] Pre-resolve code locations using multi-tier fallback strategy (MCP → Glob/Grep)
Usage: `/02c_worker WORKER_ID=... QUEUE_FILE=... [TIMESTAMP=...] [ITERATION=...] [BATCH_SIZE=...] [OUTPUT_FILE=...]`
Language: English only.
Execution hint: Prioritizes MCP Tree-sitter, falls back to filesystem-based search on failure.
---

<task>
  <goal>For each checklist item: 1) Check layer scope, 2) Use multi-tier fallback to find code locations, 3) Extract code excerpts.</goal>
  <input type="file" id="queue">{{QUEUE_FILE}}</input>
  <output type="file" id="results">{{OUTPUT_FILE}}</output>

  <critical_requirements>
    1. Process ALL items in the batch
    2. Use multi-tier fallback: MCP Tree-sitter → Glob/Grep → Fuzzy matching
    3. Mark layer-mismatched items as "out_of_scope" (skip analysis)
    4. Write JSON file to <ref id="results"/> after processing ALL items
    5. File MUST be written even if some items fail resolution
    6. Handle errors gracefully - continue processing even if individual items fail
  </critical_requirements>

  <instructions>
    ## Phase 0: Setup & Layer Validation

    1. **Read Input**:
       ```python
       import json
       with open(QUEUE_FILE) as f:
           data = json.load(f)

       items = data.get('checklist', [])[:BATCH_SIZE]
       results = []
       ```

    2. **Detect Target Layer**:
       ```python
       import json

       # Read target info
       with open('outputs/02c_TARGET_INFO.json') as f:
           target_info = json.load(f)

       target_repo = target_info['target_repo']

       def detect_target_layer(repo_name: str) -> str:
           """Detect if target is consensus or execution layer."""
           repo_lower = repo_name.lower()

           # Consensus layer clients
           if any(x in repo_lower for x in ['prysm', 'lighthouse', 'teku', 'nimbus', 'lodestar']):
               return 'consensus'

           # Execution layer clients
           if any(x in repo_lower for x in ['geth', 'go-ethereum', 'nethermind', 'besu', 'erigon', 'reth']):
               return 'execution'

           return 'unknown'

       TARGET_LAYER = detect_target_layer(target_repo)
       print(f"Target layer detected: {TARGET_LAYER}")
       ```

    3. **Check Layer Scope for Each Item**:
       ```python
       import re

       # Known layer mappings for common EIPs
       EXECUTION_LAYER_EIPS = {7823, 7825, 7883, 7917, 7920, 7623, 7691, 7702}
       CONSENSUS_LAYER_EIPS = {7594, 7692, 7742, 7840, 7892, 7716, 7732, 7549, 7685, 7251}

       def extract_spec_layer_from_notes(notes: str) -> str:
           """Extract EIP number and infer layer."""
           match = re.search(r'EIP-(\d+)', notes, re.IGNORECASE)
           if match:
               eip_num = int(match.group(1))
               if eip_num in EXECUTION_LAYER_EIPS:
                   return 'execution'
               if eip_num in CONSENSUS_LAYER_EIPS:
                   return 'consensus'
           return 'unknown'

       for item in items:
           spec_layer = extract_spec_layer_from_notes(item.get('notes', ''))

           # Check for out-of-scope (layer mismatch)
           if TARGET_LAYER != 'unknown' and spec_layer != 'unknown':
               if TARGET_LAYER != spec_layer:
                   # Mark as out_of_scope and skip analysis
                   item['code_scope'] = {
                       'locations': [],
                       'resolution_status': 'out_of_scope',
                       'resolution_error': f'Spec layer ({spec_layer}) does not match target layer ({TARGET_LAYER}). Skipped per audit scope.'
                   }
                   item['code_excerpt'] = ''
                   results.append(item)
                   continue  # Skip to next item

           # If in scope, proceed with multi-tier analysis
           # ... (see Phase 1-3 below)
       ```

    ## Phase 1: Multi-Tier Fallback Strategy

    For items that are in-scope, use a multi-tier fallback approach:

    **Tier 1: MCP Tree-sitter (Preferred)**
    - Full call graph analysis
    - Highest accuracy, but may fail

    **Tier 2: MCP Simple Symbol Search**
    - Direct symbol lookup without call graph
    - Faster, more reliable

    **Tier 3: Glob + Grep Filesystem Search (Fallback)**
    - Pure filesystem-based search
    - Always works, good accuracy with smart keywords

    **Tier 4: Fuzzy Matching**
    - Last resort for complex cases

    ### Implementation:

    ```python
    def resolve_code_location_multi_tier(item: dict) -> dict:
        """
        Multi-tier fallback for code location resolution.

        Returns:
            Item with code_scope and code_excerpt populated
        """
        test_procedure = item.get('test_procedure', '')
        keywords = extract_keywords(test_procedure)

        # Try Tier 1: MCP Tree-sitter call graph
        try:
            result = try_mcp_call_graph(item, keywords)
            if result['code_scope']['resolution_status'] == 'resolved':
                return result
        except Exception as e:
            print(f"Tier 1 (MCP call graph) failed: {e}")

        # Try Tier 2: MCP simple symbol search
        try:
            result = try_mcp_simple_search(item, keywords)
            if result['code_scope']['resolution_status'] == 'resolved':
                return result
        except Exception as e:
            print(f"Tier 2 (MCP simple) failed: {e}")

        # Try Tier 3: Glob + Grep filesystem search
        try:
            result = try_glob_grep_search(item, keywords)
            if result['code_scope']['resolution_status'] == 'resolved':
                return result
        except Exception as e:
            print(f"Tier 3 (Glob+Grep) failed: {e}")

        # Tier 4: Fuzzy matching (last resort)
        try:
            result = try_fuzzy_matching(item, keywords)
            if result['code_scope']['resolution_status'] == 'resolved':
                return result
        except Exception as e:
            print(f"Tier 4 (Fuzzy) failed: {e}")

        # All tiers failed
        item['code_scope'] = {
            'locations': [],
            'resolution_status': 'not_found',
            'resolution_error': 'All resolution tiers failed to locate code'
        }
        item['code_excerpt'] = ''
        return item
    ```

    ## Phase 2: Enhanced Keyword Extraction

    **Improved keyword extraction for better filesystem search:**

    ```python
    import re
    from typing import List

    def extract_keywords(test_procedure: str) -> List[str]:
        """
        Extract high-quality keywords from test procedure.
        Optimized for both MCP and filesystem search.
        """
        keywords = set()

        # 1. ALL_CAPS constants (highest priority)
        # Example: MAX_RLP_BLOCK_SIZE, GOSSIP_MAX_SIZE
        all_caps = re.findall(r'\b[A-Z][A-Z0-9_]{2,}\b', test_procedure)
        keywords.update(all_caps)

        # 2. PascalCase identifiers (Go exported functions/types)
        # Example: ProcessBlock, ValidateAttestation
        pascal_case = re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b', test_procedure)
        keywords.update(pascal_case)

        # 3. snake_case identifiers
        # Example: state_transition, apply_withdrawals
        snake_case = re.findall(r'\b[a-z][a-z0-9]*(?:_[a-z0-9]+){2,}\b', test_procedure)
        keywords.update(snake_case)

        # 4. camelCase identifiers
        # Example: validateBlock, processTransaction
        camel_case = re.findall(r'\b[a-z][a-z0-9]*[A-Z][a-zA-Z0-9]*\b', test_procedure)
        keywords.update(camel_case)

        # 5. Technical domain terms (blockchain/crypto specific)
        domain_terms = [
            'signature', 'hash', 'merkle', 'withdrawal', 'attestation',
            'validator', 'block', 'transaction', 'state', 'proof',
            'verify', 'validate', 'process', 'apply', 'execute',
            'transition', 'consensus', 'fork', 'beacon', 'payload',
            'execution', 'blob', 'commitment', 'precompile', 'evm'
        ]
        for term in domain_terms:
            # Find term variations (case-insensitive, word boundaries)
            matches = re.findall(rf'\b{term}\w*\b', test_procedure, re.IGNORECASE)
            keywords.update(matches)

        # 6. Remove stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were',
            'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'should', 'could', 'may', 'might', 'must', 'can'
        }
        keywords = {k for k in keywords if k.lower() not in stop_words and len(k) > 2}

        # 7. Sort by specificity (longer = more specific)
        return sorted(keywords, key=lambda x: (len(x), x.lower()), reverse=True)
    ```

    ## Phase 3: Tier 3 Implementation (Glob + Grep)

    **Robust filesystem-based search using Claude Code's Glob and Grep tools:**

    ```python
    def try_glob_grep_search(item: dict, keywords: List[str]) -> dict:
        """
        Tier 3: Filesystem-based search using Glob and Grep.
        This ALWAYS works even if MCP fails.
        """
        locations = []

        # 1. Identify relevant file patterns based on entry points
        entry_points = item.get('reachability', {}).get('entry_points', [])
        file_patterns = get_file_patterns_for_entry_points(entry_points)

        # 2. For each keyword, search in relevant files
        for keyword in keywords[:15]:  # Top 15 keywords
            # Search for function/method definitions
            grep_patterns = [
                # Go function definitions
                f'func\\s+.*{keyword}',
                f'func\\s+\\([^)]+\\)\\s+{keyword}',
                # Type definitions
                f'type\\s+{keyword}',
                # Variable/constant definitions with keyword
                f'(const|var)\\s+{keyword}',
            ]

            for pattern in grep_patterns:
                try:
                    # Use Grep tool with regex
                    matches = Grep(
                        pattern=pattern,
                        path='target_workspace',
                        glob=file_patterns,
                        output_mode='content',
                        multiline=False,
                        head_limit=10
                    )

                    # Parse matches and extract locations
                    for match in matches:
                        location = parse_grep_match(match, keyword)
                        if location:
                            locations.append(location)

                    if len(locations) >= 5:
                        break

                except Exception as e:
                    continue

            if len(locations) >= 5:
                break

        # 3. Extract code excerpts for top 3 locations
        code_excerpts = []
        for loc in locations[:3]:
            try:
                excerpt = Read(
                    file_path=f"target_workspace/{loc['file']}",
                    offset=loc['line_range']['start'] - 1,
                    limit=min(50, loc['line_range']['end'] - loc['line_range']['start'] + 1)
                )
                code_excerpts.append(
                    f"// {loc['role'].upper()}: {loc['file']}:{loc['symbol']} "
                    f"(lines {loc['line_range']['start']}-{loc['line_range']['end']})\n"
                    f"{excerpt}"
                )
            except Exception:
                pass

        # 4. Build result
        if locations:
            item['code_scope'] = {
                'locations': locations[:5],
                'resolution_status': 'resolved',
                'resolution_error': '',
                'resolution_method': 'grep_fallback'  # Track which method succeeded
            }
            item['code_excerpt'] = '\n\n'.join(code_excerpts)
        else:
            item['code_scope'] = {
                'locations': [],
                'resolution_status': 'not_found',
                'resolution_error': 'Grep search found no matching functions'
            }
            item['code_excerpt'] = ''

        return item


    def get_file_patterns_for_entry_points(entry_points: List[str]) -> str:
        """
        Map entry point categories to file glob patterns.
        Optimized for Go codebases (prysm, geth, etc.)
        """
        pattern_map = {
            'P2P': '**/{p2p,sync,network}/**/*.go',
            'Transaction': '**/{txpool,transaction,core/types}/**/*.go',
            'EngineAPI': '**/{engine,catalyst,beacon,miner}/**/*.go',
            'Engine API': '**/{engine,catalyst,beacon,miner}/**/*.go',
            'Consensus': '**/{consensus,forkchoice,validator}/**/*.go',
            'Internal': '**/{core,internal,state}/**/*.go',
            'Internal API': '**/{core,internal,state}/**/*.go',
        }

        # Combine patterns for all entry points
        patterns = []
        for ep in entry_points:
            if ep in pattern_map:
                patterns.append(pattern_map[ep])

        # If no specific pattern, search all Go files
        if not patterns:
            return '**/*.go'

        # Return combined pattern (Glob supports multiple patterns)
        return '|'.join(patterns) if len(patterns) > 1 else patterns[0]


    def parse_grep_match(match: str, keyword: str) -> dict:
        """
        Parse Grep output to extract location information.

        Grep output format (content mode):
        file_path:line_number:line_content
        """
        lines = match.strip().split('\n')
        if not lines:
            return None

        # Parse first line to get file and line number
        first_line = lines[0]
        parts = first_line.split(':', 2)
        if len(parts) < 3:
            return None

        file_path = parts[0].replace('target_workspace/', '')
        line_num = int(parts[1])
        line_content = parts[2]

        # Extract function/symbol name from line content
        # Go function pattern: func (receiver) FunctionName(
        func_match = re.search(r'func\s+(?:\([^)]+\)\s+)?(\w+)', line_content)
        if func_match:
            symbol = func_match.group(1)
        else:
            # Type definition: type TypeName
            type_match = re.search(r'type\s+(\w+)', line_content)
            if type_match:
                symbol = type_match.group(1)
            else:
                symbol = keyword  # Fallback to keyword

        # Estimate line range (will be refined when reading file)
        estimated_end = line_num + 30  # Assume ~30 lines per function

        return {
            'file': file_path,
            'symbol': symbol,
            'line_range': {
                'start': line_num,
                'end': estimated_end
            },
            'role': 'primary' if keyword.lower() in symbol.lower() else 'related'
        }
    ```

    ## Phase 4: Optimized MCP Wrappers

    **Simplified MCP calls for Tier 1 & 2:**

    ```python
    def try_mcp_simple_search(item: dict, keywords: List[str]) -> dict:
        """
        Tier 2: Simplified MCP search without call graph.
        Faster and more reliable than full call graph analysis.
        """
        try:
            # Register project (idempotent)
            mcp__tree_sitter__register_project_tool(
                path=os.path.abspath('target_workspace'),
                name='target-project'
            )
        except Exception:
            pass  # Already registered

        locations = []

        for keyword in keywords[:10]:  # Top 10 keywords
            try:
                # Direct text search
                results = mcp__tree_sitter__find_text(
                    project='target-project',
                    pattern=f'(func|type).*{keyword}',
                    use_regex=True,
                    file_pattern='**/*.go',
                    max_results=5,
                    context_lines=0
                )

                # For each result, get symbol info
                for result in results:
                    try:
                        symbols = mcp__tree_sitter__get_symbols(
                            project='target-project',
                            file_path=result['file']
                        )

                        # Find matching function in symbols
                        for func in symbols.get('functions', []):
                            if keyword.lower() in func['name'].lower():
                                locations.append({
                                    'file': result['file'],
                                    'symbol': func['name'],
                                    'line_range': {
                                        'start': func.get('start_line', result.get('line', 1)),
                                        'end': func.get('end_line', result.get('line', 1) + 30)
                                    },
                                    'role': 'primary'
                                })
                                break
                    except Exception:
                        continue

                if len(locations) >= 5:
                    break

            except Exception:
                continue

        # Extract code excerpts
        code_excerpts = []
        for loc in locations[:3]:
            try:
                content = mcp__tree_sitter__get_file(
                    project='target-project',
                    path=loc['file'],
                    start_line=loc['line_range']['start'] - 1,
                    max_lines=min(50, loc['line_range']['end'] - loc['line_range']['start'] + 1)
                )
                code_excerpts.append(
                    f"// {loc['role'].upper()}: {loc['file']}:{loc['symbol']} "
                    f"(lines {loc['line_range']['start']}-{loc['line_range']['end']})\n"
                    f"{content}"
                )
            except Exception:
                pass

        if locations:
            item['code_scope'] = {
                'locations': locations[:5],
                'resolution_status': 'resolved',
                'resolution_error': '',
                'resolution_method': 'mcp_simple'
            }
            item['code_excerpt'] = '\n\n'.join(code_excerpts)
        else:
            raise Exception('MCP simple search found no results')

        return item
    ```

    ## Phase 5: Main Processing Loop

    ```python
    # Main processing loop
    for item in items:
        try:
            # Check layer scope first
            spec_layer = extract_spec_layer_from_notes(item.get('notes', ''))

            if TARGET_LAYER != 'unknown' and spec_layer != 'unknown':
                if TARGET_LAYER != spec_layer:
                    # Out of scope - skip analysis
                    item['code_scope'] = {
                        'locations': [],
                        'resolution_status': 'out_of_scope',
                        'resolution_error': f'Spec layer ({spec_layer}) does not match target layer ({TARGET_LAYER})'
                    }
                    item['code_excerpt'] = ''
                    results.append(item)
                    continue

            # In scope - resolve with multi-tier fallback
            resolved_item = resolve_code_location_multi_tier(item)
            results.append(resolved_item)

        except Exception as e:
            # Error handling - mark as error but continue
            item['code_scope'] = {
                'locations': [],
                'resolution_status': 'error',
                'resolution_error': str(e)
            }
            item['code_excerpt'] = ''
            results.append(item)

    # Write output
    with open(OUTPUT_FILE, 'w') as f:
        json.dump({'checklist_with_code': results}, f, indent=2)

    # Print summary
    status_counts = {}
    for item in results:
        status = item['code_scope']['resolution_status']
        status_counts[status] = status_counts.get(status, 0) + 1

    print(f"Processed: {len(results)} items")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")
    print(f"Output File: {OUTPUT_FILE}")
    ```

  </instructions>

  <output>
    <format>JSON object with "checklist_with_code" array</format>
    <schema>
      IMPORTANT: Output MUST match the Phase 02c schema exactly.

      {
        "checklist_with_code": [
          {
            // Keep ALL original fields from input checklist item
            "check_id": "string",
            "property_id": "string",
            "title": "string",
            "severity": "string",
            "reachability": {...},
            "test_procedure": "string",
            "expected_behavior": "string",
            "graph_element_under_test": "string",
            // ... all other original fields ...

            // Add/update these fields:
            "code_scope": {
              "locations": [
                {
                  "file": "string (relative path from workspace root, e.g., 'core/types/block.go')",
                  "symbol": "string (function/method/type name, e.g., 'ValidateRLPSize')",
                  "line_range": {
                    "start": int,
                    "end": int
                  },
                  "role": "primary" | "caller" | "callee" | "related"
                }
              ],
              "resolution_status": "resolved" | "out_of_scope" | "not_found" | "error",
              "resolution_error": "string (only if status=error, otherwise empty string)",
              "resolution_method": "mcp_callgraph" | "mcp_simple" | "grep_fallback" | "fuzzy" (optional, only if resolved)
            },
            "code_excerpt": "string (formatted code excerpts with markers, or empty string)"
          }
        ]
      }

      Schema Requirements:
      1. ALL original fields from input MUST be preserved
      2. code_scope.locations is a list (may be empty if not_found or out_of_scope)
      3. code_scope.resolution_status is REQUIRED:
         - "resolved": Successfully found code locations
         - "out_of_scope": Spec layer does not match target layer (e.g., EL spec on CL target)
         - "not_found": All resolution tiers failed to locate code
         - "error": Exception occurred during processing
      4. code_scope.resolution_error is REQUIRED (empty string if no error)
      5. line_range.start and line_range.end are both required integers
    </schema>
    <stdout>Max 10 lines: batch size, resolution stats, status.</stdout>
    <final_line>Output File: {{OUTPUT_FILE}}</final_line>
  </output>
</task>
