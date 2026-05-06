"""Tests for Codex executable resolution."""

from pathlib import Path

from scripts.orchestrator import codex_bin


def test_resolve_codex_bin_prefers_windows_vendor_exe(tmp_path: Path, monkeypatch):
    npm_root = tmp_path / "npm"
    vendor = (
        npm_root
        / "node_modules"
        / "@openai"
        / "codex"
        / "node_modules"
        / "@openai"
        / "codex-win32-x64"
        / "vendor"
        / "x86_64-pc-windows-msvc"
        / "codex"
        / "codex.exe"
    )
    vendor.parent.mkdir(parents=True)
    vendor.write_text("", encoding="utf-8")
    cmd = npm_root / "codex.cmd"
    cmd.write_text("", encoding="utf-8")

    def fake_which(name: str):
        if name == "codex.cmd":
            return str(cmd)
        return None

    monkeypatch.setattr(codex_bin.sys, "platform", "win32")
    monkeypatch.setattr(codex_bin.shutil, "which", fake_which)

    assert codex_bin.resolve_codex_bin() == str(vendor)
