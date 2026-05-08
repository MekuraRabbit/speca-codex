from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.orchestrator.target_checkout import (
    SKIP_VALIDATION_ENV,
    TargetCheckoutValidationError,
    validate_target_checkout,
    validate_target_checkout_for_phase,
)


def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def _make_repo(path: Path, *, remote: str = "https://github.com/example/repo.git") -> str:
    path.mkdir(parents=True)
    _git(path, "init")
    _git(path, "config", "user.email", "speca@example.invalid")
    _git(path, "config", "user.name", "SPECA Test")
    (path / "README.md").write_text("target\n", encoding="utf-8")
    _git(path, "add", "README.md")
    _git(path, "commit", "-m", "initial")
    _git(path, "remote", "add", "origin", remote)
    return _git(path, "rev-parse", "HEAD")


def _write_target_info(output_dir: Path, local_checkout: str, commit: str, repo: str = "example/repo") -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "TARGET_INFO.json"
    path.write_text(
        json.dumps(
            {
                "target_repo": repo,
                "target_commit": commit,
                "target_commit_short": commit[:12],
                "local_checkout": local_checkout,
            }
        ),
        encoding="utf-8",
    )
    return path


def test_validate_target_checkout_accepts_clean_pinned_checkout(tmp_path):
    repo = tmp_path / "target_workspace" / "repo"
    head = _make_repo(repo)
    target_info = _write_target_info(
        tmp_path / "outputs",
        "target_workspace/repo",
        head,
    )

    result = validate_target_checkout(target_info, cwd=tmp_path)

    assert result.checkout_path == repo.resolve()
    assert result.git_root == repo.resolve()
    assert result.head_commit == head


def test_validate_target_checkout_accepts_short_commit_prefix(tmp_path):
    repo = tmp_path / "target_workspace" / "repo"
    head = _make_repo(repo)
    target_info = _write_target_info(
        tmp_path / "outputs",
        str(repo),
        head[:12],
    )

    assert validate_target_checkout(target_info).head_commit == head


def test_validate_target_checkout_rejects_missing_checkout(tmp_path):
    target_info = _write_target_info(
        tmp_path / "outputs",
        "target_workspace/missing",
        "a" * 40,
    )

    with pytest.raises(TargetCheckoutValidationError, match="does not exist"):
        validate_target_checkout(target_info, cwd=tmp_path)


def test_validate_target_checkout_rejects_non_root_subdirectory(tmp_path):
    repo = tmp_path / "target_workspace" / "repo"
    head = _make_repo(repo)
    subdir = repo / "contracts"
    subdir.mkdir()
    target_info = _write_target_info(tmp_path / "outputs", str(subdir), head)

    with pytest.raises(TargetCheckoutValidationError, match="repository root"):
        validate_target_checkout(target_info)


def test_validate_target_checkout_rejects_commit_mismatch(tmp_path):
    repo = tmp_path / "target_workspace" / "repo"
    _make_repo(repo)
    target_info = _write_target_info(tmp_path / "outputs", str(repo), "b" * 40)

    with pytest.raises(TargetCheckoutValidationError, match="target_commit"):
        validate_target_checkout(target_info)


def test_validate_target_checkout_rejects_dirty_checkout(tmp_path):
    repo = tmp_path / "target_workspace" / "repo"
    head = _make_repo(repo)
    (repo / "README.md").write_text("dirty\n", encoding="utf-8")
    target_info = _write_target_info(tmp_path / "outputs", str(repo), head)

    with pytest.raises(TargetCheckoutValidationError, match="dirty"):
        validate_target_checkout(target_info)


def test_validate_target_checkout_rejects_remote_mismatch(tmp_path):
    repo = tmp_path / "target_workspace" / "repo"
    head = _make_repo(repo, remote="https://github.com/example/repo.git")
    target_info = _write_target_info(
        tmp_path / "outputs",
        str(repo),
        head,
        repo="other/repo",
    )

    with pytest.raises(TargetCheckoutValidationError, match="target_repo"):
        validate_target_checkout(target_info)


def test_validate_target_checkout_for_phase_skips_non_target_phase(tmp_path):
    assert validate_target_checkout_for_phase("01a", output_dir=tmp_path / "outputs") is None


def test_validate_target_checkout_for_phase_honors_explicit_override(tmp_path):
    result = validate_target_checkout_for_phase(
        "03",
        output_dir=tmp_path / "outputs",
        env={SKIP_VALIDATION_ENV: "1"},
    )

    assert result is None


def test_cli_phase05_fails_before_writing_candidates_when_checkout_invalid(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    output_dir = tmp_path / "outputs" / "phase05"
    output_dir.mkdir(parents=True)
    _write_target_info(
        output_dir,
        "target_workspace/missing",
        "a" * 40,
    )
    (output_dir / "03_PARTIAL_W0B0_1.json").write_text(
        json.dumps({"audit_items": [], "metadata": {"processed_ids": []}}),
        encoding="utf-8",
    )
    (output_dir / "04_PARTIAL_W0B0_1.json").write_text(
        json.dumps({"reviewed_items": [], "metadata": {"processed_ids": []}}),
        encoding="utf-8",
    )

    env = dict(os.environ)
    env.pop(SKIP_VALIDATION_ENV, None)
    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "run_phase.py"),
            "--phase",
            "05",
            "--output-dir",
            str(output_dir),
        ],
        cwd=str(repo_root),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
    )

    assert result.returncode == 1
    assert "TARGET_INFO.local_checkout does not exist" in result.stderr
    assert not (output_dir / "05_POC_CANDIDATES.json").exists()
