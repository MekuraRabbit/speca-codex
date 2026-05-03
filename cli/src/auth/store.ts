/**
 * Token store for `speca-cli`.
 *
 * Layout: see docs/SPECA_CLI_SPEC.md §4.5.4.
 *
 *   POSIX:    ~/.config/speca/auth.json   (chmod 0o600)
 *   Windows:  %APPDATA%\speca\auth.json   (chmod is a no-op on win32)
 *
 * Atomic writes go through a sibling tmp file + `fs.rename`. The store schema
 * is intentionally a flat `accounts` map keyed by `accountId` so future
 * additions (e.g. per-account `subscription_tier`, `last_refresh_at`) are
 * non-breaking — bump the top-level `version` if a load-time migration is ever
 * required.
 *
 * Pattern (not source) inspiration:
 *   https://github.com/sst/opencode/blob/dev/packages/opencode/src/auth/index.ts
 *
 * We deliberately re-implement in plain TypeScript so we do not pull in
 * Effect.ts.
 */

import { randomBytes } from "node:crypto";
import { promises as fs, constants as fsConstants } from "node:fs";
import { homedir, platform } from "node:os";
import { dirname, join } from "node:path";

export type StoreVersion = 1;

export interface OAuthAccount {
  type: "oauth";
  access_token: string;
  refresh_token: string;
  /** Unix-ms expiry timestamp (matches `Date.now()` epoch). */
  expires_at: number;
  scopes: string[];
  created_at: number;
}

export interface ApiKeyAccount {
  type: "apikey";
  access_token: string;
  created_at: number;
}

export type Account = OAuthAccount | ApiKeyAccount;

export interface AuthStore {
  version: StoreVersion;
  accounts: Record<string, Account>;
}

const STORE_VERSION: StoreVersion = 1;
const FALLBACK_ACCOUNT_ID = "default";

function emptyStore(): AuthStore {
  return { version: STORE_VERSION, accounts: {} };
}

/**
 * Resolve the absolute path to `auth.json` for the current OS. Pure function;
 * does not touch the filesystem. The directory portion is guaranteed to be
 * `auth.json`'s `dirname`.
 */
export function authFilePath(env: NodeJS.ProcessEnv = process.env): string {
  if (platform() === "win32") {
    const appData = env.APPDATA;
    const base = appData && appData.length > 0 ? appData : join(homedir(), "AppData", "Roaming");
    return join(base, "speca", "auth.json");
  }
  // POSIX (linux, darwin, *bsd). Honour XDG_CONFIG_HOME, fall back to ~/.config.
  const xdg = env.XDG_CONFIG_HOME;
  const base = xdg && xdg.length > 0 ? xdg : join(homedir(), ".config");
  return join(base, "speca", "auth.json");
}

async function ensureDir(filePath: string): Promise<void> {
  await fs.mkdir(dirname(filePath), { recursive: true });
}

function isStoreShape(value: unknown): value is AuthStore {
  if (!value || typeof value !== "object") return false;
  const obj = value as Record<string, unknown>;
  if (obj.version !== STORE_VERSION) return false;
  if (!obj.accounts || typeof obj.accounts !== "object") return false;
  return true;
}

/**
 * Load the on-disk store. Returns an empty (in-memory) store if the file does
 * not exist or is malformed; callers should not have to handle ENOENT or
 * partial-write recovery themselves.
 */
export async function loadStore(filePath: string = authFilePath()): Promise<AuthStore> {
  let raw: string;
  try {
    raw = await fs.readFile(filePath, "utf8");
  } catch (err) {
    if ((err as NodeJS.ErrnoException).code === "ENOENT") {
      return emptyStore();
    }
    throw err;
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return emptyStore();
  }
  if (!isStoreShape(parsed)) {
    return emptyStore();
  }
  return parsed;
}

/**
 * Persist the store atomically: write to a sibling tmp file, fsync, rename.
 * On POSIX we also `chmod 0o600` so the secret material is owner-only. The
 * chmod is a no-op on Windows (NTFS uses ACLs, not POSIX bits — the
 * `%APPDATA%` path is already per-user-private).
 */
export async function saveStore(store: AuthStore, filePath: string = authFilePath()): Promise<void> {
  await ensureDir(filePath);
  const tmpName = `auth.json.${process.pid}.${randomBytes(6).toString("hex")}.tmp`;
  const tmpPath = join(dirname(filePath), tmpName);
  const body = JSON.stringify(store, null, 2);
  // `wx` opens exclusively; if a stale tmp exists we error rather than clobber.
  const handle = await fs.open(tmpPath, "wx", 0o600);
  try {
    await handle.writeFile(body, "utf8");
    // Best-effort: chmod is meaningful on POSIX, ignored by Node on win32.
    if (platform() !== "win32") {
      try {
        await handle.chmod(0o600);
      } catch {
        // Some filesystems (e.g. exFAT) reject chmod — ignore, the file is in
        // a per-user dir anyway.
      }
    }
    await handle.sync();
  } finally {
    await handle.close();
  }
  try {
    await fs.rename(tmpPath, filePath);
  } catch (err) {
    // Roll back the tmp file on rename failure so we do not leak garbage.
    try {
      await fs.unlink(tmpPath);
    } catch {
      // ignore — the rename failure is what we want to surface
    }
    throw err;
  }
  if (platform() !== "win32") {
    // Defensive re-chmod on the final path in case the umask relaxed bits via
    // rename's preservation rules on some platforms.
    try {
      await fs.chmod(filePath, 0o600);
    } catch {
      // ignore
    }
  }
}

export async function saveAccount(
  id: string,
  account: Account,
  filePath: string = authFilePath(),
): Promise<void> {
  const store = await loadStore(filePath);
  store.accounts[id] = account;
  await saveStore(store, filePath);
}

export async function getAccount(
  id?: string,
  filePath: string = authFilePath(),
): Promise<{ id: string; account: Account } | null> {
  const store = await loadStore(filePath);
  if (id !== undefined) {
    const acct = store.accounts[id];
    return acct ? { id, account: acct } : null;
  }
  // No id requested: prefer the conventional "default" account, otherwise
  // return the first (insertion-order) entry. This makes single-account UX
  // ergonomic without forcing users to know their `accountId`.
  const fallback = store.accounts[FALLBACK_ACCOUNT_ID];
  if (fallback) return { id: FALLBACK_ACCOUNT_ID, account: fallback };
  const keys = Object.keys(store.accounts);
  if (keys.length === 0) return null;
  const firstKey = keys[0]!;
  return { id: firstKey, account: store.accounts[firstKey]! };
}

export async function removeAccount(
  id: string,
  filePath: string = authFilePath(),
): Promise<boolean> {
  const store = await loadStore(filePath);
  if (!(id in store.accounts)) return false;
  delete store.accounts[id];
  await saveStore(store, filePath);
  return true;
}

export async function listAccounts(
  filePath: string = authFilePath(),
): Promise<Array<{ id: string; account: Account }>> {
  const store = await loadStore(filePath);
  return Object.entries(store.accounts).map(([id, account]) => ({ id, account }));
}

/**
 * Decode a JWT payload (no signature verification — we only use this to read
 * the `sub` claim, which the OAuth issuer attests to). Returns `null` for any
 * malformed input. Kept dependency-free.
 */
export function decodeJwtPayload(token: string): Record<string, unknown> | null {
  const parts = token.split(".");
  if (parts.length < 2) return null;
  const payload = parts[1]!;
  // base64url → base64
  const padded = payload.replace(/-/g, "+").replace(/_/g, "/");
  const padLen = (4 - (padded.length % 4)) % 4;
  const b64 = padded + "=".repeat(padLen);
  let json: string;
  try {
    json = Buffer.from(b64, "base64").toString("utf8");
  } catch {
    return null;
  }
  try {
    const parsed: unknown = JSON.parse(json);
    if (parsed && typeof parsed === "object") {
      return parsed as Record<string, unknown>;
    }
    return null;
  } catch {
    return null;
  }
}

/**
 * Best-effort accountId extraction from an OAuth access token. Anthropic's
 * tokens are JWTs whose `sub` claim is a stable per-user identifier; if the
 * token is opaque (or the claim is missing) we fall back to "default" so the
 * store stays usable.
 */
export function resolveAccountId(accessToken: string): string {
  const payload = decodeJwtPayload(accessToken);
  if (!payload) return FALLBACK_ACCOUNT_ID;
  const candidates = ["sub", "user_id", "account_id", "email"];
  for (const key of candidates) {
    const v = payload[key];
    if (typeof v === "string" && v.length > 0) return v;
  }
  return FALLBACK_ACCOUNT_ID;
}

/**
 * Convenience: report whether a given path is readable. Useful for `doctor`.
 */
export async function storeFileExists(filePath: string = authFilePath()): Promise<boolean> {
  try {
    await fs.access(filePath, fsConstants.R_OK);
    return true;
  } catch {
    return false;
  }
}
