import { promises as fs } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { checkAuth, checkGit, checkNode } from "../src/lib/checks.js";
import { OAUTH_SCOPES } from "../src/auth/constants.js";
import { saveAccount } from "../src/auth/store.js";

describe("checkNode", () => {
  it("accepts current Node when running on >=20", async () => {
    const r = await checkNode();
    expect(r.name).toBe("node");
    expect(["ok", "fail"]).toContain(r.status);
    if (r.status === "ok") {
      expect(r.detail).toMatch(/^v\d+\./);
    } else {
      expect(r.hint).toContain("Node");
    }
  });
});

describe("checkGit", () => {
  it("returns a CheckResult shape regardless of presence", async () => {
    const r = await checkGit();
    expect(r.name).toBe("git");
    expect(["ok", "warn", "fail"]).toContain(r.status);
    expect(typeof r.detail).toBe("string");
  });
});

describe("checkAuth", () => {
  let workDir: string;
  let storePath: string;

  beforeEach(async () => {
    workDir = await fs.mkdtemp(join(tmpdir(), "speca-checks-test-"));
    storePath = join(workDir, "speca", "auth.json");
  });

  afterEach(async () => {
    await fs.rm(workDir, { recursive: true, force: true });
  });

  it("warns (not fails) when no auth file exists", async () => {
    const r = await checkAuth({ authFile: storePath });
    expect(r.name).toBe("auth");
    expect(r.status).toBe("warn");
    expect(r.detail).toBe("not logged in");
    expect(r.hint).toContain("speca auth login");
  });

  it("returns ok for an OAuth account with the required scope", async () => {
    await saveAccount(
      "alice",
      {
        type: "oauth",
        access_token: "tok",
        refresh_token: "rtok",
        expires_at: Date.now() + 3_600_000,
        scopes: [...OAUTH_SCOPES],
        created_at: Date.now(),
      },
      storePath,
    );
    const r = await checkAuth({ authFile: storePath, now: Date.now() });
    expect(r.status).toBe("ok");
    expect(r.detail).toContain("oauth");
    expect(r.detail).toContain("alice");
  });

  it("fails when the OAuth token is missing user:sessions:claude_code", async () => {
    await saveAccount(
      "alice",
      {
        type: "oauth",
        access_token: "tok",
        refresh_token: "rtok",
        expires_at: Date.now() + 3_600_000,
        scopes: ["user:profile"], // intentionally short
        created_at: Date.now(),
      },
      storePath,
    );
    const r = await checkAuth({ authFile: storePath, now: Date.now() });
    expect(r.status).toBe("fail");
    expect(r.detail).toContain("user:sessions:claude_code");
    expect(r.hint).toContain("user:sessions:claude_code");
  });

  it("warns when the OAuth token has expired", async () => {
    await saveAccount(
      "alice",
      {
        type: "oauth",
        access_token: "tok",
        refresh_token: "rtok",
        expires_at: 1_000, // way in the past
        scopes: [...OAUTH_SCOPES],
        created_at: 0,
      },
      storePath,
    );
    const r = await checkAuth({ authFile: storePath, now: Date.now() });
    expect(r.status).toBe("warn");
    expect(r.detail).toContain("expired");
  });

  it("returns ok in api-key mode and surfaces the mode in detail", async () => {
    await saveAccount(
      "apikey",
      { type: "apikey", access_token: "sk-ant-test", created_at: Date.now() },
      storePath,
    );
    const r = await checkAuth({ authFile: storePath });
    expect(r.status).toBe("ok");
    expect(r.detail).toContain("api-key");
  });
});
