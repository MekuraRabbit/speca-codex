# Security Agents - Multi-Phase Security Analysis System

An automated security analysis system using OpenAI Agents SDK for comprehensive Bug Bounty research and vulnerability assessment.

## Overview

This system performs multi-phase security analysis for blockchain projects, specifically designed for Bug Bounty programs. It uses GPT-4o with WebSearch capabilities to analyze Bug Bounty scopes, technical specifications, and generate attack scenarios.

## How to use

```
uv sync
uv run python -m utils.static_analyzer ../contracts/src/ -v
claude --dangerously-skip-permissions
```