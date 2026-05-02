# Ethereum 11-Client Comprehensive Audit — Task Brief

| | |
|---|---|
| **Status** | Draft (v0.1) |
| **Owner** | @grandchildrice |
| **Last updated** | 2026-05-03 |
| **Disclosure mode** | Closed (private repo + per-vendor encrypted bundles) |
| **Target start** | TBD — when `speca-cli` v0.2 is usable end-to-end |
| **Estimated duration** | 8–12 weeks (4 phases, ~2–3 weeks each) |
| **Tracking issue** | NyxFoundation/speca#TBD (linked at the bottom) |

> ⚠️ **This task involves coordinated security disclosure for production blockchain clients.** All findings remain **confidential** until each vendor's disclosure timeline is satisfied. See [§7 Closed-channel sharing](#7-closed-channel-sharing-internal-team) and [§8 Per-client disclosure channels](#8-per-client-disclosure-channels-external) before producing any output that touches a real bug.

## 0. TL;DR

Use the SPECA pipeline (driven by `speca-cli`, see [SPECA_CLI_SPEC.md](SPECA_CLI_SPEC.md)) to perform a comprehensive cross-implementation audit of the **eleven Ethereum clients** currently in scope of the [Ethereum bug bounty program](https://ethereum.org/en/bug-bounty/) against the **current consensus + execution specifications**. Four phases:

1. **A. Past-fix dataset** — crawl every client's repo for already-fixed security issues. ~1500–3000 fixes, structured into a labelled JSONL set.
2. **B. Self-improvement loop** — replay SPECA against the dataset; iterate prompts until per-phase recall plateaus.
3. **C. Comprehensive run** — apply the locked-in prompts to the current `HEAD` of all 11 clients on the latest hard-fork specs.
4. **D. Closed disclosure** — submit confirmed vulnerabilities through each client's official channel; keep the cross-client comparative report private indefinitely.

**Output deliverables** (all kept in a private repo until disclosure clears):

- `dataset/eth-past-fixes-2026.jsonl` — labelled past-fix corpus (Phase A).
- `prompts/eth-audit-2026/<phase>_v<n>.md` — versioned prompts (Phase B).
- `outputs/eth-audit-2026/<client>/` — per-client SPECA outputs (Phase C).
- `reports/<client>-disclosure-<vuln-id>.md.gpg` — per-vendor encrypted reports (Phase D).
- `reports/aggregate-cross-client-2026.md` — internal-only summary (kept indefinitely private).

## 1. Mission and scope

### 1.1 Why this task

The SPECA paper ([arXiv:2604.26495](https://arxiv.org/abs/2604.26495)) demonstrated 100% recall (15/15 H/M/L) on the Sherlock Fusaka contest covering 10 clients. This task **scales that result**:

- **From 10 → 11 clients** (adds Erigon, drops c-kzg-4844 / rust-eth-kzg / alloy-evm sub-libraries that were Sherlock-specific).
- **From one fork → all live forks** (the contest was Fusaka-specific; we audit the entire surface that is currently in production).
- **Adds an explicit dataset baseline** (Phase A) to *measure* whether SPECA is improving and whether prompt edits help on real, time-stamped bugs.
- **Adds a real disclosure pipeline** (Phase D), not just contest validation.

### 1.2 The 11 in-scope clients

Verified against [ethereum.org/bug-bounty](https://ethereum.org/en/bug-bounty/) on **2026-05-03**.

| # | Client | Layer | Repo | Lang |
|---|---|---|---|---|
| 1 | **Geth** | EL | [`ethereum/go-ethereum`](https://github.com/ethereum/go-ethereum) | Go |
| 2 | **Nethermind** | EL | [`NethermindEth/nethermind`](https://github.com/NethermindEth/nethermind) | C# |
| 3 | **Besu** | EL | [`hyperledger/besu`](https://github.com/hyperledger/besu) | Java |
| 4 | **Erigon** | EL | [`ledgerwatch/erigon`](https://github.com/ledgerwatch/erigon) | Go |
| 5 | **Reth** | EL | [`paradigmxyz/reth`](https://github.com/paradigmxyz/reth) | Rust |
| 6 | **Lighthouse** | CL | [`sigp/lighthouse`](https://github.com/sigp/lighthouse) | Rust |
| 7 | **Lodestar** | CL | [`ChainSafe/lodestar`](https://github.com/ChainSafe/lodestar) | TypeScript |
| 8 | **Nimbus** | CL | [`status-im/nimbus-eth2`](https://github.com/status-im/nimbus-eth2) | Nim |
| 9 | **Prysm** | CL | [`prysmaticlabs/prysm`](https://github.com/prysmaticlabs/prysm) | Go |
| 10 | **Teku** | CL | [`ConsenSys/teku`](https://github.com/ConsenSys/teku) | Java |
| 11 | **Grandine** | CL | [`grandinetech/grandine`](https://github.com/grandinetech/grandine) | Rust |

**Re-verify this list at the start of Phase C** — the bug-bounty in-scope set changes occasionally (e.g., when a new client launches).

### 1.3 Specification corpus

- **Consensus specs:** [`ethereum/consensus-specs`](https://github.com/ethereum/consensus-specs) at the latest mainnet-active fork tag.
- **Execution specs:** [`ethereum/execution-specs`](https://github.com/ethereum/execution-specs) at the same tag.
- **EIPs:** [`ethereum/EIPs`](https://github.com/ethereum/EIPs) — every EIP referenced as Final/Last Call by the above two repos at audit start.
- **Engine API:** [`ethereum/execution-apis`](https://github.com/ethereum/execution-apis) at the matching tag.

Pin all four sources to the **same exact commits** at Phase C start; persist these in `outputs/eth-audit-2026/SPEC_PINS.json` so the run is reproducible months later.

## 2. Phase plan

```
       Phase A                   Phase B                      Phase C                 Phase D
  Past-fix dataset  ──▶  Prompt self-improvement  ──▶  Comprehensive audit  ──▶  Closed disclosure
   (~2 weeks)            (~3 weeks, iterative)         (~3 weeks compute)        (~2-4 weeks coord)
```

Each phase has an explicit gate before the next phase starts. Don't skip gates — Phase B's value comes from Phase A's quality, and Phase D's safety comes from the rigour of all upstream phases.

## 3. Phase A — Past-fix dataset construction

### 3.1 Goal

Build a structured corpus of **already-fixed security issues** in the 11 clients, time-stamped against the commit that introduced the bug and the commit that fixed it. This becomes the "ground truth bank" for prompt evaluation in Phase B.

### 3.2 Crawl scope per client

For each repo:

- All **closed PRs** with any of these signals:
  - Title or body contains `security`, `CVE`, `vulnerability`, `consensus`, `DoS`, `panic`, `overflow`, `OOB`, `RCE`, `auth bypass`, `incorrect`, `hardfork`, `fork choice`, `slashing`, `validator equivocation`, etc. (full keyword list in §3.6).
  - Linked from a public security advisory ([github.com/<repo>/security/advisories](https://docs.github.com/en/code-security/security-advisories)).
  - Tagged `security`, `severity:*`, `bug-bounty`, `audit-finding`, `cwe-*`, `consensus`, etc.
- All **closed issues** matching the same signals.
- All **GitHub Security Advisories** (public ones only — we don't have access to drafts).
- All **CHANGELOG / RELEASES.md** entries that describe a security fix (often contains additional context the PR doesn't).
- All **client-specific Bugcrowd / HackerOne / Immunefi disclosures** that have already gone public.
- All **independent audit reports** referenced by the client's docs (e.g. `audit/` directory in the repo).

### 3.3 Per-record schema

Each row in `dataset/eth-past-fixes-2026.jsonl`:

```json
{
  "id": "ETH-2026-PAST-00042",
  "client": "lighthouse",
  "fork_at_time_of_bug": "deneb",
  "introduced_in_commit": "abc1234…",
  "fixed_in_commit":      "def5678…",
  "fix_pr":               "https://github.com/sigp/lighthouse/pull/4567",
  "linked_advisory":      "GHSA-xxxx-xxxx-xxxx",
  "cve":                  "CVE-2024-12345",
  "severity_at_disclosure": "HIGH",
  "category":             "consensus",
  "cwe":                  ["CWE-770"],
  "title":                "Unbounded memory growth in attestation pool under crafted aggregation",
  "summary":              "1-3 sentence plain-English description",
  "spec_anchor":          "consensus-specs/specs/phase0/p2p-interface.md#…",
  "would_speca_have_caught_it": "tbd",
  "phase_responsible":    "01e | 02c | 03 | 04 | dataset_only",
  "raw_sources": ["url1", "url2", "..."]
}
```

The last two fields (`would_speca_have_caught_it`, `phase_responsible`) are filled in during **Phase B**, not Phase A.

### 3.4 Tooling

- **GitHub crawl:** `gh api graphql --paginate` for PRs / issues / advisories. Rate-limited; budget ~24h crawl-time per repo with backoff.
- **Storage:** the JSONL above + raw HTML / markdown snapshots under `dataset/raw/<client>/<PR>.json` for provenance.
- **De-duplication:** PRs that close issues that close other PRs that … — flatten to one record per *fix commit* (fix-merge-sha is the natural key). A bug fixed across multiple PRs (rare) deserves multiple records cross-linked via `related_ids`.
- **Categorization:** seed an LLM-assisted categorizer with the SPECA `STRIDE + CWE-Top-25` schema; **human-in-the-loop review every label** — this dataset becomes the evaluation oracle, sloppy labels destroy the loop.
- **Crawler entry point:** new script `benchmarks/scripts/crawl_eth_past_fixes.py` (does not exist yet — first deliverable of Phase A).

### 3.5 Acceptance criteria for Phase A

| # | Criterion |
|---|---|
| A1 | ≥ 1500 records total across the 11 clients, with ≥ 50 records per client (whichever is larger) |
| A2 | Every record has at least `client`, `fixed_in_commit`, `severity_at_disclosure`, `category`, `cwe`, `title`, `summary` populated (no missing fields among these) |
| A3 | Two-author manual review of a 100-record stratified sample with κ ≥ 0.85 inter-annotator agreement on `severity` and `category` |
| A4 | Categorization vocabulary matches SPECA's STRIDE + CWE-Top-25 schema 1:1 |
| A5 | The dataset is reproducible: `make dataset` re-runs the crawl from a clean state in < 24h |

### 3.6 Suggested keyword seed list

(Non-exhaustive — refine via the labelled sample.)

```
security, CVE-, GHSA-, vulnerability, vuln, advisory, exploit
consensus split, fork choice, slashable, slashing, equivocation
panic, OOB, out-of-bounds, segfault, deadlock, livelock
overflow, underflow, signedness, integer wrap
unbounded, allocation, memory leak, OOM, DoS, denial of service
deserialization, parser, malformed, validation bypass
crypto, signature, BLS, KZG, hash collision, replay
hardfork, fork transition, MEV, MEV-boost, builder
P2P, gossip, libp2p, devp2p, rpc, JSON-RPC, engine api
audit-finding, sherlock, immunefi, hackerone, code4rena
```

## 4. Phase B — Prompt self-improvement loop

### 4.1 Goal

Use the Phase A dataset as a **time-stamped oracle** to drive iterative prompt refinement: replay each SPECA phase as if the audit had happened *before* each fix commit; measure whether the bug would have been caught; refine prompts on the failures.

This is **human-in-the-loop**, not autonomous. The agent proposes prompt diffs; a human reviews and merges.

### 4.2 Per-phase evaluation harness

For each SPECA phase, define:

| Phase | Eval signal |
|---|---|
| **01a Spec Discovery** | Was the relevant spec section discovered when crawling the EIP/spec corpus that existed at `fixed_in_commit - 30d`? |
| **01b Subgraph Extraction** | Was the relevant function / state transition / invariant captured in a subgraph derived from the discovered spec? |
| **01e Property Generation** | Did a generated property assert the violated invariant — measured by semantic match against the bug's `summary` / `cwe` |
| **02c Code Pre-resolution** | Did the resolver pin the property to the actual buggy file/symbol/line range present at `introduced_in_commit`? |
| **03 Audit Map** | Did Phase 03 classify the property as `vulnerability` or `potential-vulnerability` against `introduced_in_commit`'s code? |
| **04 Audit Review** | Did Phase 04 NOT filter the finding as DISPUTED_FP? |

Each phase gets a **per-record verdict**: detected / missed-by-this-phase / dataset-out-of-scope-for-this-phase.

### 4.3 Iteration protocol

Each iteration cycle (~3 days):

1. **Sample 50 records** from the Phase A dataset stratified by `severity`, `category`, and `client`.
2. **Run all 6 phases** against each record's `introduced_in_commit` (rewinding time so the model doesn't see the fix).
3. **Score each phase** by §4.2.
4. **Cluster failures** by `phase_responsible` × `cwe`. Where 5+ records share a failure cluster, that's a **prompt edit candidate**.
5. **Propose prompt diff** (LLM-suggested + human-reviewed). New version: `prompts/eth-audit-2026/<phase>_v<n+1>.md`.
6. **Re-run** the same 50 records on the new prompt. Compute Δrecall, Δprecision, ΔF1 vs. previous version. **Reject** the diff if F1 drops > 1pp without a clear recall justification.
7. **Commit** the accepted prompt + a per-version eval JSON (`benchmarks/results/eth-audit-2026/iter-<n>/eval.json`).

### 4.4 Stopping criteria

Stop iterating on a phase when **any** of:
- Three consecutive iterations produce Δrecall < +1pp on a held-out 100-record validation slice.
- Compute spent on the phase exceeds **$300 cumulative**.
- Iteration count reaches **6** (hard cap to prevent overfitting).

When all 6 phases hit a stopping criterion → Phase B done. Lock prompts under a tag `prompts/eth-audit-2026/locked/`.

### 4.5 Anti-overfitting safeguards

- **Held-out validation slice (100 records)** never used during iteration — only for the stopping-criterion check.
- **Cross-client generalization check**: if a prompt edit improved Geth bug-detection but degraded Lighthouse, reject. We optimize for the cross-client mean, not any single client.
- **Time-stamped recovery**: only feed the model spec content that existed *at or before* `introduced_in_commit - 30d`. No retro-knowledge leakage.

## 5. Phase C — Comprehensive audit run

### 5.1 Setup

- **Specs:** pin the 4 spec repos (consensus-specs, execution-specs, EIPs, execution-apis) to commits matching the latest mainnet-active fork. Persist to `outputs/eth-audit-2026/SPEC_PINS.json`.
- **Targets:** for each of the 11 clients, pin `HEAD` of the default branch as of audit-start day. Persist to `outputs/eth-audit-2026/<client>/TARGET_INFO.json`.
- **Bug-bounty scope:** copy from the official Ethereum bug-bounty program; tailor each `BUG_BOUNTY_SCOPE.json` per client (e.g. severity classification follows ethereum.org's [Severity Levels](https://ethereum.org/en/bug-bounty/#severity-levels)).
- **Prompts:** the locked `prompts/eth-audit-2026/locked/` from Phase B.

### 5.2 Run orchestration

Two options:

**Option 1 — `speca-cli` interactive (preferred for the smaller clients).**
```bash
npx speca-cli init  # for each of the 11 client folders, with the locked prompts
npx speca-cli       # run end-to-end with live monitoring
```

**Option 2 — CI workflow (preferred for the largest clients: Geth, Lighthouse, Prysm, Teku, Reth).**
Reuse the existing `01a-discovery.yml` / `01b-subgraph.yml` / etc. workflows with the 11 client config dirs in a matrix.

The 11 runs are **independent** — execute in parallel where compute budget allows.

### 5.3 Per-client compute budget

Based on the paper's RQ1 numbers (~$60–80 per Lighthouse-class client; ~$30 per smaller client) and overhead for prompt iteration:

| Client | Phase 03 wall time | Tokens (in/out) | Estimated cost |
|---|---|---|---|
| Geth, Lighthouse, Prysm, Teku, Reth, Erigon | 5–10 min | 50K / 1.3M | $60–80 each |
| Lodestar, Nimbus, Nethermind, Besu, Grandine | 3–5 min | 25K / 600K | $30–50 each |
| **Total Phase C** | | | **~$500–800** |

Add ~30% for retries / circuit-breaker triggered re-runs → budget cap **$1500**.

### 5.4 Acceptance criteria for Phase C

| # | Criterion |
|---|---|
| C1 | All 11 clients produce a complete `outputs/eth-audit-2026/<client>/` tree with 01a → 04 PARTIALs |
| C2 | Total compute under the $1500 cap |
| C3 | Each client has ≥ 30 reviewed findings post-Phase 04 (signal: too few = pipeline misconfiguration) |
| C4 | Per-client `phase_comparison.json` shows Phase 04 broad precision ≥ 50% (else triage prompts before disclosure) |
| C5 | Cross-client property neighborhood metric (issues touched by ≥ 2 clients) ≥ 5 — sanity check that the shared spec vocabulary still works at scale |

## 6. Phase D — Closed disclosure & reporting

### 6.1 Triage

Before any external communication:

1. **Two-auditor sign-off** on each `CONFIRMED_VULNERABILITY` and `CONFIRMED_POTENTIAL` from Phase 04. No solo finding leaves the private repo.
2. **Reproducer required** for severity ≥ Medium. PoC under `reports/<client>/poc/<vuln-id>/`.
3. **Spec citation required** — every finding must cite the spec section / INV ID / EIP that defines the violated property.
4. **Severity calibration** against the Ethereum bug bounty rubric (ethereum.org severity levels), not the speca-internal one.

### 6.2 Per-client disclosure report format

One markdown file per finding, encrypted with the vendor's PGP key (or HackerOne's secure submission for clients on H1):

```
reports/<client>-<vuln-id>.md.gpg

Title: <succinct, copyable into vendor's bounty form>
Severity: <Critical | High | Medium | Low>
Affected component(s): <file:line ranges>
Discovered: <date> by SPECA / NyxFoundation
Reporter contact: security@nyx.foundation (placeholder; use real channel)

## Summary
<1 paragraph>

## Spec violation
<spec section + INV ID + paste of the relevant spec text>

## Code path
<file:line ranges + minimal code excerpt>

## Proof / proof attempt
<the Phase 03 proof_trace verbatim>

## Reproduction
<concrete steps; bash / curl / cargo test snippets>

## Suggested fix
<patch suggestion if obvious; else "vendor's choice">

## Disclosure timeline
- Discovered:    <date>
- Reported:      <date>
- Vendor ack:    <date or "pending">
- Patch landed:  <date or "pending">
- Public CVE:    <date or "pending">

## Provenance
- SPECA version: <git sha>
- Phase 04 finding id: <PROP-…>
- Spec pins: <SPEC_PINS.json sha>
```

### 6.3 Aggregate cross-client report (internal-only)

One report under `reports/aggregate-cross-client-2026.md` covering:

- Total findings × severity × verdict matrix.
- Cross-implementation property-neighborhood findings (the same property triggered TP on N of 11 clients).
- Comparative resilience ranking — but **redact client names** in any version that might leave the team. Public versions (e.g. for the SPECA paper follow-up) anonymize as `Client A / B / …`.
- Lessons-learned: which prompt-version × client combinations under- or over-performed. Feeds back into Phase B for the next audit cycle.

### 6.4 Acceptance criteria for Phase D

| # | Criterion |
|---|---|
| D1 | Every Critical / High finding submitted to the appropriate vendor channel within 7 days of triage sign-off |
| D2 | All disclosures use vendor-preferred encryption (PGP, HackerOne, Immunefi) — no plaintext bug content over email |
| D3 | Disclosure timeline tracker (`reports/disclosure-tracker.csv`) updated weekly |
| D4 | Aggregate report does not leave the private repo until vendor patches have shipped (or 90 days, whichever is later) |
| D5 | Lessons-learned commit lands in `prompts/eth-audit-2026/post-mortem-2026.md` with concrete prompt diffs queued for the next audit cycle |

## 7. Closed-channel sharing (internal team)

### 7.1 Recommended setup

| Layer | Tool | Why | Setup |
|---|---|---|---|
| **Source of truth (encrypted git)** | New private repo `NyxFoundation/speca-audits-2026` (or org-internal) | Co-located with workflow tooling; access via existing GitHub admin team | Create empty private repo; restrict to the 7 admins + named participants |
| **At-rest secret encryption inside the repo** | [`getsops/sops`](https://github.com/getsops/sops) + [`FiloSottile/age`](https://github.com/FiloSottile/age) recipients | Enables per-file ACL via age keys; works in CI; reviewable diffs (only the metadata) | `.sops.yaml` at repo root; each contributor adds an age public key; sensitive files (PoCs, findings) are sops-encrypted; non-sensitive (prompts, dataset structure) stays plaintext |
| **Per-vendor disclosure encryption** | GPG with vendor's published key | Industry standard for security@ disclosure | Per-vendor pubkey under `reports/keys/<client>.asc`; encrypt before email/H1 |
| **Inline collaboration** | GitHub PRs in the private repo | Issue tracking, review, audit trail without a separate tool | Use the same template stack as `NyxFoundation/speca` |
| **Long-form async (chat)** | Signal group **for non-finding context only** | Chat is not for content; only for "I'm starting Phase C on Geth tonight" | Pin a "no findings in chat" rule |
| **Backups** | One-shot weekly clone to encrypted local disk + offsite (Backblaze B2) | Prevents loss if GitHub access is revoked or repo is taken down | Cron job; each clone gpg-encrypted with team-key |

### 7.2 Anti-patterns to avoid

- ❌ Never paste finding content into Slack, Discord, Notion, or public Trello.
- ❌ Never push reproducers to a public branch even by mistake — the **public** `NyxFoundation/speca` repo's branch protection (§ admin-bypass enabled but PR review still required for non-admins) is **not** sufficient for sensitive content; use the dedicated **private** repo.
- ❌ Never hard-code vendor PGP keys in prompts or in the speca-cli package — pin them in the private repo only.
- ❌ Never run Phase D submissions from a personal account; use a dedicated security@nyx.foundation address with a logged audit trail.

## 8. Per-client disclosure channels (external)

| Client | Preferred disclosure channel | Notes |
|---|---|---|
| Geth | bounty@ethereum.org via [Ethereum bug bounty](https://ethereum.org/en/bug-bounty/) | Severity rubric matches ethereum.org/severity-levels |
| Nethermind | [Immunefi](https://immunefi.com/bounty/nethermind/) (verify at audit start) | Confirm program is still active |
| Besu | [Hyperledger security](https://www.hyperledger.org/security) + Ethereum bounty | Cross-submit |
| Erigon | [Immunefi](https://immunefi.com/) (verify) + Ethereum bounty | Confirm |
| Reth | [Paradigm security](mailto:security@paradigm.xyz) + Ethereum bounty | Confirm |
| Lighthouse | [HackerOne — Sigma Prime](https://hackerone.com/sigp) + Ethereum bounty | |
| Lodestar | security@chainsafe.io + Ethereum bounty | |
| Nimbus | security@status.im + Ethereum bounty | |
| Prysm | [security@prysmaticlabs.com](mailto:security@prysmaticlabs.com) + Ethereum bounty | |
| Teku | [Consensys security](https://consensys.io/security) + Ethereum bounty | |
| Grandine | [security@grandine.io](mailto:security@grandine.io) + Ethereum bounty | Confirm |

> **Re-verify all channels at the start of Phase D.** Bug-bounty channels and contact addresses change often; an outdated address can leak findings to the wrong inbox.

## 9. Risks & ethics

### 9.1 Risks

| Risk | Mitigation |
|---|---|
| **Finding leaks before disclosure** | Strict private repo + encrypted artifacts (§7); two-auditor sign-off; no findings in chat |
| **High false-positive rate floods vendor inboxes** | Phase B's recall-precision tuning + manual triage gate before Phase D — never auto-submit |
| **Self-improvement overfits to the past-fix dataset** | Held-out validation slice (§4.5); cross-client generalization check; hard iteration cap |
| **Compute cost overrun** | Per-phase budget caps wired into the orchestrator (already exists); monitor weekly |
| **Anthropic OAuth fingerprint blocked mid-run** | API-key fallback (see [SPECA_CLI_SPEC §4.5.5](SPECA_CLI_SPEC.md#455-stability-caveat)); secondary key in escrow |
| **Vendor disclosure timeline disputes** | Up-front 90-day disclosure policy posted publicly; finding-by-finding negotiation only when justified |
| **One vendor's slow response blocks the aggregate report** | Aggregate report ships on a 90-day rolling window with that vendor's findings redacted, not on the slowest vendor |

### 9.2 Ethics commitments

- We **do not** publish reproducers for Critical / High findings until the patch lands on mainnet for ≥ 30 days.
- We **do not** monetize findings outside official bug-bounty payouts. Bounty proceeds split per the team's pre-agreed contributor policy.
- We **do not** test exploits on mainnet, public testnets, or any infrastructure we don't own. PoCs live in private testnets only (Kurtosis, EthPandaOps devnets, or local Anvil).
- We **do** credit each client's security team in the post-disclosure public writeup.
- We **do** offer to walk vendors through any high-severity finding via a video call before formal submission, on request.

## 10. Roles & timeline

### 10.1 Roles

| Role | Responsibility | Headcount |
|---|---|---|
| **Audit lead** | Overall task ownership; gates between phases; vendor coordination | 1 (@grandchildrice) |
| **Dataset curator** | Phase A crawl + manual labelling | 2 (overlap with everyone else) |
| **Prompt engineer** | Phase B iteration | 2 |
| **Audit triager** | Two-auditor sign-off in Phase D | ≥ 2 distinct from finding author |
| **Vendor liaison** | Disclosure-channel comms | 1 |
| **Operations** | Compute budget, CI, secret rotation | 1 |

The same person can hold multiple roles, but **finding author ≠ finding triager** is a hard rule.

### 10.2 Timeline (target)

| Week | Milestone |
|---|---|
| W0 | Task kicked off — issue opened, private repo created, dataset crawler skeleton written |
| W1–W2 | Phase A crawl + initial labelling |
| W3 | Phase A: validation sample + κ ≥ 0.85 sign-off |
| W4–W6 | Phase B iteration cycles (1 cycle ≈ 3 days × 6 max) |
| W7 | Phase B: prompts locked under `locked/` tag |
| W8–W9 | Phase C: parallel runs across 11 clients |
| W10 | Phase C: triage gate; two-auditor sign-off |
| W11–W12 | Phase D: per-vendor disclosure submission |
| W12+ | Disclosure timeline tracking; aggregate report at 90-day rolling window |

Slip allowance: +25% per phase. The hard outer bound is **W16** (4 months) — beyond that, re-scope.

## 11. Success criteria (mission-level)

| # | Goal |
|---|---|
| S1 | Phase A produces a publishable past-fix dataset (≥ 1500 records, κ ≥ 0.85) — releasable on its own as a benchmark contribution to the SPECA paper line |
| S2 | Phase B prompt-locked tag exists and shows ≥ 10 pp recall improvement on the held-out slice vs. the un-tuned baseline prompts |
| S3 | Phase C completes for all 11 clients within the $1500 compute cap |
| S4 | At least 5 confirmed-vulnerability disclosures land at vendor channels in Phase D (calibration: SPECA v1 RQ1 found 4 novel bugs across 10 clients in a contest setting; this project's broader scope and self-improvement should comfortably clear that bar) |
| S5 | Aggregate cross-client report stays private until disclosure timelines clear; no leaks |
| S6 | Lessons-learned committed; the next audit cycle (e.g. against the next hard fork) starts with the post-mortem prompts as its baseline |

---

## Tracking

- Public tracking issue: NyxFoundation/speca#TBD (will be updated in this doc when opened).
- Private working repo: `NyxFoundation/speca-audits-2026` (to be created at W0).

If you are reading this and **not** part of the audit team, please contact @grandchildrice before acting on any of the above — coordinated disclosure depends on a single decision-making authority.
