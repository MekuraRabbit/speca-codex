# `speca-cli` — Specification & Requirements

| | |
|---|---|
| **Status** | Draft (v0.1) |
| **Owner** | @grandchildrice |
| **Last updated** | 2026-05-03 |
| **Distribution** | `npx speca-cli` (npm package) |
| **Related** | Top-level [README](../README.md), [benchmarks/README](../benchmarks/README.md), Python orchestrator under [`scripts/orchestrator/`](../scripts/orchestrator/) |

## 1. Overview

`speca-cli` is a **terminal user interface (TUI)** wrapper around the SPECA pipeline. Today, running SPECA requires:

1. Cloning the repo, installing `uv`, the Claude Code CLI, and Node.js
2. Hand-editing `outputs/BUG_BOUNTY_SCOPE.json` and `outputs/TARGET_INFO.json`
3. Running `uv run python3 scripts/run_phase.py --target 04 --workers 4` and tailing JSONL logs in another terminal
4. Manually browsing `outputs/03_PARTIAL_*.json` / `04_PARTIAL_*.json` to read findings

`speca-cli` collapses all of that into a single command — `npx speca-cli` — that opens an opencode-style TUI where users:

- **Authenticate once** with their existing Claude Code subscription (no API key, no quota juggling)
- **Configure a target** (point at a repo + spec URLs) via guided prompts, not raw JSON editing
- **Step through each phase** (01a → 04) with a "Run / Skip / Force re-run" prompt per phase
- **Watch logs and partial results stream live** in a side pane as workers complete
- **Browse findings interactively** once Phase 03/04 finishes — sortable by severity, filterable by verdict
- **Ask Claude follow-up questions** about any specific finding, log line, or property without leaving the TUI

The Python orchestrator under `scripts/orchestrator/` is **not rewritten** — `speca-cli` invokes it as a subprocess and parses its stream-JSON output. This keeps the proven harness intact and confines the new code to the UI layer.

### 1.1 Build philosophy: reuse, don't reinvent

The TUI ecosystem has matured around a small number of well-maintained components — Ink for React-style CLIs, Bubble Tea for Go, node-pty for PTY allocation, clack for prompts, chokidar for file watching. The recently shipped subscription-auth flows (OpenAI's [Codex CLI](https://github.com/openai/codex), the third-party [`ex-machina-co/opencode-anthropic-auth`](https://github.com/ex-machina-co/opencode-anthropic-auth) module that wraps Anthropic's `claude.ai/oauth` endpoint) give us a working blueprint for the trickiest part of the spec — **how to bill Claude Code subscription quota instead of API credits**.

`speca-cli` is therefore designed as an **integration project**, not a from-scratch TUI. We commit to:

- **Vendoring or depending on existing OAuth code** for Claude Code subscription auth (rather than re-implementing the unofficial OAuth flow).
- **Using Ink + clack + chokidar** verbatim for the TUI shell (no custom rendering loop).
- **Borrowing layout patterns from [opencode](https://github.com/sst/opencode) and [lazygit](https://github.com/jesseduffield/lazygit)** without forking either codebase.
- **Subprocess-and-stream-JSON the existing Python orchestrator** rather than porting it.

Concrete library choices and the per-file reuse map appear in [§9 Reference Implementations & Reuse Map](#9-reference-implementations--reuse-map).

> **Working name.** The npm package is `speca-cli`; the binary is `speca`. We use `speca-cli` throughout this doc to match the user-facing `npx speca-cli` invocation.

## 2. Goals & Non-Goals

### 2.1 Goals

| # | Goal | Rationale |
|---|---|---|
| G1 | A single `npx speca-cli` command runs the full pipeline end-to-end on a target repo | Removes the ~10-step setup gauntlet that limits adoption to insiders |
| G2 | Authentication uses the user's existing Claude Code subscription | Anthropic charges by API tokens for the API path but Claude Code subscribers already pay a flat rate; insisting on API keys blocks the largest user segment |
| G3 | Real-time visibility into per-worker progress, logs, and partial findings | Phase 03 can take 10+ min on large targets; a black box wait is unusable for iterative debugging |
| G4 | Interactive, low-cognitive-load configuration of `BUG_BOUNTY_SCOPE.json` / `TARGET_INFO.json` | Today these files are the most common reason a first-run fails; guided wizards remove that class of error |
| G5 | Built-in "ask Claude about this finding" chat tied to the user's session | Closes the loop from "the tool found something" to "I understand what to do about it" without context-switching |
| G6 | Cross-platform (macOS, Linux, WSL2) | Audit users live on all three |
| G7 | Graceful degradation if the user already has the Python venv / cloned repo / etc. | Power users should be able to opt out of any guided step |

### 2.2 Non-Goals

| # | Non-Goal | Rationale |
|---|---|---|
| N1 | A web UI or VSCode extension | TUI is sufficient for the audit-iteration use case and cheaper to maintain |
| N2 | Reimplementing the orchestrator in Node.js | The Python orchestrator is the published artifact; a parallel implementation doubles the maintenance surface |
| N3 | Hosting the SPECA pipeline as a SaaS | Pure local tool; user keeps their own audit data |
| N4 | Supporting non-Claude models for Phase 5/6 | Out of scope for v1; deferred until the upstream pipeline supports it |
| N5 | Automatic dependency installation of `uv` / `git` / `node` | Bootstrapping is a separate problem; surface clear error messages instead |

### 2.3 Success Criteria

A v1 release is considered successful if:

1. A new contributor can go from `npx speca-cli` to "I see the first finding from Phase 03" in **under 15 minutes** without reading the README.
2. **Zero hand-edited JSON** required for the common case (one target, one spec corpus, default trust model).
3. The CLI runs on macOS (Apple Silicon + Intel) and Ubuntu 22.04 LTS without additional setup beyond Node ≥ 20.
4. The "ask Claude" pane consumes the user's Claude Code subscription quota only — no Anthropic API key prompt anywhere.

## 3. User Stories

### 3.1 First-time auditor

> Alice is a security researcher who heard about SPECA at a conference. She has Claude Code installed for day-to-day coding. She wants to point SPECA at her favorite open-source consensus client and see what falls out.

**Flow:**
1. `npx speca-cli` → splash + license notice (MIT) → "Press any key to start"
2. **Auth check:** the CLI runs `claude auth status` under the hood; finds Alice already logged in. ✅ "Authenticated as alice@example.com via Claude Code subscription."
3. **Project wizard:**
   - "What are you auditing?" → text input → `lighthouse`
   - "Paste the GitHub URL of the target repo." → `https://github.com/sigp/lighthouse`
   - "Pin to a specific commit? (default: HEAD of default branch)" → press enter
   - "Paste one or more specification URLs (one per line, finish with Ctrl-D)." → EIP-7594 URL
   - "Bug-bounty scope. Use a guided template? (Y/n)" → Y → severity rubric template loaded
4. **Pipeline run:** TUI shows 6 phase rows. User presses `Enter` to start; phases progress one by one with a per-worker progress bar and live log tail in the right pane.
5. **Finding browser:** Phase 04 completes. TUI switches to a finding list (severity-coloured). Alice arrows through, picks a `CONFIRMED_VULNERABILITY`, and sees the proof trace + attack scenario.
6. **Ask Claude:** Alice presses `?` → a chat pane opens preloaded with the finding as context. She types "is this exploitable from a stranger over P2P?" and gets a Claude response in 3 seconds, billed against her Claude Code subscription.
7. **Export:** `Ctrl-S` writes a Markdown summary to the project directory.

### 3.2 Power user

> Bob runs SPECA in CI. He already has the Python orchestrator working. He wants the TUI just for live monitoring of CI runs, not for setup.

**Flow:**
1. `cd existing-speca-repo && npx speca-cli` (or `speca attach`)
2. CLI detects existing `outputs/` directory and offers: "Attach to running pipeline / Resume / Force re-run / Browse findings".
3. Bob picks "Attach"; the TUI streams live logs and partial results without re-prompting any setup.

### 3.3 Reviewer / triage user

> Carol is reviewing yesterday's SPECA run before pushing a PR. She needs to drill into specific findings.

**Flow:**
1. `npx speca-cli browse outputs/04_PARTIAL_*.json` (or `speca browse` from inside a project dir)
2. TUI opens directly on the finding browser — no pipeline run needed.
3. Carol filters to `severity:high`, picks one, presses `?` → chat with Claude grounded in the finding.

## 4. Authentication

### 4.1 Requirements

- **R1 — Claude Code subscription is the primary auth path.** The user must not be prompted for an Anthropic API key under normal flows. Subscription auth piggybacks on the [`claude auth login`](https://docs.claude.com/en/docs/claude-code) flow that the official Claude Code CLI already implements.
- **R2 — Read-only auth detection.** `speca-cli` does not store, transmit, or read the auth token contents directly. It only invokes the Claude Code CLI as a subprocess and lets that CLI handle credential management.
- **R3 — Fallback to API key.** Power users with `ANTHROPIC_API_KEY` exported can opt in via a CLI flag (`--auth=api-key`) — useful for CI or for users who do not subscribe to Claude Code.
- **R4 — No silent re-auth.** If subscription auth has expired, the CLI surfaces a clear prompt and runs `claude auth login` interactively (with the user's consent).

### 4.2 Detection algorithm

```
on startup:
  1. run `claude auth status` (a Claude Code CLI subcommand) and capture exit code
     - exit 0 + status == "authenticated"  → use subscription auth (preferred)
     - exit non-zero or status != authenticated → continue
  2. if env var ANTHROPIC_API_KEY is set                     → offer api-key fallback (display: "API key detected; use it? (y/N)")
  3. else                                                    → run `claude auth login` interactively
                                                                if it succeeds, retry step 1
                                                                if it fails or is cancelled, exit with a clear message
```

### 4.3 Surface in TUI

```
┌─ Authentication ─────────────────────────────────────────┐
│  ✔ Claude Code subscription detected                     │
│    Account: alice@example.com                             │
│    Method:  subscription (Claude Code CLI)                │
│                                                            │
│  [  Continue  ]   [ Switch to API key ]   [ Sign out ]    │
└────────────────────────────────────────────────────────────┘
```

If unauthenticated:

```
┌─ Authentication required ────────────────────────────────┐
│  No active Claude Code session was found.                 │
│                                                            │
│  • Press [L] to log in via subscription (recommended)     │
│  • Press [K] to use an Anthropic API key instead          │
│  • Press [Q] to quit                                      │
└────────────────────────────────────────────────────────────┘
```

When `[L]` is pressed, the paste-code flow (§4.5.1) runs:

```
┌─ Sign in via Claude Code subscription ───────────────────────────┐
│                                                                    │
│  We've opened the following URL in your browser:                  │
│                                                                    │
│    https://claude.ai/oauth/authorize?client_id=...&scope=...      │
│                                                                    │
│  After signing in, claude.ai will redirect you to a page that     │
│  shows a code. Copy the entire string and paste it below.         │
│                                                                    │
│  ➤ Paste code: _                                                   │
│                                                                    │
│  Trouble? Press [O] to re-open the URL, [K] to use an API key     │
│  instead, [Q] to quit.                                            │
└────────────────────────────────────────────────────────────────────┘
```

The input field accepts any of the three formats handled by `parseCallbackInput`: a full URL, the `code#state` hash form, or a `code=X&state=Y` query string.

### 4.4 Handing the auth context to Claude Code workers

The Python orchestrator already invokes the `claude` CLI per batch; it inherits the parent process' environment, so as long as `speca-cli` is running in a shell that has `claude auth login`'d, every worker subprocess uses the same subscription. **No bespoke token handling in `speca-cli` itself.**

### 4.5 Concrete OAuth implementation (vendored)

When the user has *not* yet logged into Claude Code, `speca-cli` needs to drive the OAuth flow itself rather than punt to `claude auth login` (which assumes Claude Code is already installed — a circular dependency for first-run users via `npx`).

We **vendor** the working PKCE OAuth implementation from [`ex-machina-co/opencode-anthropic-auth`](https://github.com/ex-machina-co/opencode-anthropic-auth) (MIT). Specifically:

- The PKCE generator ([`src/pkce.ts`](https://github.com/ex-machina-co/opencode-anthropic-auth/blob/main/src/pkce.ts)) — 64 bytes random → SHA-256 challenge using the `crypto.subtle` Web Crypto API; no Node-specific deps.
- The `authorize()` + `exchange()` pair ([`src/auth.ts`](https://github.com/ex-machina-co/opencode-anthropic-auth/blob/main/src/auth.ts)).
- The endpoint constants ([`src/constants.ts`](https://github.com/ex-machina-co/opencode-anthropic-auth/blob/main/src/constants.ts)) — see §4.5.2 below for the magic scope.

#### 4.5.1 The flow is **paste-code**, not loopback

> ⚠️ Earlier drafts of this spec described a loopback server (à la OpenAI's Codex CLI). **That is not how Anthropic's OAuth works** — verified against the upstream constants on 2026-05-03.

Anthropic's authorize endpoint **hard-codes** the redirect URI:

```typescript
// from constants.ts
export const CODE_CALLBACK_URL = 'https://platform.claude.com/oauth/code/callback'
```

`http://localhost:<port>` is **not** an acceptable `redirect_uri` value — Anthropic's auth server validates against this exact constant and rejects anything else. Consequently `speca-cli` cannot run a local callback server like Codex's. The flow is:

```
┌──────────────┐       ┌─────────────┐         ┌────────────────────┐         ┌──────────────────┐
│  speca-cli   │──(1)─▶│  user's     │───(2)──▶│  claude.ai/oauth/  │───(3)──▶│ platform.claude  │
│              │ open  │  browser    │  login  │  authorize         │ redirect│ .com/oauth/code/ │
│              │ URL   │             │         │  (max | console)   │         │ callback         │
└──────┬───────┘       └─────────────┘         └────────────────────┘         └────────┬─────────┘
       │                                                                                │
       │                            (5) user copies the displayed                       │ (4) page
       │◀───────────────  "<authorization_code>#<state>"  ◀─────────────────────────────┘ shows
       │                                                                                  the
       │ (6) POST platform.claude.com/v1/oauth/token                                     code+state
       │     { code, state, code_verifier, client_id, redirect_uri,                       string
       │       grant_type: "authorization_code" }
       ▼
   { access_token, refresh_token, expires_in }
```

In TUI terms: we print a clickable URL, open it via [`open`](https://github.com/sindresorhus/open), and then prompt the user to **paste the code string**. The `parseCallbackInput` helper accepts three formats (full URL with query params, `code#state` hash form, or `code=X&state=Y` URL-encoded form) so the user can paste whatever is most convenient.

#### 4.5.2 The magic scope: `user:sessions:claude_code`

This is the line in the request that decides who pays:

```typescript
export const OAUTH_SCOPES = [
  'org:create_api_key',
  'user:profile',
  'user:inference',
  'user:sessions:claude_code',  // ← bills against Claude Code subscription, not Pro web
  'user:mcp_servers',
  'user:file_upload',
]
```

Without that exact scope string in the authorize request, the issued token is rejected for inference calls (or, worse silently, billed against the user's web-only Pro entitlement which has no API quota). **`speca doctor` MUST verify the scope is present in the access token before declaring auth healthy.**

The two authorize URLs select which entitlement source Anthropic queries:

| `mode` | URL | Entitlement source | Used when |
|---|---|---|---|
| `max` | `https://claude.ai/oauth/authorize` | Claude Pro / Max subscription | **Default for `speca-cli`** |
| `console` | `https://platform.claude.com/oauth/authorize` | console.anthropic.com (creates a new API key) | User without a subscription, opt-in path |

#### 4.5.3 Header impersonation when calling `/v1/messages`

The OAuth flow above only gives us a token. When `speca-cli` (or the Python orchestrator's `claude` subprocess) actually calls Anthropic's inference API, **two more impersonation steps** are required, both encoded in the upstream constants:

```typescript
export const USER_AGENT = 'claude-cli/2.1.87 (external, cli)'
export const REQUIRED_BETAS = ['oauth-2025-04-20', 'interleaved-thinking-2025-05-14']
```

Concretely, every request must carry:

| Header | Value | Purpose |
|---|---|---|
| `Authorization` | `Bearer <access_token>` | Standard OAuth |
| `User-Agent` | `claude-cli/2.1.87 (external, cli)` | Anthropic blocks unknown UAs from subscription endpoints; we present as the official Claude Code CLI |
| `anthropic-beta` | `oauth-2025-04-20,interleaved-thinking-2025-05-14` | OAuth itself is a beta feature; without these the call is rejected |
| `anthropic-version` | (whatever the upstream pins) | Standard |

Note also the curiosity that `auth.ts` itself sends `User-Agent: axios/1.13.6` to the OAuth token endpoint — purely a fingerprint workaround for the same UA filter applied at `platform.claude.com`. We replicate this in our vendored copy.

> **Why so much fingerprint-matching?** Anthropic has not officially opened subscription auth to third-party tools; it is treated as a Claude-Code-internal mechanism. Tools that want to use it (this one, OpenCode, Crush, etc.) impersonate the official CLI. This works today and has been stable since Claude Code 2.x but is **inherently fragile** — Anthropic could detect and block it at any time. Always ship the API-key fallback (§4.2 step 2 / §10.4).

#### 4.5.4 Token storage layout

Modelled on [`sst/opencode`'s `auth/index.ts`](https://github.com/sst/opencode/blob/dev/packages/opencode/src/auth/index.ts) (pattern only — we drop their Effect.ts dependency):

```
~/.config/speca/auth.json    (chmod 0o600, written atomically via tmp+rename)
{
  "anthropic": {
    "type":    "oauth",
    "access":  "<token>",
    "refresh": "<token>",
    "expires": 1715678400123,   // ms since epoch
    "scope":   "org:create_api_key user:profile ... user:sessions:claude_code ..."
  }
}
```

When `speca-cli` spawns the Python orchestrator subprocess (which spawns `claude` per batch), it injects:
- `ANTHROPIC_API_KEY=__OAUTH_DUMMY_KEY__` — sentinel that signals the workers "we're using OAuth; pull the real token from this other env var".
- `SPECA_OAUTH_TOKEN=<access_token>` — the actual bearer token (lives only in the env, never on disk in the worker tree).
- `SPECA_OAUTH_BETAS=oauth-2025-04-20,interleaved-thinking-2025-05-14` — passed as `anthropic-beta` by the worker.

A small wrapper around the worker's HTTP client substitutes the real token in for the dummy when the dummy is detected. Standard pattern; same approach used in OpenCode.

#### 4.5.5 Stability caveat

Anthropic has not officially published the Claude Code OAuth specification. The endpoint URLs, the scope name, the User-Agent string, the beta-flag set, and the redirect URI are all reverse-engineered from the official `claude` CLI's network traffic and from the third-party packages cited above. They have been stable since Claude Code 2.x launched but **could change without notice**. Mitigation:

- All auth constants live in a single file (`src/auth/constants.ts`) so a hotfix release can ship by editing one place.
- Always fall back to API-key auth if OAuth fails — prompt the user with a clear "OAuth flow failed; paste your `ANTHROPIC_API_KEY`" path.
- Surface the upstream pinned version of `ex-machina-co/opencode-anthropic-auth` (which we vendor) in `speca doctor` so debugging upstream changes is one command away.
- Add a CI smoke test that runs the OAuth flow weekly against a test account; if it breaks, we get paged before users do.

## 5. TUI Architecture & Screens

`speca-cli` follows the modal layout patterns popularised by [opencode](https://github.com/opencodeagent/opencode), [lazygit](https://github.com/jesseduffield/lazygit), and [k9s](https://github.com/derailed/k9s):

- A persistent **header** (current project, phase status, auth state).
- A **main pane** that swaps between modes (Setup / Run / Browse / Chat).
- A persistent **side pane** (right or bottom) for live logs.
- A **status bar** at the bottom showing keybindings.

### 5.1 Screen 1 — Welcome / project picker

Shown if the CLI is launched with no project context.

```
┌─ SPECA — Specification-to-Checklist Auditing ───────────────────────┐
│                                                                       │
│   Recent projects:                                                    │
│     ▸ ~/audits/lighthouse-fusaka      (last run 2 days ago)          │
│       ~/audits/grandine-fusaka        (last run 1 week ago)           │
│                                                                       │
│   [N]ew project   [O]pen by path   [B]rowse-only   [?] Help   [Q]uit │
└───────────────────────────────────────────────────────────────────────┘
```

A **project** is a directory containing `outputs/TARGET_INFO.json`, `outputs/BUG_BOUNTY_SCOPE.json`, and the cached `outputs/*_PARTIAL_*.json` from previous runs. Opening a project dir directly skips this screen.

### 5.2 Screen 2 — New project wizard

A multi-step form, one question per page. Required fields are validated before advancing.

| Step | Prompt | Field | Validation |
|---|---|---|---|
| 1 | Project name | text | non-empty, filename-safe |
| 2 | Target git URL | URL | resolves via `git ls-remote` |
| 3 | Pin commit? | text or "default" | optional; verified via `git fetch` |
| 4 | Specification source(s) | multi-line URLs | each must respond 200 |
| 5 | Bug-bounty scope | template / paste / skip | see §7.2 |
| 6 | Audit budget | dollar cap | numeric, positive; default $10 for v1 |

The wizard writes `outputs/TARGET_INFO.json` and `outputs/BUG_BOUNTY_SCOPE.json` (see §7) and lands on Screen 3.

### 5.3 Screen 3 — Pipeline dashboard (the main TUI screen)

```
┌─ lighthouse-fusaka ────────  alice@example.com (subscription) ──────────┐
│ Phase   Name                       Status        Progress    Findings    │
│  01a    Spec Discovery             ✔ done        28 specs    —           │
│  01b    Subgraph Extraction        ✔ done        41 graphs   —           │
│  01e    Property Generation        ⠋ running     34/47       —           │
│  02c    Code Pre-resolution        ◌ pending     —           —           │
│  03     Audit Map                  ◌ pending     —           —           │
│  04     Audit Review               ◌ pending     —           —           │
├──────────────────────────────────────────────────────────────────────────┤
│ Live log (right pane)                                                    │
│   [01e/W2] worker 2 batch 5: generated 4 properties (cumulative: 134)    │
│   [01e/W0] worker 0 batch 5: generated 2 properties (cumulative: 132)    │
│   [01e/W1] worker 1 batch 5: BudgetTrack: spent $0.42 / $10.00            │
│   …                                                                      │
├──────────────────────────────────────────────────────────────────────────┤
│ [Enter] run / pause   [F] force re-run   [L] full log   [B] browse       │
│ [?] ask Claude         [Q] quit                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

#### 5.3.1 Per-phase row

Each row supports the keybindings:
- `Enter` — start the phase (queues work, dispatches workers).
- `s` — skip this phase (mark as done, do not run).
- `f` — force re-run, clearing resume state.
- `l` — open the full log for this phase in a fullscreen pager.

#### 5.3.2 Live log pane

A right-pane (or bottom on narrow terminals) that tails `outputs/logs/<phase>_*.jsonl` files. Lines are de-duplicated by event id and **colour-coded by severity** (info/warn/err) and worker id.

#### 5.3.3 Budget gauge

The bottom-of-pane status bar shows `spent / cap` updated from the runner's `CostTracker`. When 80% of the cap is reached, the bar turns yellow; at 100% the runner halts (existing behaviour) and the TUI shows a modal asking whether to bump the cap or abort.

### 5.4 Screen 4 — Finding browser

Triggered by `[B]` from the dashboard, or automatically when Phase 04 completes.

```
┌─ Findings (lighthouse-fusaka) ──────────────────────  72 total · 24 FP ─┐
│ Severity  Verdict                Property                    Loc       │
│ ▸ HIGH    CONFIRMED_VULN         PROP-6a4369e9-inv-042       data_co… │
│   HIGH    DOWNGRADED → MED       PROP-57888860-inv-006       reconst… │
│   MED     CONFIRMED_POTENTIAL    PROP-6a4369e9-pre-009       codec.r… │
│   …                                                                    │
├────────────────────────────────────────────────────────────────────────┤
│ Detail (selected finding)                                              │
│   Property:  PROP-6a4369e9-inv-042  (severity: HIGH)                   │
│   Verdict:   CONFIRMED_VULNERABILITY                                    │
│                                                                         │
│   Proof trace                                                           │
│     The cache key omits KzgCommitments (the data being proven), …      │
│                                                                         │
│   Attack scenario                                                       │
│     Attacker sends valid DataColumnSidecar A, then sends forged…       │
│                                                                         │
│   Code path                                                             │
│     beacon-chain/verification/data_column.go::inclusionProofKey :527-547│
├────────────────────────────────────────────────────────────────────────┤
│ [/] filter   [s] sort   [c] code-view   [?] ask Claude   [B] back     │
└────────────────────────────────────────────────────────────────────────┘
```

#### 5.4.1 Filter language

Filter input at `/` accepts a small DSL:

| Filter | Examples |
|---|---|
| `severity:` | `severity:high`, `severity:high|critical` |
| `verdict:` | `verdict:CONFIRMED_VULNERABILITY` |
| `prop:` | `prop:PROP-6a4*`, `prop:*-inv-042` |
| `repo:` | `repo:lighthouse_fusaka` (RQ1-style multi-target only) |
| free text | matches against `proof_trace` + `attack_scenario` |

Combine with space (AND): `severity:high verdict:CONFIRMED_VULNERABILITY p256verify`.

### 5.5 Screen 5 — Ask Claude (chat pane)

Triggered by `?` from any context. The pane opens with **the current selection as system context** so Claude sees the finding the user is asking about.

```
┌─ Ask Claude ─────────────  about: PROP-6a4369e9-inv-042 (HIGH) ────────┐
│  Claude                                                                 │
│  Yes, this is exploitable from a stranger over P2P. The                 │
│  DataColumnSidecar message is gossiped over the column-sidecar topic    │
│  with no peer-trust scoping; an attacker who can connect to the         │
│  validator's libp2p mesh can submit the second sidecar.                 │
│                                                                         │
│  > is this exploitable from a stranger over P2P?                        │
│  ─────────────────────────────────────────────────────────────────────  │
│  > _                                                                    │
├─────────────────────────────────────────────────────────────────────────┤
│ [Enter] send   [Ctrl-J] newline   [Ctrl-R] new turn   [Esc] close      │
└─────────────────────────────────────────────────────────────────────────┘
```

Implementation: each turn invokes `claude -p "<prompt>" --output-format=stream-json --resume <session-id>`, where `<session-id>` is the Claude Code session bound to the project. This:

- Reuses the user's subscription quota (no API token).
- Keeps multi-turn context across invocations.
- Streams partial output back to the TUI as it arrives.

System context is injected as a leading user-role message containing the JSON of the selected finding plus the relevant log/output snippets. Token budget is capped at 50 KB by default to avoid blowing the Claude Code context window.

## 6. Command Surface

`speca` supports both an **interactive TUI** (default) and **subcommands** for scripting:

```
speca                          # Open TUI on the current directory (or welcome screen)
speca run [--phase=<id>]       # Headless: run pipeline, stream JSON events to stdout
speca browse [path-glob]       # TUI: jump straight to the finding browser
speca attach                   # TUI: read-only attach to a running pipeline in cwd
speca auth status              # Print auth state (subscription / api-key / none)
speca auth login               # Pass-through to `claude auth login`
speca init                     # Run only the new-project wizard (no pipeline run)
speca config get|set <key>     # Read / write a single key in BUG_BOUNTY_SCOPE.json
speca doctor                   # Check Node/uv/git/claude-code versions; print diagnostics
speca version
speca help [command]
```

Common flags (apply to every subcommand):

| Flag | Description | Default |
|---|---|---|
| `--project, -C <dir>` | Project directory (the one containing `outputs/`) | `cwd` |
| `--auth=<mode>` | `auto` / `subscription` / `api-key` | `auto` |
| `--workers <n>` | Worker concurrency | inherited from PhaseConfig |
| `--max-concurrent <n>` | Max concurrent Claude executions | inherited from PhaseConfig |
| `--budget <usd>` | Cost cap | inherited from PhaseConfig |
| `--no-tui` | Force plain-text output (for CI) | `false` |
| `--json` | Emit machine-readable events on stdout (implies `--no-tui`) | `false` |
| `--verbose, -v` | Bump log level | `info` |
| `--quiet, -q` | Reduce log level | — |

## 7. Configuration

### 7.1 Project layout (managed by speca-cli)

```
my-audit/
├── .speca/
│   ├── session.json          # remembered Claude session id, last cmd, last tab
│   └── prefs.json            # TUI prefs (theme, key bindings overrides)
├── outputs/                  # standard SPECA layout — unchanged
│   ├── TARGET_INFO.json
│   ├── BUG_BOUNTY_SCOPE.json
│   ├── 01a_STATE.json
│   ├── 01b_PARTIAL_*.json
│   ├── 01e_PARTIAL_*.json
│   ├── 02c_PARTIAL_*.json
│   ├── 03_PARTIAL_*.json
│   ├── 04_PARTIAL_*.json
│   └── logs/
│       └── <phase>_W<n>B<m>_<ts>.jsonl
└── target_workspace/         # SPECA auto-clones the target repo here
```

Everything under `.speca/` is `.gitignore`-recommended; everything under `outputs/` is the existing SPECA contract.

### 7.2 `BUG_BOUNTY_SCOPE.json` wizard

The wizard collects information into a structured JSON. Three modes:

1. **Template** — pick from a small library (`ethereum-consensus`, `solana-validator`, `evm-defi`, `c-cpp-repo-audit`, `generic`). Each template ships predefined `severity_classification` and `trust_assumptions`.
2. **Paste** — drop in an existing JSON file; the wizard validates it against the [Pydantic schema in `scripts/orchestrator/schemas.py`](../scripts/orchestrator/schemas.py).
3. **Skip** — emits a placeholder file with severity classification only; the user must edit it before Phase 01e runs (and the orchestrator will fail loudly if it is malformed — existing behaviour).

### 7.3 `TARGET_INFO.json` wizard

```json
{
  "name":     "lighthouse",
  "repo":     "https://github.com/sigp/lighthouse",
  "commit":   "b8178515c…",
  "language": "rust"
}
```

The CLI auto-fills `commit` from `git ls-remote --heads <repo> | head -1` and `language` from a primary-language probe (`detect-language` heuristic on a shallow clone).

### 7.4 User-level config (`~/.config/speca/config.toml`)

| Key | Type | Default | Purpose |
|---|---|---|---|
| `auth.mode` | string | `auto` | `auto` / `subscription` / `api-key` |
| `tui.theme` | string | `dark` | `dark` / `light` / `solarized` |
| `tui.shortcuts.<action>` | string | varies | rebind keys |
| `runner.workers` | int | 4 | default worker concurrency |
| `runner.max_concurrent` | int | 8 | default Claude concurrency |
| `runner.budget_usd` | float | 10.0 | default per-run cost cap |
| `runner.python_bin` | string | `auto` | path to `uv` or `python` (auto: search `uv` then `python3`) |

## 8. Architecture

### 8.1 Component diagram

```
┌─────────────────────────────────────────────────────────────┐
│  speca-cli (Node.js, distributed via npm / npx)             │
│  ┌───────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Ink TUI layer │  │ project mgr  │  │  config mgr  │      │
│  └───────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│          │                 │                 │              │
│          ▼                 ▼                 ▼              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  process bridge  (node-pty + JSONL stream parser)     │  │
│  └─────────┬───────────────────────┬─────────────────────┘  │
│            │                       │                        │
│  ┌─────────▼─────────┐    ┌────────▼────────┐               │
│  │ Python orchestrator│    │ Claude Code CLI │               │
│  │  (uv-managed)      │    │  (subscription) │               │
│  └────────────────────┘    └─────────────────┘               │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 Layer responsibilities

| Layer | Responsibility | Lang |
|---|---|---|
| **Ink TUI layer** | Render screens, handle keybindings, manage modal state | TypeScript + [Ink](https://github.com/vadimdemedes/ink) |
| **project manager** | Detect / open / create project directories; resume prior runs | TypeScript |
| **config manager** | Read & validate `TARGET_INFO.json` / `BUG_BOUNTY_SCOPE.json` against the published Pydantic schemas (re-emitted as JSON Schema) | TypeScript |
| **process bridge** | Spawn `uv run python3 scripts/run_phase.py …` with PTY allocation, parse `--stream-json` events into typed messages, multiplex into TUI state | TypeScript + [`node-pty`](https://github.com/microsoft/node-pty) |
| **Python orchestrator** | Unchanged from current repo — the source of truth for SPECA execution | Python (existing) |
| **Claude Code CLI** | Auth + per-batch worker invocation + subscription token handling | Provided by Anthropic |

### 8.3 Recommended stack

Concrete library choices. Rationale for each appears in [§9 Reference Implementations & Reuse Map](#9-reference-implementations--reuse-map).

| Concern | Choice | Why this one | License |
|---|---|---|---|
| TUI framework | **[Ink 7.0.1](https://github.com/vadimdemedes/ink)** | React-for-CLI; battle-tested by Vercel/Wrangler/Astro/Gatsby; native `npx` distribution | MIT |
| Wizard prompts | **[@clack/prompts 1.3.0](https://github.com/bombshell-dev/clack)** | Cleaner ergonomics than Inquirer; actively maintained under bombshell-dev | MIT |
| Subprocess + PTY | **[node-pty 1.1.0](https://github.com/microsoft/node-pty)** when a real TTY is needed; `child_process.spawn` for the orchestrator subprocess | node-pty is the de-facto standard but has no prebuilt binaries (see pitfalls in §9.3) | MIT |
| Live log tail | **[chokidar 5.0.0](https://github.com/paulmillr/chokidar)** | The standard Node fs watcher (used by webpack/vite/nodemon) | MIT |
| Schema validation | **[zod](https://github.com/colinhacks/zod) 3.x** | Runtime validation of stream-JSON events and config files | MIT |
| Claude Code subscription auth | Vendor **[`ex-machina-co/opencode-anthropic-auth`](https://github.com/ex-machina-co/opencode-anthropic-auth)** | Working PKCE OAuth against Anthropic's `claude.ai/oauth` endpoints with the `user:sessions:claude_code` scope (§4.5) | MIT |

Stack alternatives explicitly rejected:

| Option | Verdict |
|---|---|
| **[Bubble Tea](https://github.com/charmbracelet/bubbletea)** + bubbles + lipgloss (Go) | Excellent ergonomics but breaks `npx` distribution — Go binaries cannot be `npx`-launched without precompiling per platform (see [plandex's `install.sh`](https://github.com/plandex-ai/plandex/blob/main/app/cli/install.sh) for a sense of the multi-arch shipping burden) |
| **[Charm Crush](https://github.com/charmbracelet/crush)** | Best-in-class chat TUI patterns, but licensed under [FSL-1.1-MIT](https://github.com/charmbracelet/crush/blob/main/LICENSE.md) (Functional Source License — 2-year delay before MIT applies). Not pure permissive; we cannot vendor or fork freely |
| **[OpenTUI](https://github.com/anomalyco/opentui)** (`@opentui/core` 0.2.2) | What [opencode](https://github.com/sst/opencode) recently pivoted to (Solid-based `.tsx` for terminal UI). MIT and modern but young (v0.2.2, May 2026) and tied to Bun runtime — Ink is the safer bet for a `npx`-friendly Node.js distribution |
| **[blessed](https://github.com/chjj/blessed)** raw | More flexible, but the imperative API balloons LoC for the layouts in §5 |
| **prompts / inquirer only** | Insufficient — we need persistent panes and live log streaming, not just one-shot prompts |
| Web UI (Electron / browser) | Violates G6 and N1; heavyweight for an audit harness |

### 8.4 Stream-JSON contract

The Python orchestrator (specifically `scripts/orchestrator/runner.py`) already invokes `claude --stream-json` per batch and writes one event per line to `outputs/logs/<phase>_W<n>B<m>_<ts>.jsonl`. `speca-cli` parses these via two paths:

1. **Live tail** — a `chokidar` watcher on `outputs/logs/*.jsonl` reads new lines as they appear. Each line is a JSON object with at least `{type, phase, worker, batch, ts, payload}`. Unknown event types are surfaced with a warning but do not crash the TUI.
2. **Process stdout** — the launched `run_phase.py` subprocess emits a higher-level event stream on stdout (one JSON object per line) describing pipeline-level transitions: `phase-started`, `phase-completed`, `phase-failed`, `budget-exceeded`, `circuit-breaker-tripped`. This stream drives the dashboard rows in §5.3. *(This requires a tiny addition to `scripts/run_phase.py` — a `--json` flag — see §11.)*

Both streams are typed in TypeScript with [Zod](https://github.com/colinhacks/zod) for runtime validation.

### 8.5 "Ask Claude" implementation

```
function askClaude(question: string, context: Finding | LogLine): Promise<AsyncIterable<string>> {
  const sessionId = projectSession.claudeSessionId ?? newSession();
  const prompt = renderPromptTemplate({ question, context });
  return spawnClaudeStream({
    args: ["-p", prompt, "--output-format", "stream-json",
           "--resume", sessionId],
    inheritEnv: true,             // subscription auth comes from parent shell
  });
}
```

- Each call appends to the same Claude Code session, preserving multi-turn context.
- `inheritEnv: true` ensures the subscription token is in scope.
- The streamed response goes directly to the chat pane without buffering, so the TUI feels responsive.

### 8.6 Non-TTY mode

When `process.stdout.isTTY === false` or `--no-tui` is passed, the CLI degrades to:

- **Setup wizards** become non-interactive errors instructing the user to write JSON files manually (with a one-line example).
- **Pipeline dashboard** is replaced by a plain-text progress reporter (one line per phase transition).
- **Finding browser** becomes a flat JSON dump on stdout.
- **Ask Claude** is unavailable.

This is the mode used by CI and by `--json` consumers.

## 9. Reference Implementations & Reuse Map

This section catalogs the OSS implementations whose patterns or code we lean on, with direct links so future maintainers can re-verify each citation. The choices in §8.3 follow from this analysis.

### 9.1 Reference projects (what they teach us)

| Project | Stack | Lesson for `speca-cli` | License |
|---|---|---|---|
| **[sst/opencode](https://github.com/sst/opencode)** ([npm](https://www.npmjs.com/package/opencode-ai)) | TypeScript / [OpenTUI](https://github.com/anomalyco/opentui) (Solid) on Bun; ships per-platform binary via npm | Token-store layout ([`auth/index.ts`](https://github.com/sst/opencode/blob/dev/packages/opencode/src/auth/index.ts)): `auth.json` at `0o600`, `OAUTH_DUMMY_KEY` sentinel for env injection, refresh/access/expires schema. Pane and dialog layout patterns ([`packages/opencode/src/cli/cmd/tui/component/dialog-*.tsx`](https://github.com/sst/opencode/tree/dev/packages/opencode/src/cli/cmd/tui/component)) translate directly to Ink components. **Note:** OpenCode's own Anthropic OAuth lives in third-party plugins, not core ([`provider/auth.ts`](https://github.com/sst/opencode/blob/dev/packages/opencode/src/provider/auth.ts) is generic). | MIT |
| **[openai/codex](https://github.com/openai/codex)** | Rust / [`codex-rs/login`](https://github.com/openai/codex/tree/main/codex-rs/login) | Architecture for the **loopback OAuth callback server** ([`server.rs`](https://github.com/openai/codex/blob/main/codex-rs/login/src/server.rs)): port-conflict fallback (1455 → 1456 → 1457), state validation, deep-link redirect on completion. Module layout (`auth/`, `device_code_auth`, `pkce`, `token_data`) is what we mirror. **Reusable:** topology only. **Not reusable:** issuer constants (`auth.openai.com` is ChatGPT-specific). | Apache-2.0 |
| **[ex-machina-co/opencode-anthropic-auth](https://github.com/ex-machina-co/opencode-anthropic-auth)** | TypeScript | The working PKCE OAuth flow against Anthropic's `claude.ai/oauth/authorize` (Pro/Max) and `platform.claude.com/v1/oauth/token` endpoints. **Most importantly:** the `user:sessions:claude_code` scope and `CLIENT_ID = '9d1c250a-…'` constants ([`src/constants.ts`](https://github.com/ex-machina-co/opencode-anthropic-auth/blob/main/src/constants.ts)). **We vendor `auth.ts`, `pkce.ts`, and `constants.ts` verbatim.** | MIT |
| **[charmbracelet/crush](https://github.com/charmbracelet/crush)** | Go / Bubble Tea | Chat-pane layout, syntax-highlighted message rendering, scrollback handling. Patterns only — we cannot lift code due to FSL-1.1-MIT licensing. | FSL-1.1-MIT |
| **[Aider-AI/aider](https://github.com/Aider-AI/aider)** | Python / `prompt_toolkit` + `rich` ([`io.py`](https://github.com/Aider-AI/aider/blob/main/aider/io.py)) | Confirms a **prompt-loop** is insufficient for our use-case (multi-pane dashboard). Aider's repo-mapping ideas inspire `speca attach`'s discovery of existing project state. | Apache-2.0 |
| **[plandex-ai/plandex](https://github.com/plandex-ai/plandex)** | Go binary distributed via `goreleaser` + [`install.sh`](https://github.com/plandex-ai/plandex/blob/main/app/cli/install.sh) | Concrete reference for the multi-arch shipping burden if we ever pivot to Go. The current spec rejects this path. | MIT |
| **[block/goose](https://github.com/block/goose)** | Rust | Plugin system as a long-term reference if `speca-cli` grows custom analysis plugins (deferred to v1.x). | Apache-2.0 |
| **[vadimdemedes/ink](https://github.com/vadimdemedes/ink)** ecosystem | TypeScript | The chosen TUI runtime. Used in production by Vercel CLI, Cloudflare Wrangler, Astro, Gatsby. Companion packages: `ink-spinner`, `ink-table`, `ink-select-input`, `ink-text-input`, `ink-testing-library`. | MIT |
| **[bombshell-dev/clack](https://github.com/bombshell-dev/clack)** | TypeScript | Wizard prompts (§5.2). The original `natemoo-re/clack` repo migrated to bombshell-dev; the latter is the actively maintained fork. | MIT |
| **[microsoft/node-pty](https://github.com/microsoft/node-pty)** | C++ + Node bindings | Real PTY allocation for any subprocess that itself runs a TUI (e.g., the embedded `claude` chat session). | MIT |
| **[paulmillr/chokidar](https://github.com/paulmillr/chokidar)** | TypeScript | The right answer for tailing `outputs/logs/*.jsonl` across macOS/Linux/WSL2. | MIT |

### 9.2 File-level reuse map (what we actually lift)

| Lift from (upstream) | Into `speca-cli` | Notes |
|---|---|---|
| [`ex-machina-co/opencode-anthropic-auth/src/auth.ts`](https://github.com/ex-machina-co/opencode-anthropic-auth/blob/main/src/auth.ts) | `src/auth/anthropic-oauth.ts` | `authorize()` + `exchange()` — full PKCE flow with state validation |
| [`.../src/pkce.ts`](https://github.com/ex-machina-co/opencode-anthropic-auth/blob/main/src/pkce.ts) | `src/auth/pkce.ts` | `generatePKCE()` — verbatim |
| [`.../src/constants.ts`](https://github.com/ex-machina-co/opencode-anthropic-auth/blob/main/src/constants.ts) | `src/auth/constants.ts` | `CLIENT_ID`, `AUTHORIZE_URLS.{max,console}`, `TOKEN_URL`, scope `user:sessions:claude_code` — **the subscription magic** |
| [`sst/opencode/packages/opencode/src/auth/index.ts`](https://github.com/sst/opencode/blob/dev/packages/opencode/src/auth/index.ts) | `src/auth/store.ts` | Pattern only (drop Effect.ts). `~/.config/speca/auth.json` at `0o600`; `OAUTH_DUMMY_KEY` sentinel for env-injection signalling |
| [`openai/codex/codex-rs/login/src/lib.rs`](https://github.com/openai/codex/blob/main/codex-rs/login/src/lib.rs) | n/a | Module-layout reference (`auth/`, `pkce`, `token_data`) — note: Codex's loopback server (`server.rs`) is **not applicable** to Anthropic, see §9.3 #4 |

For everything outside the auth flow we **depend on packages, not vendor source files** — `ink`, `@clack/prompts`, `chokidar`, `zod`, `node-pty`, `execa` are added as regular dependencies.

### 9.3 Pitfalls (drawn from the references above)

These are concrete failure modes encountered by the upstream projects — we encode them here so future maintainers do not re-discover them.

1. **Bubble Tea ≠ npx.** Crush, Plandex, and the deprecated Bubble Tea version of OpenCode all ship as Go binaries via `goreleaser` + `install.sh` (e.g. [plandex install.sh](https://github.com/plandex-ai/plandex/blob/main/app/cli/install.sh)) or via `brew`/`go install`. None of them work with bare `npx`. **Decision:** stay on Node.js + Ink; revisit Go only if Ink hits a hard scalability wall.
2. **`node-pty` has no prebuilt binaries.** As of v1.1.0 its [`package.json`](https://github.com/microsoft/node-pty/blob/main/package.json) does `node scripts/prebuild.js || node-gyp rebuild` at install — meaning users without a C++ toolchain see install failures via `npx`. **Mitigation:** prefer plain `child_process.spawn` for the Python orchestrator (it's not a TTY-aware app); only use `node-pty` when wrapping the embedded `claude` chat session, and ship a `postinstall` hook that downgrades a node-pty install failure to a runtime warning ("Ask Claude pane unavailable on this platform — install build-essentials and reinstall").
3. **OpenCode pivoted to OpenTUI; their Bubble Tea TUI is deprecated.** Their TUI now lives in [`packages/opencode/src/cli/cmd/tui/*.tsx`](https://github.com/sst/opencode/tree/dev/packages/opencode/src/cli/cmd/tui) using `@opentui/core` + `@opentui/solid`. Layout patterns translate to Ink, but the original Go TUI is no longer a moving reference.
4. **Anthropic forbids loopback `redirect_uri` — paste-code flow only.** This corrects an earlier draft of this spec. The redirect URI is hard-coded to `https://platform.claude.com/oauth/code/callback` in [`constants.ts`](https://github.com/ex-machina-co/opencode-anthropic-auth/blob/main/src/constants.ts) and Anthropic's authorize endpoint validates against that exact constant. `http://localhost:1455` is rejected. Codex's [`server.rs`](https://github.com/openai/codex/blob/main/codex-rs/login/src/server.rs) loopback architecture only works because OpenAI runs their own auth server with loopback URIs registered. **Implications for `speca-cli`:** we **do not** spawn a local HTTP server; we open the browser, then prompt the user to paste the code (§4.5.1). Less elegant UX, but the only option.
5. **`user:sessions:claude_code` is the magic scope.** Without that exact scope string in the OAuth `authorize` request, the issued token is billed against the user's Claude.ai web entitlement (or rejected entirely), not against the Claude Code subscription. **Always assert** the scope is present in the access token before declaring auth healthy (§4.5.2).
6. **Subscription auth requires impersonating the official `claude` CLI's HTTP fingerprint.** Every call to `/v1/messages` must carry `User-Agent: claude-cli/<version> (external, cli)` and `anthropic-beta: oauth-2025-04-20,interleaved-thinking-2025-05-14`. Without these, Anthropic rejects subscription-token requests. The OAuth token-exchange call itself uses `User-Agent: axios/1.13.6` for the same UA-filter reason. **All five strings (UA, betas, scope, redirect_uri, client_id) live in one constants file** so a hotfix release is a one-line change (§4.5.3).
7. **Codex's flow is ChatGPT-only.** Borrow Codex's module *layout* (`auth/`, `pkce`, `token_data`), **not** its constants — `auth.openai.com`, the `client_id`, the scopes, and the loopback URIs are all OpenAI-specific.
8. **OpenCode's Anthropic OAuth lives in plugins, not core.** [`packages/opencode/src/provider/auth.ts`](https://github.com/sst/opencode/blob/dev/packages/opencode/src/provider/auth.ts) is provider-agnostic; the Claude-specific endpoints only exist in third-party plugins like `ex-machina-co/opencode-anthropic-auth`. Anthropic has not published the OAuth spec, so treat all constants as unstable and ship the API-key fallback (§4.5.5).
9. **OpenCode-style npm distribution proven, but heavy.** [`opencode-ai`](https://www.npmjs.com/package/opencode-ai) ships a Bun-compiled binary per platform inside the npm tarball (~30 MB unpacked). For pure Node.js + Ink, `npx speca-cli` works without prebuild — keep it that way.

> All upstream metadata in this section was last verified on **2026-05-03**. Any maintainer modifying this section should re-confirm via `gh repo view <owner>/<repo>` and update the date stamp.

## 10. Implementation Notes

### 10.1 Distribution

- **Package**: `speca-cli` on npm.
- **Binaries**: `speca` (primary). Optional alias `speca-cli` for explicitness.
- **Engines field**: `"engines": { "node": ">=20.0.0" }`.
- **Bundled assets**: none of the Python sources — `speca-cli` invokes the user's local checkout (or auto-clones it; see §9.2).
- **Native deps**: `node-pty` is a native module. We ship prebuilt binaries via `node-gyp-build` and platform-specific `.node` files in the npm tarball to avoid build-on-install failures.

### 10.2 Bootstrapping the Python repo

`speca-cli` needs the SPECA Python sources to function. Two modes:

| Mode | Trigger | Behaviour |
|---|---|---|
| **Embedded** | Default, when no SPECA repo is detected | Auto-clone `https://github.com/NyxFoundation/speca` into `~/.cache/speca/<version>/` and pin to the same tag as the npm package |
| **Linked** | `SPECA_REPO=/path/to/speca` env var or `speca config set runner.repo_path …` | Use the user's own checkout (developer flow) |

Version pinning: the npm package version is the SPECA repo tag. So `speca-cli@1.4.2` clones `NyxFoundation/speca@v1.4.2`. The `speca doctor` command warns when the linked checkout drifts from the npm version.

### 10.3 Performance & UX targets

| Target | Goal |
|---|---|
| Cold start (`npx speca-cli` to first frame rendered) | < 800 ms on M1, < 1.5 s on Ubuntu cloud VM |
| Auth status check | < 500 ms (cached for the session lifetime) |
| Log tail latency (event written → row visible) | < 200 ms |
| Finding browser sort/filter response | < 50 ms for 1000 findings |
| Ask-Claude first token | < 2 s (bounded by Claude Code latency) |

### 10.4 Error handling & recovery

| Failure | UX |
|---|---|
| Claude Code CLI not installed | Modal: "Claude Code CLI is required. Install via `npm install -g @anthropic-ai/claude-code` and restart." Quit. |
| `uv` not installed | Modal with `pip install uv` instructions; offer `--use-pip` fallback (slower) |
| Network failure during git clone | Retry with exponential backoff (3 attempts), then surface error |
| Worker batch failure | Per-row inline error; Phase row stays in `error` state; user can retry from the TUI |
| Budget exceeded | Modal: "Run halted at $9.97 / $10.00 cap. Bump cap to ___ and resume? [Y/n]" |
| Auth expired mid-run | Pause runner, prompt `claude auth login`, resume |
| Disk full | Refuse to write partials; surface `df -h` output |

### 10.5 Telemetry

**No anonymous telemetry in v1.** Local-only error reporting via `~/.cache/speca/crash-<ts>.log`. A future opt-in `--share-anonymous-stats` is out of scope for this spec.

### 10.6 Testing strategy

| Layer | Strategy |
|---|---|
| TUI components | `ink-testing-library` snapshot tests + key-event simulations |
| Stream-JSON parsing | Replay-based tests using fixture JSONL files captured from real runs |
| Process bridge | `node-pty` mocked in unit tests; one e2e test that runs Phase 01a end-to-end against a tiny fixture spec |
| Wizards | Property-based tests (`fast-check`) on input validation |
| Cross-platform | GitHub Actions matrix: macos-14, ubuntu-22.04, windows-2022 (WSL2) |

### 10.7 Localisation

UI strings live in a single `i18n.ts` map. v1 ships English only; ja-JP is a v1.1 stretch goal given the maintainer team's bilinguality.

### 10.8 Accessibility

- All colour information is paired with a non-colour cue (icon, prefix). A `--no-color` / `NO_COLOR=1` mode is fully readable.
- Every interaction has a keyboard binding. Mouse is unsupported in v1 (terminal mouse is too unreliable across emulators).

## 11. Implementation Roadmap

| Milestone | Scope | Acceptance |
|---|---|---|
| **M1 — Skeleton (week 1)** | npm package scaffold, Ink layout shell, `speca version` / `speca doctor` | `npx speca-cli@next doctor` runs end-to-end |
| **M2 — Auth + project wizard (week 2)** | Vendor `ex-machina-co/opencode-anthropic-auth` into `src/auth/` (§9.2 reuse map), implement `speca auth status/login` against the Claude Code OAuth flow with API-key fallback, new-project wizard via `@clack/prompts`, write valid `TARGET_INFO.json` / `BUG_BOUNTY_SCOPE.json` | A new project can be configured without manual JSON editing; auth round-trip succeeds against a real Claude Code subscription |
| **M3 — Pipeline dashboard (weeks 3–4)** | Process bridge, stream-JSON parser, Screen 3 with live phase rows + log pane, `--json` flag added to `scripts/run_phase.py` | Running Phase 01a end-to-end inside the TUI matches the CLI behaviour 1:1 |
| **M4 — Finding browser (week 5)** | Screen 4 with filter DSL + sort + code peek | All Sherlock-RQ1 findings render correctly from a committed `outputs/04_PARTIAL_*.json` |
| **M5 — Ask Claude (week 6)** | Screen 5 chat pane bound to Claude Code session id | Multi-turn chat works against a real subscription |
| **M6 — Polish + docs (week 7)** | Theme support, key-binding overrides, error modals, `speca attach`, `speca browse [glob]` | All user stories in §3 pass on a fresh laptop |
| **M7 — v1 release** | npm publish, README + recording, CI matrix green | `npx speca-cli@1.0.0` works on macos-14 + ubuntu-22.04 |

A v0.1 internal preview can ship after **M2** (no real pipeline run, just project setup) to gather feedback early.

## 12. Required Upstream Changes & Vendoring Decisions

### 12.1 Upstream changes to this repository

Two small additions to the existing Python orchestrator are needed to make the TUI clean. Both are independent of `speca-cli` and useful on their own.

| # | File | Change | Rationale |
|---|---|---|---|
| U1 | `scripts/run_phase.py` | Add `--json` flag emitting one JSON object per line on stdout for pipeline-level events (`phase-started`, `phase-completed`, etc.) | Lets any consumer (TUI, CI, dashboards) drive a UI without log scraping |
| U2 | `scripts/orchestrator/schemas.py` | Add a `json-schema` export script under `scripts/export_schemas.py` to dump JSON Schema files matching every Pydantic model | Lets `speca-cli` validate `TARGET_INFO.json` / `BUG_BOUNTY_SCOPE.json` without running Python |

Both ship as PRs against `main` before `speca-cli@1.0.0`.

### 12.2 Vendoring vs. dependency decisions for third-party code

| Source | Mode | Rationale |
|---|---|---|
| [`ex-machina-co/opencode-anthropic-auth`](https://github.com/ex-machina-co/opencode-anthropic-auth) | **Vendor** (copy `auth.ts` / `pkce.ts` / `constants.ts` into `src/auth/`) | The project is ~3 small files; depending on it via npm couples our auth to a single hobby package. Vendoring + attribution is safer for unstable OAuth constants. |
| [`sst/opencode`](https://github.com/sst/opencode) `auth/index.ts` | **Pattern only** | Not vendored (uses Effect.ts). We re-implement the token-store pattern in plain TypeScript. |
| [`openai/codex`](https://github.com/openai/codex) `codex-rs/login/server.rs` | **Pattern only** | Different language (Rust). We re-implement the loopback-server topology in TypeScript on `node:http`. |
| `ink` / `@clack/prompts` / `chokidar` / `zod` / `node-pty` / `execa` | **npm dependency** | Stable, well-maintained packages — no need to vendor. |

When vendoring, every lifted file must:
1. Carry the original LICENSE notice in a header comment.
2. Be tracked in [`docs/SPECA_CLI_SPEC.md` §9.2](#92-file-level-reuse-map-what-we-actually-lift) with a stable upstream link.
3. Be re-checked at every minor release of the upstream package; a `make refresh-vendor` target dumps a side-by-side diff.

## 13. Open Questions

| # | Question | Owner | Notes |
|---|---|---|---|
| Q1 | Does Anthropic plan to support subscription auth via SDK (not only via the `claude` CLI)? If yes, we can drop the CLI subprocess for chat. | @grandchildrice | If/when this lands, simplify §8.5 |
| Q2 | Should `speca-cli` ship with prebuilt `node-pty` binaries for Windows native (not just WSL2)? | @grandchildrice | v1 targets WSL2; revisit if user demand exists |
| Q3 | Where do we host the project-template library (§7.2)? Inline in the npm package, or fetched at first-run from the GitHub repo? | TBD | Inline is simpler; lazy fetch lets us update templates without npm releases |
| Q4 | Should "ask Claude" support multi-finding context (e.g. "explain why these three findings cluster")? | TBD | Useful for triage; defer to v1.1 |
| Q5 | Do we need a "headless run, attach later" mode (the user starts a run, closes their laptop, comes back to attach)? | TBD | Possible via PID file + shared `.speca/run.lock`; defer to v1.1 |
| Q6 | What's the licence relationship between `speca-cli` (MIT) and the user's audit outputs? | @grandchildrice | Audit outputs belong to the user; the CLI does not exfiltrate them |

## 14. Glossary

| Term | Definition |
|---|---|
| **TUI** | Terminal User Interface — full-screen terminal application, as opposed to line-based CLI |
| **Subscription auth** | Authentication via Anthropic's Claude Code subscription, not via Anthropic API keys |
| **Stream-JSON** | The `--output-format=stream-json` mode of the Claude Code CLI, which emits one JSON event per line of stdout |
| **Phase** | One of the six SPECA pipeline stages (01a/01b/01e/02c/03/04 in legacy IDs; 1–6 in paper labels) |
| **Project** | A directory containing `outputs/TARGET_INFO.json` and `outputs/BUG_BOUNTY_SCOPE.json` plus accumulated SPECA outputs |
| **Worker** | One parallel process executing a phase batch; the orchestrator dispatches N workers per phase |
| **Finding** | A single output item from Phase 03 (`audit_items[]`) or Phase 04 (`reviewed_items[]`) |
| **Verdict** | Phase 04's per-finding label: CONFIRMED_VULNERABILITY / CONFIRMED_POTENTIAL / DISPUTED_FP / DOWNGRADED / NEEDS_MANUAL_REVIEW / PASS_THROUGH |
