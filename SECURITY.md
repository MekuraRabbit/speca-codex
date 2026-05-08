# Security Policy

SPECA Codex is a security-audit tool, so reports can fall into two different
categories. Please use the right channel for the type of issue.

## Vulnerabilities In This Repository

If you find a vulnerability in this repository, its GitHub Actions workflows,
the local FastAPI server, runner isolation, generated artifacts, or anything
that could expose secrets or run outside the intended scope, please do not open
a public issue first.

Use GitHub's private vulnerability reporting flow:

https://github.com/MekuraRabbit/speca-codex/security/advisories/new

Please include:

- the affected commit or release tag
- the impacted component
- clear reproduction steps
- whether a token, local path, target checkout, or generated output could be
  exposed
- any suggested mitigation, if known

## Findings In Audit Targets

Findings produced by SPECA are candidate findings. Validate them manually before
reporting them to a vendor or bug-bounty program.

Do not file public issues in this repository for vulnerabilities in third-party
targets analyzed with SPECA. Report those findings through the target project's
own coordinated disclosure or bug-bounty process.

## Supported Versions

This fork does not currently publish stable release branches. Security fixes are
handled on the default branch unless a tagged release states otherwise.
