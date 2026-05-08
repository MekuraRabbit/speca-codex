# Damn Vulnerable DeFi Local Rehearsal, May 2026

This note records a sanitized local rehearsal of the Codex App runner path
against [OpenZeppelin Damn Vulnerable DeFi](https://github.com/OpenZeppelin/damn-vulnerable-defi).
Damn Vulnerable DeFi is an intentionally vulnerable educational benchmark. This
run is useful as a compatibility and quality check for this fork, but it is not
production audit evidence and does not claim discovery of unknown vulnerabilities
in a live protocol.

No personal local paths, usernames, raw chat logs, API tokens, or worker traces
are included here. Paths are repository-relative.

## Scope

| Field | Value |
|---|---|
| SPECA fork | `MekuraRabbit/speca-codex` |
| Target repository | `https://github.com/OpenZeppelin/damn-vulnerable-defi` |
| Target commit | `6797353c7cb5409e3d388e9e8f13954f9bb5f609` |
| Target checkout | `target_workspace/damn-vulnerable-defi` |
| Output directory | `outputs/rehearsal_dvd` |
| Runner path | Codex App server runner |
| Target test runtime | Node.js `10.24.1` via `npx -p node@10 node ...` |

The rehearsal stayed within the pinned local target checkout. The scope audit
recorded zero actual external fetch, RPC, registry, explorer, deployment, or
transaction-infrastructure commands. Literal URL strings present in local target
files were not treated as network use.

## Environment Notes

Damn Vulnerable DeFi is an old Buidler/Ganache project. In this local
environment:

- `npm ci` was not usable because the historical lockfile was out of sync with
  package metadata.
- `npm install --legacy-peer-deps` without `--ignore-scripts` failed on old
  native dependencies under a modern Node runtime.
- The workable target setup command was:

```bash
npm install --ignore-scripts --no-audit --no-fund --legacy-peer-deps
```

The target contracts compiled successfully with:

```bash
npm run compile
```

Target Mocha tests were run with Node.js 10 because the old Ganache stack timed
out or failed under newer Node runtimes in this environment.

## Phase Results

Phase 03 generated 187 audit items across 184 partial files:

| Classification | Count |
|---|---:|
| `not-a-vulnerability` | 103 |
| `vulnerability` | 71 |
| `potential-vulnerability` | 7 |
| `informational` | 1 |
| `out-of-scope` | 5 |

Phase 04 reviewed all 187 items across 79 partial files:

| Review verdict | Count |
|---|---:|
| `PASS_THROUGH` | 109 |
| `CONFIRMED_VULNERABILITY` | 70 |
| `CONFIRMED_POTENTIAL` | 2 |
| `DISPUTED_FP` | 3 |
| `DOWNGRADED` | 3 |

Phase 05 grouped the 72 confirmed or potential review items into 9
representative PoC candidates.

## Phase 05 Candidate Results

All 9 representative PoC tests were manually implemented under
`target_workspace/damn-vulnerable-defi/test/speca-poc/` and passed locally.
Phase 05 selected and structured candidates; it did not fully automate exploit
test implementation.

| Candidate | Challenge | Verdict | Covered properties | PoC status |
|---|---|---|---:|---|
| `oracle-price-manipulation` | `compromised` | `CONFIRMED_VULNERABILITY` | 10 | passed |
| `oracle-source-quorum-degradation` | `compromised` | `CONFIRMED_POTENTIAL` | 1 | passed |
| `forced-flash-loan-fee-drain` | `naive-receiver` | `CONFIRMED_VULNERABILITY` | 5 | passed |
| `amm-spot-price-manipulation` | `puppet` | `CONFIRMED_VULNERABILITY` | 13 | passed |
| `flash-loan-governance-snapshot` | `selfie` | `CONFIRMED_VULNERABILITY` | 7 | passed |
| `flash-loan-deposit-credit` | `side-entrance` | `CONFIRMED_VULNERABILITY` | 11 | passed |
| `flash-loan-reward-snapshot` | `the-rewarder` | `CONFIRMED_VULNERABILITY` | 2 | passed |
| `unauthorized-token-approval` | `truster` | `CONFIRMED_VULNERABILITY` | 12 | passed |
| `direct-token-transfer-dos` | `unstoppable` | `CONFIRMED_VULNERABILITY` | 11 | passed |

The combined PoC test command was:

```bash
npx -p node@10 node node_modules/mocha/bin/mocha --timeout 30000 --exit --recursive test/speca-poc
```

Observed result:

```text
9 passing
```

## Known Limitations

- Damn Vulnerable DeFi is an educational benchmark with intentionally planted
  vulnerabilities. Passing this rehearsal does not imply performance on arbitrary
  production repositories.
- Phase 03 finding counts are property-level signals. They are not counts of
  independent vulnerabilities.
- The PoC tests were manually implemented from Phase 05 candidates.
- The `compromised/oracle-source-quorum-degradation` PoC proves that the two
  known compromised source keys can reduce oracle quorum from three sources to
  one. The stock challenge exposes two of three source keys, so this rehearsal
  does not demonstrate a full empty-source median DoS.
- The target checkout is expected to become dirty during local PoC testing
  because dependency installation and `test/speca-poc/` files are created inside
  the pinned target workspace.

## Reproduction Checklist

1. Start from a SPECA workspace with `outputs/BUG_BOUNTY_SCOPE.json`,
   `outputs/TARGET_INFO.json`, and the prerequisite phase outputs for the
   rehearsal target.
2. Run Phase 03/04 with the Codex App runner against a fresh output directory.
3. Run Phase 05:

```bash
uv run python scripts/run_phase.py --phase 05 --output-dir outputs/rehearsal_dvd
```

4. Implement or update PoC tests under the pinned local target checkout.
5. Run the target PoC suite with Node.js 10:

```bash
npx -p node@10 node node_modules/mocha/bin/mocha --timeout 30000 --exit --recursive test/speca-poc
```

6. Confirm `05_POC_CANDIDATES.json` and `05_POC_RESULT_*.json` agree on
   candidate IDs, representative property IDs, covered property IDs, and PoC
   paths.
