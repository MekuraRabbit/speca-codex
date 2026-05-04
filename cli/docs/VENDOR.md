# Vendored Source Files

This document tracks third-party source files that live inside `cli/src/` rather
than being pulled in as npm dependencies. Vendoring is reserved for code that
is too small to justify a dependency edge **or** that touches reverse-engineered
constants we want to be able to hot-patch in a single PR.

See `docs/SPECA_CLI_SPEC.md` §9.2 (file-level reuse map) and §12.2 (vendoring
decisions) for the policy that produced this list.

---

## Vendored files

### `cli/src/auth/constants.ts`
### `cli/src/auth/pkce.ts`
### `cli/src/auth/auth.ts`

| Field      | Value                                                                  |
| ---------- | ---------------------------------------------------------------------- |
| Upstream   | https://github.com/ex-machina-co/opencode-anthropic-auth               |
| Path       | `src/constants.ts`, `src/pkce.ts`, `src/auth.ts`                       |
| Commit     | `01c1548afb1318bdebc6f33a8b1e2f4e28c90edd`                             |
| Retrieved  | 2026-05-03                                                             |
| License    | MIT (full text reproduced in each file's header comment)               |

#### Why we vendor instead of depending

`opencode-anthropic-auth` is a ~3-file hobby package. The constants it exports
(`CLIENT_ID`, `OAUTH_SCOPES`, `USER_AGENT`, etc.) are reverse-engineered from
the official `claude` CLI's network traffic. Anthropic could rotate them at any
time. Vendoring lets a maintainer ship a hotfix as a single-file edit without
chasing a transitive dependency through npm.

#### Modifications from upstream

| File          | Modifications                                                                                           |
| ------------- | ------------------------------------------------------------------------------------------------------- |
| `constants.ts`| None (verbatim copy).                                                                                   |
| `pkce.ts`     | None (verbatim copy).                                                                                   |
| `auth.ts`     | Dropped explicit `.ts` extensions on relative imports (`./constants.ts` → `./constants.js`) so the file compiles cleanly under our `tsconfig.json` (`moduleResolution: "Bundler"`). No behavioural change. |

If you need to re-vendor, please keep the modification list in sync with the
header comment inside each file.

---

## Refresh procedure

We do not ship a `Makefile` target for refresh — the diff is small enough that a
maintainer can drive it by hand and review each change.

1. Fetch the latest upstream sources to a scratch directory:

   ```bash
   mkdir -p /tmp/vendor-refresh
   gh api repos/ex-machina-co/opencode-anthropic-auth/contents/src/auth.ts      --jq '.content' | base64 -d > /tmp/vendor-refresh/auth.ts
   gh api repos/ex-machina-co/opencode-anthropic-auth/contents/src/pkce.ts      --jq '.content' | base64 -d > /tmp/vendor-refresh/pkce.ts
   gh api repos/ex-machina-co/opencode-anthropic-auth/contents/src/constants.ts --jq '.content' | base64 -d > /tmp/vendor-refresh/constants.ts
   ```

2. Diff each file against our vendored copy, **ignoring the header comment** that
   we add (it is the part above the first `import`/`export`):

   ```bash
   for f in auth.ts pkce.ts constants.ts; do
     echo "=== $f ==="
     diff -u \
       <(awk '/^(import|export|function|const|type)/{p=1} p' cli/src/auth/$f) \
       /tmp/vendor-refresh/$f
   done
   ```

3. Note the new commit SHA:

   ```bash
   gh api repos/ex-machina-co/opencode-anthropic-auth/commits/main --jq '.sha'
   ```

4. If there is a meaningful diff:
   - Apply the upstream changes by hand to each file in `cli/src/auth/`.
   - Update the `Commit` and `Retrieved` fields in **both** this file and in
     each affected file's header comment.
   - Re-run `npm run typecheck && npm test` from `cli/`.
   - Commit with a message like `chore(cli/auth): refresh vendored opencode-anthropic-auth to <sha>`.

5. If the upstream introduced a brand-new file (e.g. `src/refresh.ts`) and we
   need it:
   - Copy it into `cli/src/auth/`.
   - Add the same MIT header preamble that the other files use.
   - Add a new section to this document.

6. If the upstream is archived or forked, document the rationale here and pin
   to the last good commit instead of removing the section.

---

## What we do **not** vendor

For everything outside the auth flow we depend on packages, not vendor source
files (`ink`, `meow`, `which`, etc.). The full reuse map lives in
`docs/SPECA_CLI_SPEC.md` §9.2.

The `sst/opencode` token-store layout (`auth/index.ts`) is a **pattern only**
inspiration for `cli/src/auth/store.ts`; we did not copy any of its source
because it depends on Effect.ts. We re-implemented the same layout in plain
TypeScript, so no vendor entry is required for it.
