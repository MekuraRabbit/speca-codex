"""Path normalization helpers for the local SPECA API server."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_OUTPUT_ROOT = REPO_ROOT / "outputs"
SERVER_WORKTREE_ROOT = REPO_ROOT / ".codex" / "worktrees"


def normalize_output_dir(value: str | None) -> str | None:
    """Normalize a user supplied output_dir to a repo-relative outputs path."""
    return _normalize_relative_child(
        value,
        base=SERVER_OUTPUT_ROOT,
        field_name="output_dir",
    )


def normalize_worktree_root(value: str | None) -> str | None:
    """Normalize a user supplied worktree_root to a repo-relative worktree path."""
    return _normalize_relative_child(
        value,
        base=SERVER_WORKTREE_ROOT,
        field_name="worktree_root",
    )


def resolve_child_path(value: str, base: Path, field_name: str) -> Path:
    """Resolve a metadata path and ensure it stays under ``base``.

    Unlike API request paths, metadata paths may already be absolute because
    Codex app-server records absolute diff file names. They are still accepted
    only when the resolved path remains inside the expected base directory.
    """
    if not value or not value.strip():
        raise ValueError(f"{field_name} must not be empty")

    raw = Path(value)
    if _has_parent_or_home_ref(raw):
        raise ValueError(f"{field_name} must not contain traversal")

    candidate = raw if raw.is_absolute() else base / raw
    resolved_base = base.resolve()
    resolved_candidate = candidate.resolve()
    if resolved_candidate != resolved_base and not resolved_candidate.is_relative_to(
        resolved_base
    ):
        raise ValueError(f"{field_name} must stay under {resolved_base}")
    return resolved_candidate


def _normalize_relative_child(
    value: str | None,
    *,
    base: Path,
    field_name: str,
) -> str | None:
    if value is None:
        return value
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")

    raw = Path(value)
    if raw.is_absolute():
        raise ValueError(f"{field_name} must be relative")
    if _has_parent_or_home_ref(raw):
        raise ValueError(f"{field_name} must not contain traversal")

    resolved_base = base.resolve()
    resolved_candidate = (REPO_ROOT / raw).resolve()
    if resolved_candidate != resolved_base and not resolved_candidate.is_relative_to(
        resolved_base
    ):
        relative_base = resolved_base.relative_to(REPO_ROOT).as_posix()
        raise ValueError(f"{field_name} must stay under {relative_base}")

    return resolved_candidate.relative_to(REPO_ROOT).as_posix()


def _has_parent_or_home_ref(path: Path) -> bool:
    return any(part == ".." or part.startswith("~") for part in path.parts)
