# speca-cli

TUI front-end prototype for the [SPECA Codex fork](https://github.com/MekuraRabbit/speca-codex) security-audit pipeline.

> **Status:** early prototype. `version`, `doctor`, `auth login`, and `auth status`
> exist; run orchestration and browsing are still future work. The auth commands
> are historical prototype surfaces and are not used by the Codex App runner.
> The current Codex App runner path is documented in
> [`docs/CODEX_APP.md`](../docs/CODEX_APP.md).

## Quick start (development)

```bash
cd cli
npm install
npm run dev -- doctor       # run from source via tsx
npm run build               # compile to dist/
node dist/cli.js doctor     # run the built bundle
```

## Commands available now

| Command | Description |
|---|---|
| `speca version` | Print the speca-cli version |
| `speca doctor` | Check Node / uv / git / auth status |
| `speca auth login` | Historical Anthropic auth prototype; not used by the Codex App runner |
| `speca auth status` | Show currently saved auth records |
| `speca help` | Show usage |

Future milestones may add `init`, `run`, `browse`, `attach`, `config`, the live
pipeline dashboard, and the finding browser.

## Stack

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
│   ├── auth/                  # credential storage and auth checks
│   ├── components/
│   │   └── Layout.tsx         # shared header / body / status frame
│   └── commands/
│       ├── auth/              # commands/auth/
│       │   ├── login.tsx
│       │   └── status.tsx
│       ├── version.tsx
│       └── doctor.tsx
└── test/
    ├── auth.flow.test.ts
    ├── auth.store.test.ts
    └── checks.test.ts
```

## License

MIT.
