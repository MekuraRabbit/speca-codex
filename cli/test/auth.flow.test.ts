import { promises as fs } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { runLogin } from "../src/commands/auth/login.js";
import { OAUTH_SCOPES } from "../src/auth/constants.js";
import { listAccounts, type OAuthAccount } from "../src/auth/store.js";
import { checkAuth } from "../src/auth/check.js";

let workDir: string;
let storePath: string;

beforeEach(async () => {
  workDir = await fs.mkdtemp(join(tmpdir(), "speca-flow-test-"));
  storePath = join(workDir, "speca", "auth.json");
});

afterEach(async () => {
  await fs.rm(workDir, { recursive: true, force: true });
});

describe("runLogin (OAuth path)", () => {
  it("drives authorize → prompt → exchange → store and resolves accountId from JWT", async () => {
    // Build a JWT whose `sub` claim becomes the account id.
    const header = Buffer.from(JSON.stringify({ alg: "none" })).toString("base64url");
    const body = Buffer.from(JSON.stringify({ sub: "user-fixture-123" })).toString("base64url");
    const fakeAccess = `${header}.${body}.sig`;

    const promptedUrls: string[] = [];
    const result = await runLogin({
      authFile: storePath,
      authorizeFn: async (mode) => {
        expect(mode).toBe("max");
        return {
          url: "https://claude.ai/oauth/authorize?fixture=1",
          redirectUri: "https://platform.claude.com/oauth/code/callback",
          state: "state-fixture",
          verifier: "verifier-fixture",
        };
      },
      prompt: async (url) => {
        promptedUrls.push(url);
        return "code-fixture#state-fixture";
      },
      exchangeFn: async (input, verifier, redirectUri, expectedState) => {
        expect(verifier).toBe("verifier-fixture");
        expect(expectedState).toBe("state-fixture");
        expect(redirectUri).toBe("https://platform.claude.com/oauth/code/callback");
        expect(input).toBe("code-fixture#state-fixture");
        return {
          type: "success",
          access: fakeAccess,
          refresh: "refresh-fixture",
          expires: Date.now() + 3_600_000,
        };
      },
    });

    expect(result.ok).toBe(true);
    if (!result.ok) throw new Error("unreachable");
    expect(result.type).toBe("oauth");
    expect(result.accountId).toBe("user-fixture-123");
    expect(promptedUrls).toEqual(["https://claude.ai/oauth/authorize?fixture=1"]);

    const accounts = await listAccounts(storePath);
    expect(accounts).toHaveLength(1);
    const stored = accounts[0]?.account as OAuthAccount;
    expect(stored.type).toBe("oauth");
    expect(stored.access_token).toBe(fakeAccess);
    expect(stored.refresh_token).toBe("refresh-fixture");
    expect(stored.scopes).toEqual(OAUTH_SCOPES);

    // Round-trip into checkAuth so the full login → status flow is covered.
    const check = await checkAuth({ authFile: storePath });
    expect(check.status).toBe("ok");
    expect(check.detail).toContain("user-fixture-123");
  });

  it("reports a failure (without writing to store) when exchange rejects", async () => {
    const result = await runLogin({
      authFile: storePath,
      authorizeFn: async () => ({
        url: "https://claude.ai/oauth/authorize",
        redirectUri: "https://platform.claude.com/oauth/code/callback",
        state: "s",
        verifier: "v",
      }),
      prompt: async () => "garbage-input",
      exchangeFn: async () => ({ type: "failed" }),
    });
    expect(result.ok).toBe(false);
    expect(await listAccounts(storePath)).toHaveLength(0);
  });

  it("rejects an empty pasted code without invoking exchange", async () => {
    let exchangeCalls = 0;
    const result = await runLogin({
      authFile: storePath,
      authorizeFn: async () => ({
        url: "https://claude.ai/oauth/authorize",
        redirectUri: "https://platform.claude.com/oauth/code/callback",
        state: "s",
        verifier: "v",
      }),
      prompt: async () => "   ",
      exchangeFn: async () => {
        exchangeCalls++;
        return { type: "failed" };
      },
    });
    expect(result.ok).toBe(false);
    expect(exchangeCalls).toBe(0);
  });
});

describe("runLogin (--api-key path)", () => {
  it("persists an API key without touching authorize/exchange", async () => {
    let authorizeCalls = 0;
    const result = await runLogin({
      apiKey: "sk-ant-test-fixture",
      authFile: storePath,
      authorizeFn: async () => {
        authorizeCalls++;
        throw new Error("authorize must not be called when --api-key is set");
      },
    });
    expect(authorizeCalls).toBe(0);
    expect(result.ok).toBe(true);
    if (!result.ok) throw new Error("unreachable");
    expect(result.type).toBe("apikey");

    const check = await checkAuth({ authFile: storePath });
    expect(check.status).toBe("ok");
    expect(check.detail).toContain("api-key");
  });

  it("rejects an empty --api-key value", async () => {
    const result = await runLogin({ apiKey: "   ", authFile: storePath });
    expect(result.ok).toBe(false);
    expect(await listAccounts(storePath)).toHaveLength(0);
  });
});
