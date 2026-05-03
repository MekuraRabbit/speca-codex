/**
 * `speca auth login` — drive the Anthropic OAuth paste-code flow (or save an
 * API key when `--api-key` is supplied).
 *
 * Implementation note: the OAuth flow is fundamentally a sequential prompt
 * (print URL → block on user paste → exchange) so this command is plain
 * stdout + readline rather than Ink. That keeps the user's clipboard paste
 * working reliably across Windows ConHost / iTerm / WSL2 — Ink's raw-mode
 * input handling has historically interacted badly with multi-line paste of
 * long OAuth callback URLs.
 *
 * The Ink TUI surface (auth wizard inside `speca init`, etc.) lives in M2's
 * other half and consumes the same `authorize`/`exchange`/store API exposed
 * here.
 */

import { createInterface } from "node:readline/promises";
import { stdin as input, stdout as output, stderr as errorOut } from "node:process";
import { authorize, exchange } from "../../auth/auth.js";
import { OAUTH_SCOPES } from "../../auth/constants.js";
import {
  resolveAccountId,
  saveAccount,
  type ApiKeyAccount,
  type OAuthAccount,
} from "../../auth/store.js";

export interface LoginOptions {
  /** When set, skip the OAuth flow entirely and persist the API key. */
  apiKey?: string;
  /** OAuth entitlement source. Defaults to "max" (Pro/Max subscription). */
  mode?: "max" | "console";
  /**
   * For tests / non-interactive callers: the prompt callback receives the
   * authorize URL and must resolve to whatever the user pasted. Default
   * implementation is a real readline prompt.
   */
  prompt?: (authorizeUrl: string) => Promise<string>;
  /** Override the on-disk auth.json path (used by tests). */
  authFile?: string;
  /**
   * Allow tests to inject a fake `authorize`/`exchange` pair. Defaults to the
   * vendored implementation.
   */
  authorizeFn?: typeof authorize;
  exchangeFn?: typeof exchange;
}

export interface LoginSuccess {
  ok: true;
  accountId: string;
  type: "oauth" | "apikey";
}

export interface LoginFailure {
  ok: false;
  message: string;
}

export type LoginResult = LoginSuccess | LoginFailure;

async function defaultPrompt(authorizeUrl: string): Promise<string> {
  const rl = createInterface({ input, output, terminal: false });
  try {
    output.write("\n");
    output.write("Open the following URL in your browser to log in:\n\n");
    output.write(`  ${authorizeUrl}\n\n`);
    output.write("After signing in, claude.ai will show a code string. Paste it below.\n");
    output.write("Accepted formats: full callback URL, `code#state`, or `code=...&state=...`\n\n");
    const answer = await rl.question("Paste code: ");
    return answer;
  } finally {
    rl.close();
  }
}

/**
 * Programmatic entry point. Returns a structured result so the CLI surface
 * (and tests) can react without inspecting stdout.
 */
export async function runLogin(opts: LoginOptions = {}): Promise<LoginResult> {
  const now = Date.now();

  if (opts.apiKey !== undefined) {
    const trimmed = opts.apiKey.trim();
    if (trimmed.length === 0) {
      return { ok: false, message: "--api-key was empty" };
    }
    const account: ApiKeyAccount = {
      type: "apikey",
      access_token: trimmed,
      created_at: now,
    };
    const id = "apikey";
    await saveAccount(id, account, opts.authFile);
    return { ok: true, accountId: id, type: "apikey" };
  }

  const authorizeFn = opts.authorizeFn ?? authorize;
  const exchangeFn = opts.exchangeFn ?? exchange;
  const mode = opts.mode ?? "max";

  const authn = await authorizeFn(mode);
  const promptFn = opts.prompt ?? defaultPrompt;
  const pasted = await promptFn(authn.url);
  if (!pasted || pasted.trim().length === 0) {
    return { ok: false, message: "no code was pasted" };
  }

  const result = await exchangeFn(pasted, authn.verifier, authn.redirectUri, authn.state);
  if (result.type !== "success") {
    return {
      ok: false,
      message:
        "OAuth token exchange failed. Double-check the pasted code/URL and retry, " +
        "or fall back to `speca auth login --api-key <key>`.",
    };
  }

  const account: OAuthAccount = {
    type: "oauth",
    access_token: result.access,
    refresh_token: result.refresh,
    expires_at: result.expires,
    scopes: [...OAUTH_SCOPES],
    created_at: now,
  };
  const id = resolveAccountId(result.access);
  await saveAccount(id, account, opts.authFile);
  return { ok: true, accountId: id, type: "oauth" };
}

/** Print the result from `runLogin` to stdout/stderr and return an exit code. */
export function reportLogin(result: LoginResult): number {
  if (result.ok) {
    output.write(
      `\nLogged in as ${result.accountId} (${result.type === "oauth" ? "Claude Code subscription" : "API key"}).\n`,
    );
    return 0;
  }
  errorOut.write(`\nLogin failed: ${result.message}\n`);
  return 1;
}

/** CLI entry: parse args from cli.tsx, run, exit-code. */
export async function loginCommand(opts: LoginOptions): Promise<number> {
  try {
    const result = await runLogin(opts);
    return reportLogin(result);
  } catch (err) {
    errorOut.write(`\nLogin error: ${(err as Error).message}\n`);
    return 1;
  }
}

export const LOGIN_HELP = `Usage
  $ speca auth login [--api-key <key>] [--mode <max|console>]

Log in to Anthropic. Without flags, runs the OAuth paste-code flow against
your Claude Code (Pro/Max) subscription. With --api-key, persists the given
key for users without a subscription.

Flags
  --api-key <key>    Skip OAuth and store the given Anthropic API key.
  --mode <max|console>
                     Which OAuth entitlement source to use. Defaults to "max"
                     (Pro/Max subscription, billed against Claude Code).
  --help             Show this help and exit.

Examples
  $ speca auth login
  $ speca auth login --api-key sk-ant-api03-...
  $ speca auth login --mode console
`;
