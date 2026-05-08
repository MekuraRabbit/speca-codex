# OpenZeppelin ERC-4626 Local Smoke Rehearsal, May 2026

This note records a local smoke rehearsal of the Codex App runner path against
the ERC-4626 portion of
[OpenZeppelin Contracts](https://github.com/OpenZeppelin/openzeppelin-contracts).
It is useful as a compatibility and quality check for this fork, but it is not a
production audit report and does not claim discovery of unknown vulnerabilities
in OpenZeppelin Contracts.

## Scope

| Field | Value |
|---|---|
| SPECA fork | `MekuraRabbit/speca-codex` |
| Target repository | `https://github.com/OpenZeppelin/openzeppelin-contracts` |
| Target ref | `v5.6.1` |
| Target commit | `5fd1781b1454` |
| Focus | ERC-4626 vault and related ERC-20 support contracts |
| Runner path | Codex App server runner |
| Target test runtime | Hardhat |

The configured scope focused on ERC-4626, the ERC-4626 interface, core ERC-20
interfaces and implementation, `SafeERC20`, and `Math`. Mocks, tests, docs,
scripts, governance, proxy, access-control, ERC-721, and ERC-1155 components
were outside the configured audit target.

## Phase Results

The smoke run completed the pipeline through Phase 05:

| Stage | Count |
|---|---:|
| Specification records | 8 |
| Generated properties | 125 |
| Properties with code locations | 125 |
| Phase 03 audit items | 125 |
| Phase 04 reviewed items | 125 |
| Phase 05 PoC candidates | 6 |

Phase 03 classifications:

| Classification | Count |
|---|---:|
| `not-a-vulnerability` | 112 |
| `potential-vulnerability` | 10 |
| `out-of-scope` | 3 |

Phase 04 review verdicts:

| Verdict | Count |
|---|---:|
| `PASS_THROUGH` | 115 |
| `CONFIRMED_POTENTIAL` | 8 |
| `DISPUTED_FP` | 2 |

## Candidate Triage

The original Phase 05 candidate index contained 6 PoC candidates. Post-run
triage grouped them into two root-cause families:

| Family | Original candidates | Triage result |
|---|---:|---|
| Max-boundary ERC-4626 conversion and limit views | 2 | Reproduced as a standards-compliance edge case |
| Short-delivering or fee-on-transfer underlying asset integration hazard | 4 | Grouped as one conditional integration hazard family |

The reproduced boundary test showed that a default-offset ERC-4626 vault at a
`type(uint256).max` share and asset-balance boundary can make conversion,
preview, and `maxWithdraw` view paths revert through checked arithmetic. The
immediately lower boundary returned successfully in the same local test. This is
best described as a boundary-state non-revert compliance issue, not as an
asset-extraction exploit.

The short-delivery candidates all depended on a vault being paired with a
fee-on-transfer, deflationary, or otherwise short-delivering underlying token.
Those candidates point to an integration caveat: the base implementation trusts
the nominal transfer amount unless an integrator adds custom accounting. They
should not be counted as independent OpenZeppelin core vulnerabilities.

## SPECA Observations

This rehearsal was useful because it exercised the Codex App worker path against
a widely used library target and reached Phase 05 candidate triage. It also
identified a quality issue in the candidate grouping step: one prerequisite could
be split across several nearby-symbol candidates. That observation led to a
Phase 04/05 improvement so conditional integration hazards and ERC-4626
max-boundary conversion issues are grouped by root cause more consistently.

## Limitations

- This was a local smoke test of SPECA Codex, not a vendor-ready security
  assessment.
- Phase 03 finding counts are property-level signals, not counts of independent
  vulnerabilities.
- Only the max-boundary candidate family was reproduced with a local Hardhat
  PoC.
- The short-delivery family was classified from code evidence and human triage;
  no dedicated short-delivery mock PoC was added in this rehearsal.
- The results should not be used as a claim that SPECA discovered a new
  production vulnerability in OpenZeppelin Contracts.

## Reproduction Outline

1. Configure a fresh SPECA output directory for the pinned OpenZeppelin
   Contracts target and ERC-4626 scope.
2. Run the prerequisite phases through Phase 04 with the Codex App runner.
3. Run Phase 05 to build representative PoC candidates.
4. Triage Phase 05 candidates by root cause and prerequisite.
5. Reproduce selected candidates with the target repository's native Hardhat
   test harness.
