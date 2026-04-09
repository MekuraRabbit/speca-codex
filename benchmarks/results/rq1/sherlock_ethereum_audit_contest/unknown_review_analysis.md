# Findings Review & False Positive Root Cause Analysis

This document analyzes false positives across both `unknown_review.csv` (SPECA-only findings) and `findings_labels.csv` (all labeled findings including Sherlock-matched ones).

---

# Part I: Unknown Findings Review (unknown_review.csv)

Analysis of the 13 SPECA-discovered findings that were **not present** in the Sherlock contest dataset (`sherlock_contest_1140_issues_1766639267091.csv`).

## 1. Review Summary

| Finding ID | Repo | Classification | Human Review | Reviewer |
|---|---|---|---|---|
| PROP-5a6a79d5-post-002 | alloy-rs/evm | vulnerability | **valid** | Claude (automated) |
| PROP-5a6a79d5-inv-008 | alloy-rs/evm | vulnerability | **invalid** | Claude (automated) |
| PROP-57888860-post-001 | ethereum/c-kzg-4844 | vulnerability | **invalid** | Claude (automated) |
| PROP-57888860-pre-003 | grandinetech/grandine | potential-vulnerability | **invalid** | Claude (automated) |
| PROP-56ad1eb2-inv-005 | grandinetech/grandine | vulnerability | **invalid** | Claude (automated) |
| PROP-6a4369e9-inv-026 | sigp/lighthouse | vulnerability | **invalid** | Kirk (Sigma Prime) |
| PROP-57888860-inv-028 | sigp/lighthouse | potential-vulnerability | **invalid** | Kirk (Sigma Prime) |
| PROP-6a4369e9-inv-025 | OffchainLabs/prysm | potential-vulnerability | **valid** | Lin (Nethermind) |
| PROP-ff7df16a-post-001 | OffchainLabs/prysm | vulnerability | **invalid** | Lin (Nethermind) |
| PROP-6a4369e9-inv-026 | OffchainLabs/prysm | vulnerability | **valid** | Lin (Nethermind) |
| PROP-6a4369e9-inv-043 | OffchainLabs/prysm | vulnerability | **valid** | Lin (Nethermind) |
| PROP-ff7df16a-inv-020 | paradigmxyz/reth | potential-vulnerability | **invalid** | Claude (automated) |
| PROP-ff7df16a-inv-011 | paradigmxyz/reth | vulnerability | **invalid** | Claude (automated) |

**Totals**: 4 valid, 9 invalid (of which 7 were automated review, 6 from human experts)

### Automated Review Scope (7 findings)

| Verdict | Count |
|---|---|
| valid (spec deviation, informational) | 1 |
| invalid (always FP) | 6 |

All 6 invalid findings were verified as **false positives from the audited commit** — none were valid vulnerabilities that were subsequently fixed in the latest codebase. The relevant code at each audited commit is functionally identical to the current HEAD for the specific behaviors in question.

---

## 2. Sherlock Dataset Independence Verification

All 7 automated-review findings were confirmed as independent from the Sherlock dataset:

| Finding | Closest Sherlock Issue | Independence Confirmed |
|---|---|---|
| PROP-5a6a79d5-post-002 | None (alloy-rs/evm not in Sherlock as target) | Yes |
| PROP-5a6a79d5-inv-008 | None | Yes |
| PROP-57888860-post-001 | Sherlock mentions c-kzg recovery but re: index ordering, not polynomial degree | Yes |
| PROP-57888860-pre-003 | None for grandine blob reconstruction | Yes |
| PROP-56ad1eb2-inv-005 | #319 (blob schedule ordering) and #401 (ENR nfd gating) — different root causes | Yes |
| PROP-ff7df16a-inv-020 | None for reth EIP-7702 | Yes |
| PROP-ff7df16a-inv-011 | None (duplicate of inv-020) | Yes |

---

## 3. Detailed Findings

### 3.1 PROP-5a6a79d5-post-002 — alloy-rs/evm system call ordering (VALID)

**Claim**: `apply_pre_execution_changes` executes blockhashes (EIP-2935) before beacon roots (EIP-4788), violating the required order.

**Verification**: Confirmed. Both `SystemCaller::apply_pre_execution_changes` (mod.rs:58-59) and `EthBlockExecutor::apply_pre_execution_changes` (block.rs:122-124) call blockhashes before beacon roots, whereas the execution-specs and geth call beacon roots first.

**Impact**: Informational. The two system calls target independent contracts (0x000F3df6... vs 0x0000F908...) with no shared state. State roots are identical regardless of ordering. No consensus failure occurs. However, this is a spec deviation that could become critical if future EIPs introduce cross-dependencies between pre-execution system calls.

**Scope**: alloy-rs/evm is a library, not directly in Ethereum bug bounty scope. Reth inherits this ordering.

### 3.2 PROP-5a6a79d5-inv-008 — alloy-rs/evm blob gas limit (INVALID)

**Claim**: Block executor lacks MAX_BLOB_GAS_PER_BLOCK validation.

**Verdict**: Design choice, not vulnerability. Per EIP-4844, blob gas limit validation (`blob_gas_used <= MAX_BLOB_GAS_PER_BLOCK`) is a header/consensus-layer check. EIP-7742 further decouples blob count from the EL. Reth validates blob gas in its consensus module (`validate_4844_header_standalone`) before execution. geth follows the same separation. alloy-evm is a library that deliberately separates concerns.

**Audited commit vs latest**: No change. Blob gas accumulation without limit check exists at both a3ee030baf and HEAD.

### 3.3 PROP-57888860-post-001 — c-kzg-4844 polynomial degree (INVALID)

**Claim**: `recover_cells` doesn't validate recovered polynomial has degree < FIELD_ELEMENTS_PER_BLOB.

**Verdict**: Defense-in-depth observation, not exploitable. KZG proof verification (performed before recovery in all spec-defined workflows) mathematically guarantees the polynomial degree constraint. The consensus spec's `recover_polynomialcoeff` also omits this check (truncates without validating). c-kzg-4844 is additionally out of scope as an external C library.

**Audited commit vs latest**: No change. The `recover_cells` function has the same API contract at both 0aa3a1aa0f and HEAD.

### 3.4 PROP-57888860-pre-003 — grandine blob reconstruction threshold (INVALID)

**Claim**: Column-level 50% threshold doesn't guarantee per-blob 50% threshold because columns may contain different blob subsets.

**Verdict**: False premise. In PeerDAS, every `DataColumnSidecar` contains exactly one cell per ALL blobs in the block. The data matrix is uniform (blob_count rows x NUMBER_OF_COLUMNS columns), enforced by construction (`get_data_column_sidecars` iterates all blobs per column) and validation (`column.len() == kzg_commitments.len()`). Column-level >= 50% IS per-blob >= 50% by the uniform matrix structure.

**Audited commit vs latest**: No change. `DataColumnSidecar` structure identical at both f1d757971d and HEAD.

### 3.5 PROP-56ad1eb2-inv-005 — grandine fork digest epoch (INVALID)

**Claim**: `compute_fork_digest_post_fulu` uses `blob_entry.epoch` (activation epoch) instead of current epoch.

**Verdict**: Code correctly follows Fulu consensus spec. The spec's `compute_fork_digest` explicitly uses `blob_parameters.epoch` (the schedule entry's activation epoch) via `get_blob_parameters()`. Fork digest is intentionally constant within a blob schedule period — this is correct P2P domain separation. Using the current epoch would break peer connectivity by changing the digest every epoch.

**Audited commit vs latest**: No change. `compute_fork_digest_post_fulu` is identical at both f1d757971d and HEAD.

### 3.6-3.7 PROP-ff7df16a-inv-020 & inv-011 — reth EIP-7702 auth chain_id (INVALID, duplicates)

**Claim**: Transaction pool doesn't validate individual authorization chain_ids in EIP-7702 transactions.

**Verdict**: EIP-7702 spec mandates execution-time validation for authorization chain_ids; invalid tuples are skipped (not rejected) per spec. Revm's `apply_eip7702_auth_list` correctly validates and skips mismatched chain_ids at execution. geth also omits pool-level auth chain_id validation. These two findings are semantic duplicates generated from the same spec invariant.

**Audited commit vs latest**: No change. Pool validation logic (renamed from `validate_one_no_state` to `validate_stateless`) is functionally identical at both 8e65a1d1a2 and HEAD.

---

## 4. False Positive Root Cause Analysis

### 4.1 FP Origin by Pipeline Phase

| FP Origin Phase | Count | Finding IDs |
|---|---|---|
| Phase 03 (Audit) primary | 4 | inv-008, post-001, pre-003, inv-005 |
| Phase 01b/01e (Property Generation) primary | 2 | inv-020, inv-011 |

### 4.2 Root Cause Categories

#### Category A: Architectural Boundary Blindness (3 findings)

**Affected**: PROP-5a6a79d5-inv-008, PROP-ff7df16a-inv-020, PROP-ff7df16a-inv-011

The pipeline cannot distinguish "this validation is missing (bug)" from "this validation is the caller's/other-layer's job (by design)." When a spec describes behavior spanning multiple architectural layers (consensus + execution, pool + execution, library + client), the pipeline lacks a model of responsibility boundaries.

**Phase 03 specifics for inv-008**:
- 02c returned `resolution_status: "not_found"` but Phase 03 ignored the skip instruction
- Found regular gas limit check and used false analogy: "regular gas is checked here, so blob gas should be too"
- Never considered library vs. full-node architectural boundary

**Phase 01b/01e specifics for inv-020/011**:
- 01b extracted validation invariants (`INV-002: chain_id must match`) from `fork_types.py` — a pure data type definition, not validation logic
- 01e generated pool-level validation assertions from a type definition
- Missed that EIP-7702's design is "skip invalid at execution" not "reject at pool"

#### Category B: Failure to Verify Assumptions Against Spec (4 findings)

**Affected**: PROP-5a6a79d5-inv-008, PROP-57888860-pre-003, PROP-56ad1eb2-inv-005, PROP-57888860-post-001

Phase 03 found a "gap" between expectation and code, then classified it as a vulnerability without checking whether the gap is intentional per the spec.

**PROP-57888860-pre-003**: Saw Rust `ContiguousList` (variable-length) and hypothesized columns could have inconsistent blob counts. Never checked the spec's `get_data_column_sidecars` which proves uniform matrix construction.

**PROP-56ad1eb2-inv-005**: Assumed fork digest should vary per-epoch. Never checked that the Fulu spec explicitly uses `blob_parameters.epoch` (activation epoch) for domain separation.

#### Category C: Cryptographic/Mathematical Invariant Ignorance (2 findings)

**Affected**: PROP-57888860-post-001, PROP-57888860-pre-003

The pipeline cannot reason about properties enforced by mathematical/cryptographic construction rather than explicit code checks.

**PROP-57888860-post-001**: "No explicit degree check after recovery" → vulnerability. Missed that KZG proof verification (pairing-based cryptographic check) mathematically guarantees the polynomial degree. The proof-based approach ("prove property holds, gaps in proof are bugs") breaks when the "proof" relies on cryptographic hardness assumptions.

#### Category D: Semantic Deduplication Failure (1 finding pair)

**Affected**: PROP-ff7df16a-inv-020 and PROP-ff7df16a-inv-011

Two semantically identical properties generated from the same invariant note (`INV-002`). `inv-011` is a direct translation ("chain_id must match"), `inv-020` is a higher-level restatement ("must not be replayable"). Syntactic deduplication did not catch the semantic equivalence.

### 4.3 Phase-Level Contribution Matrix

| Phase | inv-008 | post-001 | pre-003 | inv-005 | inv-020 | inv-011 |
|---|---|---|---|---|---|---|
| 01b | — | — | — | — | **Primary** (type → invariant) | **Primary** |
| 01e | Minor (no arch boundary) | — | — | Minor (ambiguous notation) | **Primary** (wrong layer) | **Primary** (dedup) |
| 02c | Minor (wrong error msg) | Minor (misleading note) | — | — | Minor (missed revm) | Minor |
| 03 | **Primary** (ignored skip, false analogy) | **Primary** (no crypto reasoning) | **Primary** (wrong data model assumption) | **Primary** (didn't check spec) | Contributor (pool-only scope) | Contributor |

### 4.4 Recommended Pipeline Improvements

| Issue | Improvement | Phases Affected |
|---|---|---|
| Arch boundary blindness | Add `target_type: "library"\|"client"` to TARGET_INFO.json; inject responsibility boundary context into Phase 03 | 02c, 03 |
| Spec cross-reference gap | Mandate spec re-verification step in Phase 03 when a code "gap" is found before classifying as vulnerability | 03 |
| Cryptographic invariant ignorance | Inject crypto primitive guarantees (KZG binding, Merkle tree, erasure coding) into Phase 03 context | 03 |
| 02c `not_found` skip bypass | Strengthen Phase 03 prompt enforcement of skip instruction for `not_found` / `out_of_scope` resolutions | 03 |
| Semantic deduplication | Add embedding-based similarity check in 01e to catch semantically equivalent properties | 01e |
| Type → invariant over-inference | Constrain 01b subgraph extractor: data type definitions should not generate validation invariants unless the spec explicitly defines validation logic | 01b |

---

## 5. Methodology

### Verification Process

1. **Sherlock independence**: Keyword search across all 55K rows of `sherlock_contest_1140_issues_1766639267091.csv` for each finding's keywords, code locations, and spec references
2. **Latest code verification**: Cloned latest default branch of each repository, verified whether reported code patterns exist
3. **Spec verification**: Cross-referenced each finding against the canonical spec (execution-specs, consensus-specs, EIPs)
4. **Audited-commit comparison**: Compared code at audited commit vs HEAD to distinguish "always FP" from "was valid, now fixed"
5. **Pipeline tracing**: Traced each finding through 01e → 02c → 03 outputs on `ethereum-fusaka-20260220` and target-specific branches

### Verification Date

2026-03-18

### Reviewer

Claude Opus 4.6 (automated), with expert reviews from Kirk (Sigma Prime) and Lin (Nethermind) for Lighthouse and Prysm findings respectively.

---

# Part II: All Findings Label Analysis (findings_labels.csv)

Analysis of the 102 total labeled findings across all 10 target repositories, focusing on false positive root causes.

## 6. Overall Distribution

| Label | Count | Description |
|---|---|---|
| `fp_invalid` | 27 | Matched a Sherlock issue that was rejected as invalid |
| `tp_info` | 23 | True positive, informational severity |
| `unknown` | 18 | Not matched to any Sherlock issue (analyzed in Part I) |
| `tp` | 17 | True positive, matched valid Sherlock issue |
| `potential-info` | 6 | Potential finding, informational level |
| `fixed` | 5 | Valid bug, confirmed fixed in latest |
| `fp_review` | 4 | False positive, needs further review |
| `partially_fixed` | 2 | Valid bug, partially fixed |
| **Total** | **102** | |

**Precision metrics** (excluding `unknown`):
- TP-equivalent (tp + tp_info + fixed + partially_fixed + potential-info): 53 / 84 = **63.1%**
- FP-equivalent (fp_invalid + fp_review): 31 / 84 = **36.9%**

## 7. fp_invalid Analysis (27 findings)

### 7.1 Distribution by Repository

| Repository | fp_invalid Count |
|---|---|
| status-im/nimbus-eth2 | 9 |
| sigp/lighthouse | 6 |
| OffchainLabs/prysm | 5 |
| grandinetech/grandine | 3 |
| ethereum/c-kzg-4844 | 1 |
| ChainSafe/lodestar | 1 |
| NethermindEth/nethermind | 1 |
| paradigmxyz/reth | 1 |

### 7.2 Root Cause Categories

#### Category 1: Dead/Unused Code (8 findings, 30%)

**Sherlock #18**: "Nimbus PeerDAS builds wrong `DataColumnSidecars` in repair/reconstruction path"
**Sherlock #121**: "Each DataColumnSidecar contains too many cells/proofs instead of one per blob"

**Rejection reason**: Logical bug in dead code path — `get_data_column_sidecars()` was already unused, removed in PR #7511.

**Affected findings** (all Nimbus):
- PROP-6a4369e9-inv-008, inv-010, inv-011, asm-003, post-003
- PROP-57888860-pre-002, pre-007, inv-029

**Pipeline failure**: Phase 02c resolved code locations to functions that existed in the codebase but were not reachable from any live execution path. Phase 03 audited this dead code as if it were production code. Phase 04 (run only on Nimbus) correctly caught 5/8 as DISPUTED_FP.

**Root cause**: No dead code / reachability analysis in the pipeline. Phase 02c resolves symbols by name without checking whether they are called from any entry point.

#### Category 2: EL Trust Boundary Misunderstanding (7 findings, 26%)

**Sherlock #92**: "EL response re-ordering not explicitly rejected at CL custody-column boundary"
**Sherlock #250**: "Faulty execution clients will slip unverifiable data columns past Nimbus"
**Sherlock #331**: "Prysm violates EIP-7594 by trusting EL for data column sidecars without crypto verification"
**Sherlock #389**: "CL will falsely mark unavailable data as available, trusting unverified EL custody columns"

**Rejection reason**: CL intentionally trusts its own EL by design. The CL-EL interface (Engine API) runs over authenticated local connections (JWT/IPC). Skipping KZG verification for EL-sourced data is intentional for performance.

**Affected findings**:
- Grandine: PROP-6a4369e9-inv-018
- Lighthouse: PROP-6a4369e9-inv-010, inv-041, post-003, asm-001, asm-003 (57888860)
- Prysm: PROP-57888860-asm-003

**Pipeline failure**: Phase 01e properties assume all data must be cryptographically verified regardless of source. Phase 03 treats the EL as an untrusted source, flagging every verification skip as a vulnerability.

**Root cause**: The pipeline has no model of trust boundaries within the client architecture. The CL-EL trust relationship is a fundamental design assumption of the Ethereum consensus protocol (the "Engine API" spec explicitly defines this trust model), but SPECA's property generation treats all external inputs uniformly.

#### Category 3: Spec Interpretation / Design Choice (5 findings, 19%)

**Sherlock #94**: "Teku & Prysm Reject Spec-Compliant Blob Schedule" — Rejecting extra fields is correct behavior
**Sherlock #51**: "get_custody_groups Returns HashSet" — Internal data structure choice, no functional impact
**Sherlock #154**: "Blob Parameters Forks Computation Missing in fork_digest" — Protocol team confirmed code is correct
**Sherlock #282**: "secp256r1 Point-at-Infinity Consensus Split" — Too abstract, no demonstrated connection

**Affected findings**:
- Prysm: PROP-56ad1eb2-inv-014, inv-015, inv-027
- Grandine: PROP-57888860-inv-025
- c-kzg-4844: PROP-57888860-inv-053

**Pipeline failure**: Phase 01e over-inferred invariants from spec text. Phase 03 flagged spec-compliant behavior as deviations because its understanding of the spec differed from the protocol team's authoritative interpretation.

**Root cause**: Spec ambiguity — when the spec text is open to multiple interpretations, the pipeline may choose the stricter interpretation while client teams follow the protocol team's guidance (often communicated via Discord/GitHub issues, not in the spec document itself).

#### Category 4: Scope / Pre-existing Issues (4 findings, 15%)

**Sherlock #317**: "Missing Authentication/Authorization on IPC JSON-RPC Interface" — Not introduced in Fusaka
**Sherlock #53**: "Malicious gossip peer will stall PeerDAS sampling" — Erigon CL is out of scope
**Sherlock #64**: "Attacker can censor broadcasts" — Public disclosure before submission

**Affected findings**:
- Grandine: PROP-6a4369e9-asm-002
- Reth: PROP-ff7df16a-asm-002
- Lighthouse: PROP-6a4369e9-inv-039
- Nimbus: PROP-6a4369e9-inv-036

**Pipeline failure**: SPECA audits the entire codebase at a point-in-time commit. It has no concept of "changes introduced in this fork" (diff-based scoping) or external scope constraints.

**Root cause**: No diff-awareness. The pipeline generates properties from the full spec and audits the full codebase, rather than focusing on Fusaka-specific changes.

#### Category 5: Validation at Different Architecture Layer (3 findings, 11%)

**Sherlock #107**: "Missing TxGasLimit Validation In Block During NewPayload" — Validation exists deeper in stack
**Sherlock #222**: "Malicious peer will waste resources bypassing retention clamp" — Rate limiter handles this

**Affected findings**:
- Nethermind: PROP-aa9e39fd-pre-002
- Lodestar: PROP-6a4369e9-pre-008
- Prysm: PROP-6a4369e9-pre-008

**Pipeline failure**: Same pattern as Category A in Part I (architectural boundary blindness). Phase 03 found a missing check at one layer without verifying that the check exists at another layer.

**Root cause**: Phase 03's proof scope is limited to the code locations resolved by Phase 02c. When the validation lives in a different module/layer than where the property was resolved, Phase 03 cannot discover it.

### 7.3 Summary: fp_invalid Root Causes

| Root Cause | Count | % of fp_invalid | Pipeline Phase |
|---|---|---|---|
| Dead/Unused Code | 8 | 30% | 02c (no reachability), 03 (audits dead code) |
| EL Trust Boundary | 7 | 26% | 01e (no trust model), 03 (treats EL as untrusted) |
| Spec Interpretation | 5 | 19% | 01b/01e (over-inference from spec) |
| Scope / Pre-existing | 4 | 15% | Pipeline-wide (no diff-awareness) |
| Validation at Different Layer | 3 | 11% | 03 (narrow proof scope) |

## 8. Phase 04 FP Filter Effectiveness

Phase 04 (6-gate FP filter) was run on **all 10 target repositories** (output in `benchmarks/results/rq1/sherlock_ethereum_audit_contest/<repo>_fusaka/04_PARTIAL_*.json`). All 27 fp_invalid findings were processed by Phase 04.

### 8.1 Phase 04 Results on All fp_invalid Findings

| Finding ID | Repo | Phase 04 Verdict | Caught? |
|---|---|---|---|
| PROP-6a4369e9-inv-018 | grandine | **DISPUTED_FP** | Yes |
| PROP-6a4369e9-asm-002 | grandine | **DISPUTED_FP** | Yes |
| PROP-57888860-inv-025 | grandine | **DISPUTED_FP** | Yes |
| PROP-aa9e39fd-pre-002 | nethermind | **DISPUTED_FP** | Yes |
| PROP-ff7df16a-asm-002 | reth | **DISPUTED_FP** | Yes |
| PROP-56ad1eb2-inv-014 | prysm | **DISPUTED_FP** | Yes |
| PROP-56ad1eb2-inv-015 | prysm | **DISPUTED_FP** | Yes |
| PROP-6a4369e9-inv-010 | lighthouse | **DISPUTED_FP** | Yes |
| PROP-57888860-asm-003 | lighthouse | **DISPUTED_FP** | Yes |
| PROP-57888860-inv-029 | nimbus | **DISPUTED_FP** | Yes |
| PROP-57888860-pre-007 | nimbus | **DISPUTED_FP** | Yes |
| PROP-6a4369e9-asm-003 | nimbus | **DISPUTED_FP** | Yes |
| PROP-6a4369e9-inv-036 | nimbus | **DISPUTED_FP** | Yes |
| PROP-6a4369e9-post-003 | nimbus | **DISPUTED_FP** | Yes |
| PROP-56ad1eb2-inv-027 | prysm | DOWNGRADED | No (leaked) |
| PROP-57888860-asm-003 | prysm | CONFIRMED_POTENTIAL | No (leaked) |
| PROP-6a4369e9-pre-008 | prysm | CONFIRMED_VULNERABILITY | No (leaked) |
| PROP-6a4369e9-pre-008 | lodestar | CONFIRMED_POTENTIAL | No (leaked) |
| PROP-57888860-inv-053 | c-kzg-4844 | CONFIRMED_VULNERABILITY | No (leaked) |
| PROP-6a4369e9-asm-001 | lighthouse | CONFIRMED_VULNERABILITY | No (leaked) |
| PROP-6a4369e9-inv-039 | lighthouse | CONFIRMED_POTENTIAL | No (leaked) |
| PROP-6a4369e9-inv-041 | lighthouse | CONFIRMED_POTENTIAL | No (leaked) |
| PROP-6a4369e9-post-003 | lighthouse | CONFIRMED_POTENTIAL | No (leaked) |
| PROP-57888860-pre-002 | nimbus | CONFIRMED_VULNERABILITY | No (leaked) |
| PROP-6a4369e9-inv-008 | nimbus | CONFIRMED_VULNERABILITY | No (leaked) |
| PROP-6a4369e9-inv-010 | nimbus | CONFIRMED_VULNERABILITY | No (leaked) |
| PROP-6a4369e9-inv-011 | nimbus | CONFIRMED_POTENTIAL | No (leaked) |

**Overall Phase 04 filter rate**: 14/27 = **51.9%** of fp_invalid findings correctly filtered.

### 8.2 Phase 04 Filter Rate by Root Cause Category

| Root Cause Category | Caught | Leaked | Total | Filter Rate |
|---|---|---|---|---|
| Scope / Pre-existing | 3 | 1 | 4 | **75%** |
| Spec Interpretation | 3 | 2 | 5 | **60%** |
| Dead/Unused Code | 4 | 4 | 8 | **50%** |
| EL Trust Boundary | 3 | 4 | 7 | **43%** |
| Validation at Different Layer | 1 | 2 | 3 | **33%** |
| **Total** | **14** | **13** | **27** | **52%** |

### 8.3 Phase 04 Filter Rate by Repository

| Repository | Total fp_invalid | Caught | Leaked | Filter Rate |
|---|---|---|---|---|
| grandinetech/grandine | 3 | 3 | 0 | **100%** |
| NethermindEth/nethermind | 1 | 1 | 0 | **100%** |
| paradigmxyz/reth | 1 | 1 | 0 | **100%** |
| status-im/nimbus-eth2 | 9 | 5 | 4 | **56%** |
| OffchainLabs/prysm | 5 | 2 | 3 | **40%** |
| sigp/lighthouse | 6 | 2 | 4 | **33%** |
| ethereum/c-kzg-4844 | 1 | 0 | 1 | **0%** |
| ChainSafe/lodestar | 1 | 0 | 1 | **0%** |

### 8.4 Analysis of Leaked Findings (13)

**EL Trust Boundary leaks (4)**: Lighthouse inv-041, post-003, asm-001; Prysm asm-003. Phase 04 confirmed these because verification skip patterns look like real vulnerabilities from a pure code-analysis perspective. Gate 2 (Trust Boundary) cannot determine that "EL is trusted by design" without explicit trust model configuration.

**Dead Code leaks (4)**: Nimbus inv-008, inv-010, inv-011, pre-002. These describe gossip-vs-sync validation inconsistencies that reference real (live) code paths alongside dead code. Gate 1 (Dead Code) caught the obviously dead functions but missed cases where the finding spans both live and dead code.

**Spec Interpretation leaks (2)**: Prysm inv-027 (fork_digest, DOWNGRADED but not DISPUTED), c-kzg inv-053 (point-at-infinity, CONFIRMED_VULNERABILITY). These require authoritative spec interpretation that Phase 04 does not have access to.

**Validation at Different Layer leaks (2)**: Lodestar/Prysm pre-008 (#222, retention range). The "missing validation" pattern looks convincing; Gate 3 (Code Verification) didn't discover rate limiters as the actual mitigation.

**Scope leak (1)**: Lighthouse inv-039 (#53, Erigon CL out of scope). Phase 04 has no concept of which components are in audit scope.

## 9. fp_review Analysis (4 findings)

These findings require manual review but are likely false positives:

| Finding ID | Repo | Description |
|---|---|---|
| PROP-56ad1eb2-inv-014 | Lighthouse | BlobSchedule lacks max_blobs_per_block <= 4096 validation |
| PROP-6a4369e9-post-002 | Lodestar | Gossip validation check ordering (expensive before cheap) |
| PROP-57888860-post-003 | Prysm | ComputeCells return length not validated == 128 |
| PROP-6a4369e9-post-002 | Prysm | Self-peer bypass accepts own messages without REJECT checks |

These share characteristics with Category 3 (Spec Interpretation) and Category 5 (Validation at Different Layer). The Lighthouse finding is the same class as Sherlock #94 (spec-compliant behavior flagged). The Prysm self-peer bypass is a common pattern in gossip implementations (own messages are trusted by design).

## 10. SPECA-Independent Discoveries: Confirmed Fixes Outside Sherlock Dataset

SPECA identified **7 findings** (across 4 repositories) labeled `fixed` or `partially_fixed` that have **no match in the Sherlock contest dataset** (`csv_issue_id` is empty). These represent bugs independently discovered by SPECA and subsequently confirmed via fix commits on the latest branch.

### 10.1 Inventory

| Finding ID | Repo | Label | Fix Commit | Phase 04 Verdict |
|---|---|---|---|---|
| PROP-57888860-inv-003 | ethereum/c-kzg-4844 | fixed | f18ba082 | CONFIRMED_VULNERABILITY |
| PROP-6a4369e9-inv-043 | ChainSafe/lodestar | fixed | 3b98c59c | CONFIRMED_VULNERABILITY |
| PROP-6a4369e9-inv-037 | ChainSafe/lodestar | fixed | 3b98c59c | CONFIRMED_VULNERABILITY |
| PROP-57888860-inv-027 | status-im/nimbus-eth2 | partially_fixed | b3a3f3f9 | CONFIRMED_VULNERABILITY |
| PROP-57888860-pre-006 | status-im/nimbus-eth2 | partially_fixed | b3a3f3f9 | DISPUTED_FP |
| PROP-6a4369e9-inv-036 | OffchainLabs/prysm | fixed | b5bdd65f | NEEDS_MANUAL_REVIEW |
| PROP-57888860-inv-027 | OffchainLabs/prysm | fixed | b5bdd65f | CONFIRMED_POTENTIAL |

**Phase 04 retention**: 6/7 findings survived Phase 04 filtering (86%). One finding (PROP-57888860-pre-006) was incorrectly filtered as DISPUTED_FP — this is the same finding analyzed in Section 11 as a recall loss case.

### 10.2 Unique Bugs (4)

The 7 findings map to **4 unique bugs** (findings that share a fix commit address different aspects of the same bug):

#### Bug A: c-kzg-4844 — Wrong array in KZG challenge computation (1 finding)

**Finding**: PROP-57888860-inv-003 — "Challenge computation at line 877 passes `commitments_bytes` (original array with duplicates) instead of `unique_commitments` (deduplicated array) to `compute_verify_cell_kzg_proof_batch_challenge`."

**Impact**: High — incorrect challenge computation could lead to accepting invalid KZG proofs. The challenge hash includes commitment data; using duplicates instead of deduplicated commitments produces a different challenge value, potentially allowing a crafted proof to pass verification.

**Fix commit**: `f18ba082` — corrected to pass `unique_commitments`.

**Significance**: This is a cryptographic correctness bug in a core library (c-kzg-4844) used by multiple Ethereum clients. It was not reported in the Sherlock contest, likely because c-kzg-4844 was treated as an external dependency by most auditors.

#### Bug B: Lodestar — Inverted logic + missing validation in data column handling (2 findings)

**Finding 1**: PROP-6a4369e9-inv-043 — "Logic inverted: function returns early when `blobsCount > 0` (line 58), preventing `RESOURCE_UNAVAILABLE` error. When a block has blobs but node is missing custody columns, it yields partial sidecars instead of erroring."

**Finding 2**: PROP-6a4369e9-inv-037 — "`validateBlockDataColumnSidecars` validates `kzgProofs.length == kzgCommitments.length` but does NOT validate `column.length == kzgCommitments.length`. `cellIndices`/`cells` arrays use `column.length` for indexing, causing potential mismatch."

**Impact**: Medium — inverted early return silently returns partial data instead of signaling unavailability, potentially causing downstream consensus issues. Missing length validation could cause index-out-of-bounds or incorrect sidecar construction.

**Fix commit**: `3b98c59c` — corrected both the early return logic and added column length validation.

**Significance**: Two distinct aspects of PeerDAS data column handling, both caught by SPECA from different properties (invariant vs. validation). The inverted logic is a classic boolean error that is difficult to catch without specification-driven analysis.

#### Bug C: Nimbus — Unchecked array access in cell proof construction (2 findings)

**Finding 1**: PROP-57888860-inv-027 — "Function assumes `cell_proofs` contains exactly `blobs.len * CELLS_PER_EXT_BLOB` elements but performs no validation. Line 328 performs unchecked indexed access `cell_proofs[i * CELLS_PER_EXT_BLOB + j]`."

**Finding 2**: PROP-57888860-pre-006 — "Missing bounds check before array access. Function assumes `cell_proofs.len >= blobs.len * CELLS_PER_EXT_BLOB` but no validation exists at any call site (RPC, EL paths, block recovery)."

**Impact**: Medium — out-of-bounds array access in Nim (no automatic bounds checking in release builds with `--panics:off`) could cause a crash or memory corruption. Reachable from multiple entry points including RPC and EL Engine API responses.

**Fix commit**: `b3a3f3f9` — added bounds validation (partially fixed; some call paths may still lack checks).

**Significance**: Both findings describe the same underlying bug from different property perspectives (invariant assertion vs. precondition). The `partially_fixed` label indicates the fix addressed the primary path but may not cover all callers — a common pattern with bounds-check bugs.

#### Bug D: Prysm — Wrong subnet parameter + missing cell count validation (2 findings)

**Finding 1**: PROP-6a4369e9-inv-036 — "Code iterates over custody columns and broadcasts each, but line 154 passes `sidecar.Index` (column index) directly as the subnet parameter instead of computing `column_index % NUMBER_OF_CUSTODY_GROUPS`."

**Finding 2**: PROP-57888860-inv-027 — "Code calls `kzg.ComputeCells()` without validating `len(cells)==128`, then constructs proofs array with exactly 128 elements."

**Impact**: Medium — incorrect subnet parameter causes data columns to be published to wrong subnets, breaking PeerDAS data availability guarantees. Missing cell count validation could cause silent data corruption if the KZG library returns an unexpected number of cells.

**Fix commit**: `b5bdd65f` — corrected subnet computation and added cell count validation.

**Significance**: The subnet parameter bug is a PeerDAS networking correctness issue that would cause node isolation from specific data columns. This type of off-by-one/wrong-variable bug is precisely the kind of spec-vs-implementation gap that SPECA's property-based approach is designed to catch.

### 10.3 Summary

| Metric | Value |
|---|---|
| Total SPECA-independent findings | 7 |
| Unique bugs discovered | 4 |
| Repositories affected | 4 (c-kzg-4844, lodestar, nimbus, prysm) |
| Confirmed fully fixed | 5 |
| Confirmed partially fixed | 2 |
| Not in Sherlock dataset | 7/7 (100%) |
| Survived Phase 04 | 6/7 (86%) |

These 4 bugs represent **genuine independent discoveries** by SPECA — they were not reported by any of the 366 Sherlock contest submissions, yet they were confirmed as real bugs by the respective development teams (evidenced by fix commits on the latest branch). This demonstrates SPECA's ability to find vulnerabilities that traditional manual auditing misses, particularly:
- Cryptographic implementation bugs in core libraries (Bug A)
- Boolean logic errors in newly-added protocol code (Bug B)
- Missing bounds checks in unsafe language contexts (Bug C)
- Spec-implementation parameter mismatches (Bug D)

---

## 11. Phase 04 Recall Loss: TP Findings Incorrectly Filtered

Phase 04's DISPUTED_FP gate incorrectly filtered **6 true positive findings** (all `tp_info` severity). No H/M/L TP was lost — the recall-safe design holds for high-impact findings but over-filters informational ones.

### 10.1 Filtered TP Inventory

| Finding ID | Repo | Sherlock Issue | Severity | Gate | Root Cause |
|---|---|---|---|---|---|
| PROP-6a4369e9-inv-014 | grandinetech/grandine | #11 | info | Gate 2 (Trust Boundary) | Config file = operator-controlled |
| PROP-6a4369e9-inv-014 | sigp/lighthouse | #11 | info | Gate 2 (Trust Boundary) | Config file = operator-controlled |
| PROP-6a4369e9-inv-014 | OffchainLabs/prysm | #11 | info | Gate 2 (Trust Boundary) | Config file = operator-controlled |
| PROP-1ada093f-inv-041 | NethermindEth/nethermind | #212 | info | Gate 5+6 (Spec + Scope) | Spec-compliant + pre-Fusaka code |
| PROP-aa9e39fd-inv-008 | NethermindEth/nethermind | #65 | info | Gate 4 (Exploitability) | Acknowledged design choice |
| PROP-5a6a79d5-asm-002 | paradigmxyz/reth | #77 | info | Gate 3 (Code Verification) | Validation at type level |

### 10.2 Root Cause Analysis

#### A. Trust Boundary Over-Filtering (3 findings — PROP-6a4369e9-inv-014)

**Issue**: Sherlock #11 — "Prysm has abnormal behaviour from LH, TEKU and Specs on BPO + HardFork epoch, which leads to a network peer isolation of all Prysm nodes"

**Phase 04 reasoning**: Gate 2 classified the entry point as "local configuration files (loaded via CLI flag ChainConfigFileFlag)" under `local_validator` trust assumption with `in_scope_for_bug_bounty=false`. Conclusion: no untrusted path can deliver malicious configs.

**Why this is wrong**: The finding is not about malicious config injection — it is about a **spec deviation** in how blob parameters at fork boundaries are computed. The bug is triggered by the normal upgrade process (all operators upgrading to Fusaka), not by attacker-controlled input. Gate 2's trust boundary model assumes all vulnerabilities require an attacker-controlled entry point, but correctness bugs that manifest during normal operation (fork transitions, config parsing) do not fit this model.

**Pipeline fix**: Gate 2 should exempt "correctness/spec-deviation" findings from trust boundary filtering. When the finding's classification is `potential-vulnerability` or the matched issue is a spec deviation (not an exploit), trust boundary analysis is not applicable.

#### B. Spec Cross-Reference + Scope Over-Filtering (1 finding — PROP-1ada093f-inv-041)

**Issue**: Sherlock #212 — "Erigon panic DoS in blob-wrapped tx when commitments > blobs"

**Phase 04 reasoning**: Gate 5 found the code is spec-compliant (RLP exception caught and handled gracefully, peer disconnected). Gate 6 found the RLP decoding code is pre-Fusaka generic infrastructure, not Fusaka-specific.

**Why this is a borderline case**: The Nethermind code does handle the exception without crashing (spec-compliant). However, the Sherlock issue was about Erigon's handling of the same scenario (panic), and the `human_label` confirms "same report found on Erigon #212." The finding correctly identifies the attack vector (malformed blob tx) even though Nethermind's implementation happens to handle it gracefully. Phase 04 correctly identified the defense but over-applied the scope gate — the finding has value as cross-client validation that the defense exists.

**Pipeline fix**: When a finding matches a known issue from another client, the scope gate should not dismiss it. Cross-client validation findings should survive Phase 04 regardless of whether the specific client has the bug.

#### C. Exploitability Dismissal of Design Choice (1 finding — PROP-aa9e39fd-inv-008)

**Issue**: Sherlock #65 — "EstimateGas Not Enforced Against TX_GAS_LIMIT_CAP By EIP-7825 In Reth"

**Phase 04 reasoning**: Gate 4 found the race condition during fork activation is "acknowledged by design" (code comment: "this is used only in tx pool and this is not a problem there"). The timing difference between TxPool and BlockValidator during fork transitions is intentional.

**Why this is a borderline case**: The code comment acknowledges the race but does not fully analyze its security implications. The Sherlock issue (found on Reth, matched here on Nethermind) was accepted as informational precisely because the impact is "temporary mempool pollution that self-corrects." Phase 04 correctly analyzed the mechanism but over-weighted the "acknowledged by design" signal — a code comment saying "not a problem" is not equivalent to a formal security analysis.

**Pipeline fix**: Gate 4 should not treat developer comments as authoritative security dismissals. "Acknowledged in code" should downgrade severity, not trigger DISPUTED_FP.

#### D. Validation-at-Different-Layer Dismissal (1 finding — PROP-5a6a79d5-asm-002)

**Issue**: Sherlock #77 — "Incorrect max_blob_count initialization post-Osaka allows the Transaction Pool to accept transactions with 7-9 blobs"

**Phase 04 reasoning**: Gate 3 found the validation exists at the type level (EIP-4844 blob transactions are structurally enforced to have a `to` field of type `Address`, not `Option<Address>`). Phase 03's claim about missing pool-level validation is "factually incorrect" because the check exists at a lower layer.

**Why this is wrong**: Phase 04 evaluated a different aspect of the finding than what Sherlock #77 reports. The Sherlock issue is about `max_blob_count` initialization (blob count limits), not about the `to` field validation. Phase 04 verified a correct but **irrelevant** defense (type-level `to` field enforcement) and dismissed the finding. The actual bug (wrong max blob count post-Osaka) was not evaluated.

**Pipeline fix**: Gate 3 should verify the **specific claim** in the finding, not just find any valid defense in the same code region. When the Phase 03 finding text mentions "blob count" but Gate 3 verifies "contract creation field," there is a claim-verification mismatch that should prevent DISPUTED_FP.

### 10.3 Summary

| Root Cause | Count | Gate | Severity Impact |
|---|---|---|---|
| Trust boundary inapplicable to correctness bugs | 3 | Gate 2 | info only |
| Claim-verification mismatch | 1 | Gate 3 | info only |
| Developer comment as security authority | 1 | Gate 4 | info only |
| Cross-client scope over-application | 1 | Gate 5+6 | info only |
| **Total** | **6** | | **All info** |

**Key observation**: All 6 filtered TPs are `tp_info` (informational severity). Zero H/M/L TPs were filtered. The recall-safe design successfully protects high-impact findings, but the gates are overly aggressive on informational findings where the vulnerability pattern is real but the impact is low.

**Recommended improvement priority**:
1. Gate 2: Exempt correctness/spec-deviation findings from trust boundary filtering (fixes 3/6)
2. Gate 3: Add claim-verification alignment check — verify the specific claim, not just any defense (fixes 1/6)
3. Gate 4: Code comments should downgrade, not dismiss (fixes 1/6)
4. Gate 5+6: Cross-client matches should survive scope filtering (fixes 1/6)

---

## 12. Consolidated Root Cause Taxonomy

Combining Part I (6 unknown FPs) and Part II (27 fp_invalid + 4 fp_review), the full FP taxonomy is:

| Root Cause | Part I | Part II | Total | Primary Phase |
|---|---|---|---|---|
| Dead/Unused Code | 0 | 8 | 8 | 02c, 03 |
| EL Trust Boundary | 0 | 7 | 7 | 01e, 03 |
| Spec Interpretation / Design Choice | 1 | 5+4 | 10 | 01b, 01e |
| Architectural Boundary Blindness | 3 | 3 | 6 | 03 |
| Scope / Pre-existing | 0 | 4 | 4 | Pipeline-wide |
| Cryptographic/Mathematical Invariant | 2 | 0 | 2 | 03 |
| Semantic Deduplication Failure | 1 | 0 | 1 | 01e |
| **Total** | **7** | **31** | **38** | |

### Top 3 Actionable Improvements (by expected FP reduction)

1. **Spec re-verification in Phase 03** (10 FPs, Phase 04 catches 60%→need 40% more): When Phase 03 identifies a "missing check," require it to re-read the relevant spec section before classifying as vulnerability. Add a mandatory "spec says X, code does Y, therefore Z" chain-of-reasoning step with explicit spec quotation.

2. **Dead code / reachability analysis** (8 FPs, Phase 04 catches 50%→need 50% more): Add call-graph reachability check in Phase 02c. If a resolved symbol is not reachable from any entry point (main, RPC handler, gossip handler, etc.), mark as `out_of_scope`. Tree-sitter MCP's `find_usage` could support this.

3. **Trust boundary modeling** (7 FPs, Phase 04 catches 43%→need 57% more): Add trust boundaries to `BUG_BOUNTY_SCOPE.json` or `TARGET_INFO.json`. For Ethereum clients: `{trusted: ["engine_api", "local_validator"], untrusted: ["p2p_gossip", "rpc"]}`. Phase 01e properties should be scoped to untrusted inputs only. This is where Phase 04 has the **lowest filter rate**, making upstream improvement most critical.

## 13. Methodology (Part II)

1. **Label analysis**: Parsed all 102 rows of `findings_labels.csv`, grouped by `auto_label`
2. **Sherlock cross-reference**: For each `fp_invalid`, retrieved the matched Sherlock issue's rejection comment from `sherlock_contest_1140_issues_1766639267091.csv`
3. **Root cause categorization**: Grouped by Sherlock rejection reason pattern, then mapped to pipeline phase
4. **Phase 04 effectiveness**: Cross-referenced Phase 04 outputs on `nimbus_fusaka` branch with fp_invalid finding IDs
5. **Verification date**: 2026-03-18
