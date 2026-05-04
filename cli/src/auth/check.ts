/**
 * `speca doctor` integration for the auth subsystem.
 *
 * Kept in `src/auth/` (not in `src/lib/checks.ts`) so all auth-related
 * knowledge lives behind one boundary; `checks.ts` just imports `checkAuth`.
 */

import type { CheckResult } from "../lib/checks.js";
import { OAUTH_SCOPES } from "./constants.js";
import { authFilePath, getAccount, type Account } from "./store.js";

export const REQUIRED_OAUTH_SCOPE = "user:sessions:claude_code";

/**
 * Verified by docs/SPECA_CLI_SPEC.md §4.5.2: without this scope the issued
 * token is rejected for inference (or silently billed against the wrong
 * entitlement). `checkAuth` fails when an OAuth account exists but is missing
 * it.
 */
export const REQUIRED_OAUTH_SCOPES = [REQUIRED_OAUTH_SCOPE];

export interface CheckAuthOptions {
  /** Override the auth.json location (used by tests). */
  authFile?: string;
  /** Inject the current time (used by tests for expiry boundary cases). */
  now?: number;
}

function describeScopes(account: Account): string[] {
  return account.type === "oauth" ? account.scopes : [];
}

function missingScopes(account: Account, required: string[]): string[] {
  if (account.type !== "oauth") return [];
  const have = new Set(account.scopes);
  return required.filter((s) => !have.has(s));
}

/**
 * Return a single `CheckResult` describing the auth subsystem's state.
 * Statuses (per the spec):
 *   - "ok"   logged in (oauth w/ required scope, or apikey)
 *   - "warn" not logged in (subscription mode is opt-in)
 *   - "fail" logged in but token is missing required scope
 */
export async function checkAuth(opts: CheckAuthOptions = {}): Promise<CheckResult> {
  const file = opts.authFile ?? authFilePath();
  const found = await getAccount(undefined, file);
  if (!found) {
    return {
      name: "auth",
      status: "warn",
      detail: "not logged in",
      hint: "Run `speca auth login` to enable Claude Code subscription mode",
    };
  }
  const { id, account } = found;
  if (account.type === "apikey") {
    return {
      name: "auth",
      status: "ok",
      detail: `api-key mode (account: ${id})`,
    };
  }
  // OAuth account.
  const missing = missingScopes(account, REQUIRED_OAUTH_SCOPES);
  if (missing.length > 0) {
    return {
      name: "auth",
      status: "fail",
      detail: `oauth (account: ${id}) missing scope(s): ${missing.join(", ")}`,
      hint: `Re-run \`speca auth login\` — your token is missing ${missing.join(", ")}`,
    };
  }
  const now = opts.now ?? Date.now();
  if (account.expires_at <= now) {
    return {
      name: "auth",
      status: "warn",
      detail: `oauth (account: ${id}) token expired`,
      hint: "Run `speca auth login` to refresh your subscription token",
    };
  }
  const remainingMs = account.expires_at - now;
  const remainingMin = Math.floor(remainingMs / 60_000);
  const scopeCount = describeScopes(account).length;
  return {
    name: "auth",
    status: "ok",
    detail: `oauth (account: ${id}, ${scopeCount} scopes, expires in ${remainingMin}m)`,
  };
}
