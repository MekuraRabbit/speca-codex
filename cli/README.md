# speca-cli

TUI front-end for the [SPECA](https://github.com/NyxFoundation/speca) security-audit pipeline.

> **Status:** M1 (skeleton). Full design in [`docs/SPECA_CLI_SPEC.md`](../docs/SPECA_CLI_SPEC.md). Tracking issue: [#3](https://github.com/NyxFoundation/speca/issues/3).

## Quick start (development)

```bash
cd cli
npm install
npm run dev -- doctor       # run from source via tsx
npm run build               # compile to dist/
node dist/cli.js doctor     # run the built bundle
```

## Commands available in M1

| Command | Description |
|---|---|
| `speca version` | Print the speca-cli version |
| `speca doctor` | Check that Node / uv / git / claude-code are installed |
| `speca help` | Show usage |

Future milestones (M2–M7) add `init`, `auth`, `run`, `browse`, `attach`, `config`, the live pipeline dashboard, and the finding browser. See [SPEC §11](../docs/SPECA_CLI_SPEC.md#11-implementation-roadmap).

## Stack (M1)

- [Ink 7](https://github.com/vadimdemedes/ink) + React 19 — TUI framework
- [meow](https://github.com/sindresorhus/meow) — CLI argument parsing
- [which](https://github.com/npm/node-which) — cross-platform binary detection
- [vitest](https://vitest.dev/) — tests
- TypeScript (ESM, `moduleResolution: Bundler`)

## Layout

```
cli/
├── src/
│   ├── cli.tsx                # entry point + command routing
│   ├── lib/
│   │   └── checks.ts          # version-check helpers
│   ├── components/
│   │   └── Layout.tsx         # shared header / body / status frame
│   └── commands/
│       ├── version.tsx
│       └── doctor.tsx
└── test/
    └── checks.test.ts
```

## License

MIT.
