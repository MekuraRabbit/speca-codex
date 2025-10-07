# === Fusaka (Osaka+Fulu) Spec: Deep Crawl & Natural‑Language Spec Generation ===
# Task Owner: /01_spec
# Usage: /01_spec <TARGET_DIRECTORY>
# Example: /01_spec ../contracts/docs
#
# Description:
# Produce a *comprehensive*, natural‑language specification for the Fusaka upgrade, covering
#   • Osaka (Execution Layer) and
#   • Fulu (Consensus Layer),
# by recursively traversing the seed links and all relevant sublinks (docs, code, READMEs),
# extracting authoritative details, and augmenting with web search. Emit a single JSON file
# at security-agent/outputs/01_SPEC.json that conforms to the NEW schema below (supports
# narrative procedures, step lists, error catalogs, invariants, runbooks, and worked examples).
#
# IMPORTANT:
# • Always run with `/serena` to maximize token efficiency.
# • Language: English.
# • Scope: Fusaka only (Osaka EL + Fulu CL). Include cross‑layer interfaces (Engine API, requests_hash, PeerDAS) where they constrain behavior.
# • Aggressively follow sublinks from the seeds; prefer primary sources.
# • Cite sources *inside strings* with [S1], [S2], … and append plain‑text `Sources:` mapping at the end of each string.
# • Output only the JSON file; no extra prints. Use the schema below exactly (order & names are strict).

SEED_URLS (breadth‑first across domains; then depth‑first up to depth=5 per domain):
1) Osaka EL (Python spec): https://github.com/ethereum/execution-specs/tree/forks/osaka/src/ethereum/forks/osaka
2) Fulu CL (MD spec): https://github.com/ethereum/consensus-specs/tree/master/specs/fulu
3) Auditor guide (index to EIPs, client links, devnets): https://notes.ethereum.org/@fredrik/fusaka-auditor-guide

CRAWLING RULES (strict):
- Start from SEED_URLS. Enumerate and visit all intra‑site references and inter‑repo links that define Osaka/Fulu behavior:
  * For Osaka: EL state transition, tx validation, gas accounting, EVM changes, precompiles, JSON‑RPC deltas (`eth_config`), blob fees/limits, requests pipeline.
  * For Fulu: fork activation, proposer lookahead, PeerDAS (data columns/sidecars, gossip topics, Req/Resp), custody/sampling, CL‑EL boundaries (Engine API expectations, requests_hash commitment).
- Include: READMEs, design/docs, CHANGELOG/RELEASE NOTES, test vectors/fixtures, in‑source docstrings/comments, p2p/Beacon API docs that are tagged for Fulu/Osaka.
- Prefer latest *stable* releases (tags `v*`, `release-*`). If unavailable, use `forks/osaka` tip and `consensus-specs/master` for Fulu. Record selected tag/commit and dates per fork.
- Exclude legacy or unrelated branches unless referenced by the latest fork docs. Skip examples unless they illustrate Fusaka behavior.

MANDATORY — Web Search:
- After repo crawling, perform web search to collect: official docs, EIPs included in Fusaka, Engine API refs, Beacon API refs, design notes, release posts, **bug bounty requirements** (scope/exclusions/reporting/severity/rewards) from recognized platforms (Sherlock/Code4rena/Immunefi/HackerOne).
- Prioritize: official GitHub/Docs > Foundation/EIP/Ethereum.org > official audits > recognized bounty platforms.
- Use inline `[S#]` footnotes in strings; append `Sources: [S1] https://..., [S2] https://...`.

AUTO‑DETECT GENRE:
- Expect **Ethereum Client** (EL/CL specs). If multi‑domain patterns appear (e.g., WebApp docs), still capture but tag flows accordingly.

🎯 GOALS — Before a security audit, capture:
1) Current architecture per fork (components, state machines, data flows, cross‑layer interfaces).
2) **Natural‑language normative behavior**: detailed “what” and **procedural “how”** with numbered steps.
3) APIs & key algorithms (Engine/Beacon APIs, fee math, sampling, validation gates) with **error catalogs**.
4) Security‑critical invariants and requirements (DoS limits, custody thresholds, consensus safety).
5) Historical deltas (latest two versions/commits) and **worked examples** for edge cases.

📥 INPUT POLICY:
- Root Directory: {{TARGET_DIRECTORY}}
- Traverse Markdown/HTML/PDF/**code** breadth‑first; dedupe by path/heading.
- Prefer latest stable; else branch tips as above.
- Augment via web search; embed per‑string citations and source lists.
- **Fusaka‑only filter**: only include Osaka/Fulu items or cross‑layer elements affecting them.

📤 OUTPUT:
- Write one file: `security-agent/outputs/01_SPEC.json`.
- Use the NEW schema (below). Do not add keys or comments beyond the schema. Textual fields may be long and should use RFC 2119 keywords (MUST/SHOULD/MAY) where applicable.

SCHEMA (NEW, natural‑language capable; schema_version = "2.0.0-nl"):
```

{
"metadata": {
"source\_directory": "{{TARGET\_DIRECTORY}}",
"spec\_generated\_at": "<RFC3339 timestamp>",
"latest\_tags\_or\_commits": {
"osaka": "\<tag|commit-hash>",
"fulu": "\<tag|commit-hash>"
},
"latest\_release\_dates": {
"osaka": "<YYYY-MM-DD>",
"fulu": "<YYYY-MM-DD>"
},
"schema\_version": "2.0.0-nl"
},
"forks": \[
{
"name": "Osaka",
"layer": "Execution",
"genre": "Ethereum Client Spec",
"architecture": {
"overview": "Natural-language paragraph describing Osaka scope, activation conditions, components, and CL boundary (Engine API, requests\_hash). \[S1]\[S2] Sources: \[S1] https\://..., \[S2] https\://...",
"components": \[
{
"name": "State Transition",
"type": "service|library|module",
"description": "Role, boundaries, and trust assumptions. \[S1] Sources: \[S1] https\://...",
"depends\_on": \["Tx Validation", "EVM", "Engine API"],
"technology": \["Python", "EVM", "RLP"]
}
],
"state\_machines": \[
{
"name": "Block Execution",
"inputs": \["BlockEnvironment", "Transactions", "Parent Header"],
"outputs": \["State Root", "Receipts Root", "Requests Hash"],
"invariants": \[
"Total gas used MUST NOT exceed block gas limit. \[S1] Sources: \[S1] https\://..."
],
"transitions": \[
"1. Validate header fields (timestamps, limits, base fee).",
"2. For each transaction, apply Osaka tx rules and execute EVM.",
"3. Accumulate receipts, logs bloom, blob/fee accounting, requests."
]
}
],
"data\_flow\_diagram": "Mermaid code block (flowchart or sequence) showing Osaka datapaths and CL interface. \[S1] Sources: \[S1] https\://..."
},
"normative\_spec": \[
{
"id": "OSK-TX-VALIDATION",
"title": "Transaction Validation under Osaka",
"summary": "What the validator MUST/SHOULD do before execution. \[S1]\[S2] Sources: ...",
"preconditions": \[
"Fork activation time reached; chain config loaded. \[S1] Sources: ..."
],
"inputs": \["Typed transaction", "Chain config", "Account state"],
"procedure": \[
"1. Decode typed transaction; reject if unknown type.",
"2. Enforce TX\_MAX\_GAS\_LIMIT and calldata floor pricing.",
"3. Verify nonce, signature/auth (e.g., SetCode auth), and balances.",
"4. If blob tx: validate blob hashes, count, and price bounds."
],
"postconditions": \[
"Transaction is either accepted into execution or rejected with precise error."
],
"errors": \[
{"code": "ERR\_TX\_GAS\_CAP", "when": "gas > 2^24", "effect": "reject"},
{"code": "ERR\_BLOB\_COUNT", "when": ">6 per tx", "effect": "reject"}
],
"rationale": "Defends against DoS from over‑sized transactions and enforces fee market rules. \[S1] Sources: ..."
}
],
"algorithms": \[
{
"name": "Blob Base Fee Update (Osaka)",
"purpose": "Compute blob gas price from excess\_blob\_gas with lower bound.",
"pseudocode": "`pseudo\nfunction blob_gas_price(excess): ...\n` \[S1] Sources: \[S1] https\://...",
"complexity": "O(1)",
"notes": "Monotonicity MUST hold; no under/overflow. \[S1] Sources: ..."
}
],
"apis": {
"interfaces": \[
{
"kind": "json\_rpc",
"name": "eth\_config",
"stability": "stable",
"request\_schema": "{...}",
"response\_schema": "{...}",
"errors": \["InvalidParams", "InternalError"],
"notes": "Expose Osaka constants and blob schedule. \[S1] Sources: ..."
},
{
"kind": "engine\_api",
"name": "forkchoiceUpdatedV\*",
"stability": "stable",
"sequence\_diagram": "Mermaid sequence of CL→EL FCU with Osaka fields. \[S1] Sources: ..."
}
]
},
"wire\_protocol": {
"topics": \[],
"notes": "EL wire protocols referenced (if any). Keep brief; most wire‑level changes are on CL side."
},
"constants": \[
{"name": "TX\_MAX\_GAS\_LIMIT", "value": "16777216", "units": "gas", "notes": "2^24. \[S1] Sources: ..."}
],
"invariants": \[
"RLP execution block size MUST NOT exceed MAX\_RLP\_BLOCK\_SIZE. \[S1] Sources: ..."
],
"user\_flows": \[
{
"id": 1,
"title": "\[Client] New transaction inclusion (Osaka rules)",
"actors": \["User", "EL Client", "CL via Engine API"],
"preconditions": \["Osaka active", "Engine API connected"],
"steps": \[
"1. Receive tx via RPC/p2p.",
"2. Run OSK-TX-VALIDATION procedure.",
"3. Execute EVM; update receipts, requests\_hash.",
"4. Return payload result to CL."
],
"postconditions": \["State updated; payload advertised. \[S1] Sources: ..."]
}
],
"worked\_examples": \[
{
"id": "EX-OSK-BLOB-PRICE",
"title": "Blob gas price under low demand",
"scenario": "excess\_blob\_gas below threshold",
"given": "target=..., base cost=..., excess=...",
"when": "block contains k blobs",
"then": "blob gas price is bounded by execution cost lower bound. \[S1] Sources: ..."
}
],
"edge\_cases": \[
"CLZ opcode with input=0 MUST return 256. \[S1] Sources: ..."
],
"compatibility": {
"backwards": "Describe incompatibilities vs previous fork.",
"cross\_layer": "Summarize Osaka↔Fulu interplay (requests\_hash, blob availability). \[S1]\[S2] Sources: ..."
},
"changelog": {
"latest\_version": "\<tag|branch>",
"since\_previous": \[
{"commit": "<hash>", "date": "<YYYY-MM-DD>", "summary": "User‑visible Osaka delta. \[S1] Sources: ..."}
],
"breaking\_changes": \[
"List explicit breaking behaviors (caps, limits, new opcodes). \[S1] Sources: ..."
]
},
"bug\_bounty": {
"scope": "Repos/branches, in‑scope Osaka components. \[S1] Sources: ...",
"impact": "Critical/High definitions (funds at risk, consensus split, auth bypass). \[S1] Sources: ...",
"exclusions": "Non‑issues and out‑of‑scope items. \[S1] Sources: ...",
"reproduction": "Required PoC format, env, funding limits. \[S1] Sources: ...",
"reporting": "Channel/PGP/SLA. \[S1] Sources: ...",
"rewards": "Policy/tiers. \[S1] Sources: ..."
}
},
{
"name": "Fulu",
"layer": "Consensus",
"genre": "Ethereum Client Spec",
"architecture": {
"overview": "Natural-language paragraph describing Fulu scope (e.g., PeerDAS, proposer lookahead), activation, and EL boundary expectations. \[S1]\[S2] Sources: ...",
"components": \[
{
"name": "PeerDAS Sampling",
"type": "service|module",
"description": "Sampling, custody assignment, sidecar handling, validation gates. \[S1] Sources: ..."
}
],
"state\_machines": \[
{
"name": "Proposer Lookahead",
"inputs": \["Beacon state", "Epoch transitions"],
"outputs": \["Deterministic schedule"],
"invariants": \["Lookahead vector MUST be deterministic for pre‑confirmation safety. \[S1] Sources: ..."],
"transitions": \[
"1. Compute lookahead at epoch boundary.",
"2. Persist in state for external verification."
]
}
],
"data\_flow\_diagram": "Mermaid showing gossip topics (data\_column\_sidecar\_\*), Req/Resp, sampling & custody. \[S1] Sources: ..."
},
"normative\_spec": \[
{
"id": "FULU-PEERDAS",
"title": "Data Availability Sampling (PeerDAS)",
"summary": "Node MUST sample columns and verify cell KZG proofs; proposer MUST assemble sidecars correctly. \[S1] Sources: ...",
"preconditions": \["Fork active; subnet subscriptions in place. \[S1] Sources: ..."],
"inputs": \["Block body", "Data columns/sidecars", "KZG commitments"],
"procedure": \[
"1. Subscribe to per‑column subnets.",
"2. Sample assigned columns; verify KZG proofs.",
"3. Mark custody and contribute to availability decision."
],
"postconditions": \["Availability considered satisfied if sampling thresholds met. \[S1] Sources: ..."],
"errors": \[
{"code": "ERR\_INSUFFICIENT\_SAMPLES", "when": "below threshold", "effect": "treat as unavailable"}
],
"rationale": "Enables scalable blob throughput while bounding verification cost. \[S1] Sources: ..."
}
],
"algorithms": \[
{
"name": "Custody Assignment",
"purpose": "Assign columns to validators each slot/epoch.",
"pseudocode": "`pseudo\nassign_custody(state, slot): ...\n` \[S1] Sources: ...",
"notes": "Uniform distribution; resilience under churn. \[S1] Sources: ..."
}
],
"apis": {
"interfaces": \[
{
"kind": "beacon\_api",
"name": "GET /eth/v2/beacon/blocks/{slot}",
"stability": "stable",
"notes": "Document fields relevant to PeerDAS/requests. \[S1] Sources: ..."
}
]
},
"wire\_protocol": {
"topics": \[
"data\_column\_sidecar\_{subnet\_id}"
],
"notes": "Req/Resp RPCs for column range fetch. \[S1] Sources: ..."
},
"constants": \[
{"name": "SAMPLES\_PER\_BLOCK", "value": "<n>", "units": "columns", "notes": "If specified. \[S1] Sources: ..."}
],
"invariants": \[
"Proposer lookahead MUST be derivable from beacon root. \[S1] Sources: ..."
],
"user\_flows": \[
{
"id": 1,
"title": "\[Client] PeerDAS sampling cycle",
"actors": \["Validator", "Beacon Node"],
"preconditions": \["Subscribed to column subnets"],
"steps": \[
"1. Receive sidecars; verify proofs.",
"2. Sample assigned columns; record custody.",
"3. Contribute to availability verdict."
],
"postconditions": \["Block considered available/unavailable. \[S1] Sources: ..."]
}
],
"worked\_examples": \[
{
"id": "EX-FULU-SAMPLING",
"title": "Sampling with partial sidecar loss",
"scenario": "Lost sidecars in some subnets",
"given": "Assignment across k subnets",
"when": "Missing m sidecars",
"then": "Availability decision still satisfied if threshold met. \[S1] Sources: ..."
}
],
"edge\_cases": \[
"Sidecar with invalid cell proof MUST be rejected and penalized per rules. \[S1] Sources: ..."
],
"compatibility": {
"cross\_layer": "Fulu expectations on EL payloads (e.g., requests\_hash, blob accounting). \[S1]\[S2] Sources: ..."
},
"changelog": {
"latest\_version": "\<tag|branch>",
"since\_previous": \[
{"commit": "<hash>", "date": "<YYYY-MM-DD>", "summary": "User‑visible Fulu delta. \[S1] Sources: ..."}
],
"breaking\_changes": \[
"List explicit changes affecting client behavior. \[S1] Sources: ..."
]
},
"bug\_bounty": {
"scope": "Repos/branches, in‑scope Fulu components. \[S1] Sources: ...",
"impact": "Consensus split, slashable faults, DoS. \[S1] Sources: ...",
"exclusions": "Telemetry-only, cosmetic issues. \[S1] Sources: ...",
"reproduction": "Devnet/testnet steps; PoC requirements. \[S1] Sources: ...",
"reporting": "Channel/PGP/SLA. \[S1] Sources: ...",
"rewards": "Policy/tiers. \[S1] Sources: ..."
}
}
],
"cross\_layer": {
"interfaces": \[
{
"name": "Engine API / Fork Choice",
"preconditions": \["EL/CL versions compatible; JWT/auth as required"],
"sequence\_diagram": "Mermaid sequence of CL→EL FCU, payload attributes/payload status, with requests\_hash and excess\_blob\_gas fields. \[S1] Sources: ...",
"errors": \["INVALID\_PARAMS", "SYNCING", "INVALID\_BLOCK\_HASH"],
"timeouts": "Document expected timeouts and retries. \[S1] Sources: ...",
"notes": "Map Fulu expectations to Osaka commitments (headers, receipts). \[S1] Sources: ..."
}
],
"data\_availability": "Summarize how PeerDAS (Fulu) and blob pricing/limits (Osaka) interact. \[S1]\[S2] Sources: ..."
},
"security\_requirements": \[
{
"id": "SR-EL-001",
"description": "EL MUST enforce Osaka gas/size caps before execution; reject malformed payloads deterministically. \[S1] Sources: ...",
"risk\_category": "integrity",
"related\_components": \["Tx Validation", "State Transition"]
},
{
"id": "SR-CL-001",
"description": "CL MUST ensure DA sampling thresholds and proof verification before attesting. \[S1] Sources: ...",
"risk\_category": "consensus",
"related\_components": \["PeerDAS Sampling"]
},
{
"id": "SR-XL-001",
"description": "EL/CL interface MUST keep FCU/finality consistent; unvalidated payloads must not alter canonical state. \[S1] Sources: ...",
"risk\_category": "consistency",
"related\_components": \["Engine API"]
},
{
"id": "SR-EL-002",
"description": "Blob fee invariants MUST be monotonic with defined lower bound; prevent arithmetic under/overflow. \[S1] Sources: ...",
"risk\_category": "economic",
"related\_components": \["Fee Market"]
},
{
"id": "SR-CL-002",
"description": "Proposer lookahead MUST be deterministic from beacon state and verifiable externally. \[S1] Sources: ...",
"risk\_category": "liveness",
"related\_components": \["Proposer Lookahead"]
}
]
}

```

USER‑FLOW CONSTRUCTION (by genre):
- **[Ethereum Client]** Focus on inter‑node requests & consensus boundaries:
  Peer discovery → Handshake (eth/69 or Beacon gossip) → Tx/Blob propagation → Block import → FCU → Engine/Beacon API → Sync/Pruning → Metrics/Healthcheck.

QUALITY & WRITING RULES:
- Use RFC‑2119 keywords (MUST/SHOULD/MAY) in **normative_spec**.
- Each **procedure** is a *numbered* step list; each **errors** entry names a code, condition, and effect.
- Keep each narrative chunk concise but self‑contained (≤ 250 words).
- End every string with `Sources: [S#] URL, ...`

BUG BOUNTY INTEGRATION:
- Populate `bug_bounty` for both forks with: Scope, Impact, Exclusions, Reproduction, Reporting (PGP/contact/SLA), Rewards.
- Prefer official EF posts/pages and recognized platforms.

CHANGE LOG:
- Diff the two most recent releases/commits per fork; list **only user‑visible** changes. Mark breaking changes and migrations.

RUNTIME NOTE:
- If web search is unavailable, **abort** and treat as retryable error (do **not** emit a partial spec).
```

---
