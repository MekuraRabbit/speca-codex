import { execFile } from "node:child_process";
import { promisify } from "node:util";
import which from "which";

const execFileAsync = promisify(execFile);

export type CheckStatus = "ok" | "warn" | "fail" | "skip";

export interface CheckResult {
  name: string;
  status: CheckStatus;
  detail: string;
  hint?: string;
}

import { checkAuth } from "../auth/check.js";

// Re-export so callers (e.g. cli/test/checks.test.ts, doctor.tsx) can import
// the auth check from a single, stable surface.
export { checkAuth };

const MIN_NODE_MAJOR = 20;

export async function checkNode(): Promise<CheckResult> {
  const version = process.version;
  const major = Number.parseInt(version.replace(/^v/, "").split(".")[0] ?? "0", 10);
  if (major >= MIN_NODE_MAJOR) {
    return { name: "node", status: "ok", detail: version };
  }
  return {
    name: "node",
    status: "fail",
    detail: `${version} (need >= v${MIN_NODE_MAJOR})`,
    hint: `Install Node ${MIN_NODE_MAJOR}+ from https://nodejs.org/`,
  };
}

async function probeBinary(
  bin: string,
  args: string[],
  install: string,
  optional = false,
): Promise<CheckResult> {
  const path = await which(bin, { nothrow: true });
  if (!path) {
    return {
      name: bin,
      status: optional ? "warn" : "fail",
      detail: "not found on PATH",
      hint: install,
    };
  }
  // Node.js 22.5+ refuses to execute .cmd / .bat files directly on Windows
  // (CVE-2024-27980). Invoke them through `cmd.exe /c` ourselves to avoid the
  // DEP0190-flagged `shell:true + args` path.
  const isWinScript = process.platform === "win32" && /\.(cmd|bat)$/i.test(path);
  const execPath = isWinScript ? "cmd.exe" : path;
  const execArgs = isWinScript ? ["/d", "/s", "/c", path, ...args] : args;
  try {
    const { stdout } = await execFileAsync(execPath, execArgs, {
      timeout: 5000,
      windowsHide: true,
    });
    const version = stdout.trim().split(/\r?\n/)[0] ?? "";
    return { name: bin, status: "ok", detail: version || path };
  } catch (err) {
    return {
      name: bin,
      status: optional ? "warn" : "fail",
      detail: `failed to invoke (${(err as Error).message})`,
      hint: install,
    };
  }
}

export const checkUv = (): Promise<CheckResult> =>
  probeBinary("uv", ["--version"], "https://docs.astral.sh/uv/getting-started/installation/");

export const checkGit = (): Promise<CheckResult> =>
  probeBinary("git", ["--version"], "https://git-scm.com/downloads");

export const checkClaude = (): Promise<CheckResult> =>
  probeBinary(
    "claude",
    ["--version"],
    "npm install -g @anthropic-ai/claude-code",
    true,
  );

export async function runAllChecks(): Promise<CheckResult[]> {
  return Promise.all([checkNode(), checkUv(), checkGit(), checkClaude(), checkAuth()]);
}
