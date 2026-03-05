# Full Audit Automation

Runs the complete SPECA pipeline from a bug bounty URL. The user provides
only the bug bounty program URL and target repository — everything else is
automated. The user only needs to approve each step.

## Usage

```
/audit <bug_bounty_url> <target_repo> [options]
```

Examples:
```
/audit https://immunefi.com/bounty/ethereum ethereum/go-ethereum
/audit https://hackerone.com/cosmos cosmos/cosmos-sdk --workers 4
```

## Required inputs

| Input | Description | Example |
|-------|-------------|---------|
| `bug_bounty_url` | Bug bounty program page URL | `https://immunefi.com/bounty/ethereum` |
| `target_repo` | Target GitHub repository (`owner/repo`) | `ethereum/go-ethereum` |

## Optional inputs

| Input | Default | Description |
|-------|---------|-------------|
| `--workers` | `4` | Number of parallel workers |
| `--max-concurrent` | `64` | Max concurrent Claude calls |
| `--branch` | auto-generated | Git branch name to use |
| `--spec-urls` | (extracted from bug bounty page) | Comma-separated spec URLs |
| `--keywords` | (extracted from bug bounty page) | Comma-separated search keywords |

## Execution steps

### Step 0: Setup

1. Create a new branch: `audit/{target_repo_name}/{YYYYMMDD-HHMMSS}`
2. Extract information from the bug bounty URL:
   - **Scope**: in-scope assets (smart contracts, repos, URLs)
   - **Keywords**: project name, technology stack, protocol names
   - **Spec URLs**: documentation, specification links, GitHub wiki
3. Generate `outputs/BUG_BOUNTY_SCOPE.json`:
   ```json
   {
     "program_url": "<bug_bounty_url>",
     "program_name": "<extracted program name>",
     "in_scope_assets": ["<asset1>", "<asset2>"],
     "out_of_scope": ["<excluded1>"],
     "severity_ratings": "<program's severity classification if available>",
     "reward_range": "<reward info if available>",
     "notes": "<any special rules or conditions>"
   }
   ```
4. Generate `outputs/TARGET_INFO.json`:
   ```json
   {
     "target_repo": "<target_repo>",
     "target_ref_type": "latest_default_branch",
     "target_ref_label": "<default branch name>",
     "target_commit": "<full commit hash>",
     "target_commit_short": "<short commit hash>"
   }
   ```
5. Clone the target repository to `target_workspace/`
6. Run pre-flight tests: `uv run python3 -m pytest tests/ -v --tb=short`

**User approval point**: Confirm scope, target repo, and branch before proceeding.

### Step 1: Phase 01a — Spec Discovery

```bash
KEYWORDS="<extracted_keywords>" \
SPEC_URLS="<extracted_spec_urls>" \
uv run python3 scripts/run_phase.py --phase 01a
```

Discovers specification documents from the provided URLs and keywords.
Outputs: `outputs/01a_STATE.json`

Commit and push results.

### Step 2: Phase 01b — Subgraph Extraction

```bash
uv run python3 scripts/run_phase.py --phase 01b --workers $WORKERS
```

Extracts program graphs (Mermaid state diagrams) from discovered specs.
Outputs: `outputs/01b_PARTIAL_*.json`, `outputs/subgraphs/*.mmd`

Commit and push results.

### Step 3: Phase 01e — Property Generation

```bash
uv run python3 scripts/run_phase.py --phase 01e --workers $WORKERS
```

Generates formal security properties using STRIDE + CWE Top 25 analysis.
Requires: `outputs/BUG_BOUNTY_SCOPE.json` (created in Step 0)
Outputs: `outputs/01e_PARTIAL_*.json`

Commit and push results.

### Step 4: Phase 02c — Code Pre-resolution

```bash
uv run python3 scripts/run_phase.py --phase 02c --workers $WORKERS --max-concurrent $MAX_CONCURRENT
```

Pre-resolves code locations for properties against the target repository.
Requires: `outputs/TARGET_INFO.json`, Tree-sitter MCP server
Outputs: `outputs/02c_PARTIAL_*.json`, `outputs/01b_SUBGRAPH_INDEX.json`

Commit and push results.

### Step 5: Phase 03 — Audit Map

```bash
uv run python3 scripts/run_phase.py --phase 03 --workers $WORKERS --max-concurrent $MAX_CONCURRENT
```

Proof-based formal audit (Map -> Prove -> Stress-Test) against target code.
Outputs: `outputs/03_PARTIAL_*.json`

Commit and push results.

### Step 6: Phase 04 — Review

```bash
uv run python3 scripts/run_phase.py --phase 04 --workers $WORKERS --max-concurrent $MAX_CONCURRENT
```

3-gate FP filter (Dead Code -> Trust Boundary -> Scope Check) + severity calibration.
Outputs: `outputs/04_PARTIAL_*.json`

Commit and push results.

**User approval point**: Review final results before merging.

### Step 7: Summary

After all phases complete:
1. Print summary table: total properties, confirmed vulnerabilities, FPs filtered, by severity
2. Provide the web client URL for detailed exploration: `cd web && npm run dev`
3. Create a summary commit with all results

## Error handling

- If any phase fails, stop and report the error. Do NOT continue to the next phase.
- If a phase partially completes (some batches succeed, some fail), commit partial results and report.
- The user can resume from the failed phase by re-running with `--force` flag.
- Circuit breaker failures (3+ consecutive failures) indicate systemic issues — report and stop.

## Environment requirements

- `claude` CLI installed and authenticated
- `uv` installed (Python package manager)
- MCP servers configured: `bash scripts/setup_mcp.sh`
- Git configured with push access to the repository

## Notes

- Each phase commits and pushes results immediately after completion
- The web client (`web/`) can be started at any time to monitor progress
- All UI is in Japanese — results are visible at `http://localhost:5173`
- Token and repo are configured in the web client's Settings page
