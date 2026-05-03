import { describe, expect, it } from "vitest";
import { checkGit, checkNode } from "../src/lib/checks.js";

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
