import { promises as fs } from "node:fs";
import { tmpdir, platform } from "node:os";
import { join } from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  authFilePath,
  decodeJwtPayload,
  getAccount,
  listAccounts,
  loadStore,
  removeAccount,
  resolveAccountId,
  saveAccount,
  saveStore,
  storeFileExists,
  type ApiKeyAccount,
  type OAuthAccount,
} from "../src/auth/store.js";

let workDir: string;
let storePath: string;

beforeEach(async () => {
  workDir = await fs.mkdtemp(join(tmpdir(), "speca-auth-test-"));
  storePath = join(workDir, "speca", "auth.json");
});

afterEach(async () => {
  await fs.rm(workDir, { recursive: true, force: true });
});

function makeOauth(overrides: Partial<OAuthAccount> = {}): OAuthAccount {
  return {
    type: "oauth",
    access_token: "access-1",
    refresh_token: "refresh-1",
    expires_at: Date.now() + 60_000,
    scopes: ["user:sessions:claude_code", "user:profile"],
    created_at: Date.now(),
    ...overrides,
  };
}

function makeApiKey(): ApiKeyAccount {
  return {
    type: "apikey",
    access_token: "sk-ant-test",
    created_at: Date.now(),
  };
}

describe("authFilePath", () => {
  it("uses %APPDATA% on Windows", () => {
    if (platform() !== "win32") {
      // Cannot fully simulate win32 here — just ensure the function returns
      // a path containing 'speca' and 'auth.json' on the host OS.
      expect(authFilePath()).toMatch(/speca.+auth\.json$/);
      return;
    }
    const p = authFilePath({ APPDATA: "C:/fake/AppData" });
    expect(p).toMatch(/speca[\\/]auth\.json$/);
    expect(p).toContain("AppData");
  });

  it("honours XDG_CONFIG_HOME on POSIX", () => {
    if (platform() === "win32") return;
    const p = authFilePath({ XDG_CONFIG_HOME: "/tmp/xdg-fake" });
    expect(p).toBe("/tmp/xdg-fake/speca/auth.json");
  });
});

describe("loadStore / saveStore round-trip", () => {
  it("returns an empty store when file is missing", async () => {
    const store = await loadStore(storePath);
    expect(store).toEqual({ version: 1, accounts: {} });
    expect(await storeFileExists(storePath)).toBe(false);
  });

  it("persists and re-loads an account losslessly", async () => {
    const oauth = makeOauth();
    await saveAccount("alice", oauth, storePath);
    const re = await loadStore(storePath);
    expect(re.version).toBe(1);
    expect(re.accounts["alice"]).toEqual(oauth);
    expect(await storeFileExists(storePath)).toBe(true);
  });

  it("recovers from corrupt JSON by returning an empty store", async () => {
    await fs.mkdir(join(workDir, "speca"), { recursive: true });
    await fs.writeFile(storePath, "{ not valid json", "utf8");
    const store = await loadStore(storePath);
    expect(store).toEqual({ version: 1, accounts: {} });
  });

  it("creates the parent directory if it does not exist", async () => {
    const deep = join(workDir, "deeper", "speca", "auth.json");
    await saveStore({ version: 1, accounts: { x: makeApiKey() } }, deep);
    const re = await loadStore(deep);
    expect(re.accounts["x"]?.type).toBe("apikey");
  });
});

describe("atomic write semantics", () => {
  it("does not leave a tmp file behind on success", async () => {
    await saveAccount("bob", makeOauth(), storePath);
    const dir = join(workDir, "speca");
    const entries = await fs.readdir(dir);
    expect(entries).toContain("auth.json");
    expect(entries.filter((e) => e.endsWith(".tmp"))).toEqual([]);
  });

  it("each sequential save leaves the file parseable", async () => {
    // We cannot assert across concurrent saves on Windows (NTFS rejects
    // overlapping renames to the same destination with EPERM, which is the
    // expected behaviour, not a bug in our code). Instead, do a sequential
    // sweep and assert every observable state is parseable + correct.
    for (let i = 0; i < 10; i++) {
      await saveAccount(`acc-${i}`, makeOauth({ access_token: `tok-${i}` }), storePath);
      const snapshot = await loadStore(storePath);
      expect(snapshot.version).toBe(1);
      expect(snapshot.accounts[`acc-${i}`]).toBeDefined();
    }
    const final = await loadStore(storePath);
    expect(Object.keys(final.accounts)).toHaveLength(10);
  });
});

describe("chmod (POSIX only)", () => {
  it("stores auth.json as 0o600 on POSIX", async () => {
    if (platform() === "win32") {
      // Windows uses ACLs, not POSIX mode bits — chmod is a documented no-op.
      // Skip the assertion rather than fail.
      return;
    }
    await saveAccount("perm", makeOauth(), storePath);
    const stat = await fs.stat(storePath);
    // Mask off the file-type bits, keep only permissions.
    expect(stat.mode & 0o777).toBe(0o600);
  });
});

describe("getAccount fallback resolution", () => {
  it("returns null when no accounts exist", async () => {
    expect(await getAccount(undefined, storePath)).toBeNull();
  });

  it("prefers the 'default' account when no id requested", async () => {
    await saveAccount("alice", makeOauth({ access_token: "alice" }), storePath);
    await saveAccount("default", makeOauth({ access_token: "default" }), storePath);
    const r = await getAccount(undefined, storePath);
    expect(r?.id).toBe("default");
    expect((r?.account as OAuthAccount).access_token).toBe("default");
  });

  it("falls back to the first account when 'default' is absent", async () => {
    await saveAccount("alice", makeOauth(), storePath);
    const r = await getAccount(undefined, storePath);
    expect(r?.id).toBe("alice");
  });

  it("returns null when the requested id is not present", async () => {
    await saveAccount("alice", makeOauth(), storePath);
    expect(await getAccount("bob", storePath)).toBeNull();
  });
});

describe("removeAccount / listAccounts", () => {
  it("removes only the requested account", async () => {
    await saveAccount("alice", makeOauth(), storePath);
    await saveAccount("bob", makeOauth(), storePath);
    expect(await removeAccount("alice", storePath)).toBe(true);
    const left = await listAccounts(storePath);
    expect(left).toHaveLength(1);
    expect(left[0]?.id).toBe("bob");
  });

  it("returns false when removing a non-existent account", async () => {
    expect(await removeAccount("ghost", storePath)).toBe(false);
  });
});

describe("decodeJwtPayload / resolveAccountId", () => {
  function makeJwt(payload: Record<string, unknown>): string {
    const header = Buffer.from(JSON.stringify({ alg: "none", typ: "JWT" })).toString("base64url");
    const body = Buffer.from(JSON.stringify(payload)).toString("base64url");
    return `${header}.${body}.sig`;
  }

  it("extracts the sub claim", () => {
    const tok = makeJwt({ sub: "user-abc-123" });
    expect(decodeJwtPayload(tok)).toMatchObject({ sub: "user-abc-123" });
    expect(resolveAccountId(tok)).toBe("user-abc-123");
  });

  it("falls back to email/account_id when sub is absent", () => {
    expect(resolveAccountId(makeJwt({ email: "alice@example.com" }))).toBe("alice@example.com");
    expect(resolveAccountId(makeJwt({ account_id: "acct_42" }))).toBe("acct_42");
  });

  it("returns 'default' for opaque/non-JWT tokens", () => {
    expect(resolveAccountId("totally-opaque")).toBe("default");
    expect(resolveAccountId("")).toBe("default");
  });

  it("returns 'default' for JWT-shaped but malformed payloads", () => {
    expect(resolveAccountId("aaa.bbb.ccc")).toBe("default");
  });
});
