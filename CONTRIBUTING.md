# Contributing

Thanks for helping improve SPECA Codex. This fork keeps the upstream Claude
workflow available while adding Codex App support, so changes should preserve
both paths unless the issue explicitly says otherwise.

## Before Opening An Issue

- Search existing issues first.
- Use the bug or feature template when one fits.
- Include a minimal reproducer and the affected commit when reporting a bug.
- Redact API keys, tokens, account identifiers, private repository names, and
  local absolute paths from logs or screenshots.
- For security-sensitive issues, use `SECURITY.md` instead of a public issue.

## Pull Requests

Keep PRs focused. A good PR normally touches one pipeline phase, one runner
surface, or one documentation area at a time.

Before opening a PR:

1. Create a topic branch from `main`.
2. Update tests when behavior or schema contracts change.
3. Keep `README.md` and `README.ja.md` aligned when user-facing behavior or
   public validation notes change.
4. Preserve `CLAUDE.md`, `.claude/`, and the legacy Claude runner path unless
   the change is explicitly about removing or replacing legacy behavior.
5. Run the test suite:

```bash
uv run python -m pytest tests/ -v --tb=short
```

On Windows, if `uv sync` is blocked by the legacy SWE-agent dependency checkout,
the lightweight Codex App environment used by this fork can run the tests with:

```powershell
.venv/Scripts/python.exe -m pytest tests/ -v --tb=short
```

## Schema And Prompt Changes

If a change affects an inter-phase contract, update the schema and the relevant
worker prompt together. Partial result and resume behavior are first-class
features; do not break existing `outputs/*_PARTIAL_*.json` resume semantics
without a migration path.

## Public Wording

Be conservative in public claims. Local rehearsals are compatibility and quality
checks, not proof that the tool will find vulnerabilities in arbitrary targets.
Do not present estimated API-style cost fields as actual spend unless the API
runner was explicitly used.
