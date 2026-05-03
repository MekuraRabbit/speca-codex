#!/usr/bin/env node
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { render } from "ink";
import meow from "meow";
import { createElement } from "react";
import { DoctorCommand } from "./commands/doctor.js";
import { VersionCommand } from "./commands/version.js";

const __dirname = dirname(fileURLToPath(import.meta.url));

interface PackageJsonShape {
  version: string;
}

function readPackageVersion(): string {
  // dist/cli.js → ../package.json (also works under tsx where __dirname is src/)
  for (const candidate of [resolve(__dirname, "..", "package.json"), resolve(__dirname, "..", "..", "package.json")]) {
    try {
      const raw = readFileSync(candidate, "utf8");
      const pkg = JSON.parse(raw) as PackageJsonShape;
      if (pkg.version) return pkg.version;
    } catch {
      // try next candidate
    }
  }
  return "unknown";
}

const cli = meow(
  `
  Usage
    $ speca <command>

  Commands
    version            Print speca-cli version
    doctor             Check Node / uv / git / claude-code installation
    help               Print this help

  Common flags (reserved for future milestones)
    --no-tui           Force plain-text output (M6)
    --json             Emit machine-readable events on stdout (M3)

  Examples
    $ speca doctor
    $ speca version
`,
  {
    importMeta: import.meta,
    flags: {
      noTui: { type: "boolean", default: false },
      json: { type: "boolean", default: false },
    },
    autoHelp: false,
    autoVersion: false,
  },
);

const command = cli.input[0] ?? "help";
const version = readPackageVersion();

async function run(): Promise<number> {
  switch (command) {
    case "version":
    case "--version":
    case "-v": {
      const app = render(createElement(VersionCommand, { version }));
      await app.waitUntilExit();
      return 0;
    }
    case "doctor": {
      const app = render(createElement(DoctorCommand));
      try {
        await app.waitUntilExit();
        return 0;
      } catch {
        return 1;
      }
    }
    case "help":
    case "--help":
    case "-h":
      cli.showHelp(0);
      return 0;
    default:
      console.error(`Unknown command: ${command}`);
      cli.showHelp(1);
      return 1;
  }
}

run().then((code) => {
  process.exit(code);
});
