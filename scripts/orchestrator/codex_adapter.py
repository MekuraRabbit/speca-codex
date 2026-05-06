"""Helpers for adapting Claude-oriented SPECA prompts to Codex workers."""

from __future__ import annotations

import os
from pathlib import Path

from .config import PhaseConfig


_CLAUDE_MODEL_MARKERS = ("claude", "sonnet", "opus", "haiku")


def build_codex_prompt(config: PhaseConfig, adapter: str, prompt: str) -> str:
    """Return a Codex prompt with adapter instructions and skill context.

    Some original SPECA prompts ask Claude Code to invoke slash skills such as
    ``/spec-discovery``. Codex does not execute Claude slash skills directly, so
    when a phase references a `.claude/skills/<name>/SKILL.md` file we inline
    that skill body as task context and instruct Codex to perform it directly.
    """
    skill_context = _load_referenced_skill(config, prompt)
    parts = [adapter]
    if skill_context:
        parts.append(skill_context)
    parts.append(prompt)
    return "\n\n".join(parts)


def codex_model_from_config(config: PhaseConfig) -> str | None:
    """Return the model name that is safe to pass to Codex.

    PhaseConfig still contains Claude-oriented defaults such as ``sonnet`` for
    the legacy runner. Passing those strings to Codex would select an invalid
    model, so Codex runners drop Claude model names and let Codex use its own
    configured default. A caller can still force a Codex model with
    ``SPECA_CODEX_MODEL`` or by setting ``config.model`` to a non-Claude name
    such as ``gpt-5.2``.
    """
    model, _ = codex_model_selection_from_config(config)
    return model


def codex_model_selection_from_config(config: PhaseConfig) -> tuple[str | None, str]:
    """Return the Codex model plus the source used for metadata."""
    explicit = config.runtime_env.get("SPECA_CODEX_MODEL")
    if explicit:
        return explicit, config.runtime_env.get("SPECA_CODEX_MODEL_SOURCE", "explicit")
    env_model = os.environ.get("SPECA_CODEX_MODEL")
    if env_model:
        return env_model, "env"
    model = config.model
    if not model:
        return None, "codex-app-default"
    if is_claude_model_name(model):
        return None, "codex-app-default"
    return model, "explicit"


def codex_reasoning_effort_from_config(
    config: PhaseConfig,
) -> tuple[str | None, str]:
    """Return the Codex reasoning effort plus its metadata source."""
    explicit = config.runtime_env.get("SPECA_CODEX_REASONING_EFFORT")
    if explicit:
        return explicit, config.runtime_env.get(
            "SPECA_CODEX_REASONING_EFFORT_SOURCE",
            "explicit",
        )
    env_effort = os.environ.get("SPECA_CODEX_REASONING_EFFORT")
    if env_effort:
        return env_effort, "env"
    return None, "codex-app-default"


def codex_service_tier_from_config(config: PhaseConfig) -> tuple[str | None, str]:
    """Return the Codex service tier plus its metadata source."""
    explicit = config.runtime_env.get("SPECA_CODEX_SERVICE_TIER")
    if explicit:
        return explicit, config.runtime_env.get(
            "SPECA_CODEX_SERVICE_TIER_SOURCE",
            "explicit",
        )
    env_tier = os.environ.get("SPECA_CODEX_SERVICE_TIER")
    if env_tier:
        return env_tier, "env"
    return None, "codex-app-default"


def is_claude_model_name(model: str) -> bool:
    lower = model.lower()
    return any(marker in lower for marker in _CLAUDE_MODEL_MARKERS)


def _load_referenced_skill(config: PhaseConfig, prompt: str) -> str:
    skill_path = config.skill_path
    if skill_path.name != "SKILL.md":
        return ""
    if ".claude" not in skill_path.parts:
        return ""

    skill_name = skill_path.parent.name
    if f"/{skill_name}" not in prompt:
        return ""
    if not skill_path.exists():
        return (
            "<codex_skill_context>\n"
            f"Referenced Claude skill /{skill_name} was not found at "
            f"{skill_path.as_posix()}. Perform the requested task directly "
            "from the phase prompt.\n"
            "</codex_skill_context>"
        )

    body = skill_path.read_text(encoding="utf-8", errors="replace")
    return (
        "<codex_skill_context>\n"
        f"The phase prompt references Claude slash skill /{skill_name}. "
        "Codex cannot invoke Claude slash skills directly, so execute the "
        "skill behavior described below as part of this worker turn.\n\n"
        f"--- {skill_path.as_posix()} ---\n"
        f"{body}\n"
        "</codex_skill_context>"
    )
