"""Validation for the target checkout described by TARGET_INFO.json."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from .paths import get_output_root
from .schemas import TargetInfo


TARGET_CHECKOUT_PHASES = {"02c", "03", "04", "05"}
SKIP_VALIDATION_ENV = "SPECA_ALLOW_UNVERIFIED_TARGET_CHECKOUT"


class TargetCheckoutValidationError(RuntimeError):
    """Raised when TARGET_INFO.local_checkout does not match its contract."""


@dataclass(frozen=True)
class TargetCheckoutValidation:
    """Resolved checkout details used only for pre-flight validation."""

    target_info: TargetInfo
    target_info_path: Path
    checkout_path: Path
    git_root: Path
    head_commit: str
    remote_url: str = ""


def _env_flag_enabled(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def validate_target_checkout_for_phase(
    phase_id: str,
    *,
    output_dir: Path | str | None = None,
    cwd: Path | str | None = None,
    env: dict[str, str] | None = None,
) -> TargetCheckoutValidation | None:
    """Validate TARGET_INFO.local_checkout before target-code phases run.

    Returns validation details for target phases, ``None`` for phases that do
    not consume target code, or when the explicit trusted-run override is set.
    """

    if phase_id not in TARGET_CHECKOUT_PHASES:
        return None

    env_map = env if env is not None else os.environ
    if _env_flag_enabled(env_map.get(SKIP_VALIDATION_ENV)):
        return None

    root = Path(output_dir) if output_dir is not None else get_output_root()
    return validate_target_checkout(root / "TARGET_INFO.json", cwd=cwd)


def validate_target_checkout(
    target_info_path: Path | str,
    *,
    cwd: Path | str | None = None,
) -> TargetCheckoutValidation:
    """Validate that TARGET_INFO points at the pinned local Git checkout."""

    path = Path(target_info_path)
    if not path.exists():
        raise TargetCheckoutValidationError(
            f"{path} is required before phases 02c/03/04/05. "
            "Create TARGET_INFO.json with target_repo, target_commit, and "
            "local_checkout pointing at the pinned target checkout."
        )

    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        info = TargetInfo.model_validate(data)
    except Exception as exc:
        raise TargetCheckoutValidationError(f"{path} is not a valid TARGET_INFO.json: {exc}") from exc

    checkout_path = _resolve_checkout_path(info.local_checkout, cwd=cwd)
    if not checkout_path.exists():
        raise TargetCheckoutValidationError(
            f"TARGET_INFO.local_checkout does not exist: {info.local_checkout}"
        )
    if not checkout_path.is_dir():
        raise TargetCheckoutValidationError(
            f"TARGET_INFO.local_checkout is not a directory: {info.local_checkout}"
        )

    git_root = _git_root(checkout_path)
    if checkout_path.resolve() != git_root:
        raise TargetCheckoutValidationError(
            "TARGET_INFO.local_checkout must point at the target repository root. "
            f"Resolved {checkout_path.resolve()} inside Git root {git_root}."
        )

    head_commit = _git(git_root, "rev-parse", "HEAD")
    if not _commit_matches(head_commit, info.target_commit):
        raise TargetCheckoutValidationError(
            "TARGET_INFO target_commit does not match local_checkout HEAD. "
            f"TARGET_INFO={info.target_commit}, HEAD={head_commit}."
        )

    dirty = _git(git_root, "status", "--porcelain")
    if dirty:
        raise TargetCheckoutValidationError(
            "TARGET_INFO.local_checkout is dirty. Commit, stash, or clean the "
            f"target checkout first, or set {SKIP_VALIDATION_ENV}=1 for a "
            "trusted legacy/local run."
        )

    remote_url = _optional_git(git_root, "remote", "get-url", "origin")
    expected_repo = _repo_slug(info.target_repo)
    actual_repo = _repo_slug(remote_url)
    if expected_repo and actual_repo and expected_repo != actual_repo:
        raise TargetCheckoutValidationError(
            "TARGET_INFO target_repo does not match local_checkout origin. "
            f"TARGET_INFO={info.target_repo}, origin={remote_url}."
        )

    return TargetCheckoutValidation(
        target_info=info,
        target_info_path=path.resolve(),
        checkout_path=checkout_path.resolve(),
        git_root=git_root,
        head_commit=head_commit,
        remote_url=remote_url,
    )


def _resolve_checkout_path(local_checkout: str, *, cwd: Path | str | None = None) -> Path:
    checkout = Path(local_checkout)
    if checkout.is_absolute():
        return checkout.resolve()
    base = Path(cwd) if cwd is not None else Path.cwd()
    return (base / checkout).resolve()


def _git_root(path: Path) -> Path:
    root = _git(path, "rev-parse", "--show-toplevel")
    return Path(root).resolve()


def _git(cwd: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
        )
    except FileNotFoundError as exc:
        raise TargetCheckoutValidationError("git executable not found") from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or exc.stdout or "").strip()
        detail = f": {stderr}" if stderr else ""
        raise TargetCheckoutValidationError(
            f"TARGET_INFO.local_checkout is not a usable Git checkout{detail}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise TargetCheckoutValidationError("git command timed out while validating TARGET_INFO") from exc
    return result.stdout.strip()


def _optional_git(cwd: Path, *args: str) -> str:
    try:
        return _git(cwd, *args)
    except TargetCheckoutValidationError:
        return ""


def _commit_matches(head_commit: str, target_commit: str) -> bool:
    expected = target_commit.strip().lower()
    actual = head_commit.strip().lower()
    if not expected or not actual:
        return False
    return actual == expected or (len(expected) >= 7 and actual.startswith(expected))


def _repo_slug(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""

    candidate = raw
    parsed = urlparse(raw)
    if parsed.scheme and parsed.netloc:
        candidate = parsed.path
    elif "@" in raw and ":" in raw:
        candidate = raw.split(":", 1)[1]

    candidate = candidate.replace("\\", "/").strip("/")
    if candidate.endswith(".git"):
        candidate = candidate[:-4]

    parts = [part for part in candidate.split("/") if part]
    if len(parts) < 2:
        return ""
    owner, repo = parts[-2], parts[-1]
    if owner.endswith(":"):
        return ""
    return f"{owner}/{repo}".lower()
