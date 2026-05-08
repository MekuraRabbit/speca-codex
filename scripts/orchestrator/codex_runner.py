"""
Codex Runner Module

Executes SPECA batches with the Codex CLI (`codex exec`) while preserving the
same queue/context/output contract used by the existing Claude runner.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .codex_adapter import build_codex_prompt, codex_model_from_config
from .codex_bin import resolve_codex_bin
from .codex_sandbox import codex_exec_sandbox_args
from .runner import ClaudeRunner


_CODEX_BIN = resolve_codex_bin()


class CodexRunner(ClaudeRunner):
    """Run a SPECA batch through Codex CLI instead of Claude Code CLI."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.debug_root = self.output_dir / ".codex_debug"
        self.debug_root.mkdir(parents=True, exist_ok=True)

    def _build_prompt(self, **kwargs: Any) -> str:
        prompt = super()._build_prompt(**kwargs)
        return build_codex_prompt(
            self.config,
            self._codex_adapter_instructions(),
            prompt,
        )

    def _build_env(self, **kwargs: Any) -> dict[str, str]:
        env = os.environ.copy()
        env.update(self.config.runtime_env)
        env["SPECA_OUTPUT_DIR"] = str(self.output_dir)
        for key, value in kwargs.items():
            env[key.upper()] = str(value)
        return env

    def _build_cmd(self, prompt_content: str) -> tuple[list[str], bytes | None]:
        """Build the Codex CLI command.

        Codex accepts stdin when the prompt argument is "-". We always pipe the
        prompt to avoid command-line length and quoting issues on Windows.
        """
        cmd = [
            _CODEX_BIN,
            "exec",
            "--json",
            "--skip-git-repo-check",
        ]
        cmd.extend(codex_exec_sandbox_args(
            self.config,
            writable_roots=[self.output_dir],
        ))
        model = codex_model_from_config(self.config)
        if model:
            cmd.extend(["--model", model])
        cmd.append("-")
        return cmd, prompt_content.encode("utf-8")

    @staticmethod
    def _codex_adapter_instructions() -> str:
        return """<codex_worker_adapter>
You are running inside Codex CLI (`codex exec`) as a non-interactive SPECA worker.

Preserve the worker contract exactly:
- Read the queue/context paths named in the prompt.
- Produce the requested output file or output directory.
- Keep all normal SPECA schemas, field names, phase names, and partial-result
  conventions unchanged.
- Treat BUG_BOUNTY_SCOPE and TARGET_INFO as the authorized scope for this run.
  Do not expand analysis to unrelated repositories, live services, accounts, or
  infrastructure.
- Resolve any `outputs/...` path before reading it. Use SPECA_OUTPUT_DIR or the
  output root implied by the queue/context/output paths; never probe
  repository-root `outputs/` as a fallback for run artifacts.
- For target code, read TARGET_INFO.local_checkout from the resolved output root
  and resolve it as the target checkout root. If local_checkout is absolute, use
  it as-is. If it is relative, resolve it relative to the worker cwd/workspace,
  not relative to the output root. Never build OUTPUT_ROOT/target_workspace,
  outputs/target_workspace, or outputs/rehearsal_dvd/target_workspace. Restrict
  file reads/searches to the resolved checkout. Do not list/search its parent
  `target_workspace`, sibling paths, the SPECA repo root, or live services.
- If the original phase prompt mentions `outputs/...`, translate that path to
  SPECA_OUTPUT_DIR or to the output root implied by the queue/context/output
  paths instead of assuming repository-root `outputs/`.
- Do not edit source code, docs, prompts, tests, or config unless the worker
  prompt explicitly asks for those files. For normal phase work, write only the
  requested SPECA output artifacts.

Tool translation:
- If the prompt says Read, use shell commands to read files.
- If the prompt says Write, create the requested output file with shell commands.
- If the prompt says Grep/Glob, use fast file search commands available in the
  environment. If `rg` is unavailable or fails with "Access is denied" on
  Windows, do not retry `rg`; immediately fall back to PowerShell
  `Get-ChildItem` plus `Select-String` under the resolved checkout.
- If the prompt references a Claude slash skill, perform the described task
  directly in Codex while preserving the required JSON/output contract.

Finish with a concise summary and the output path, matching the phase prompt.
</codex_worker_adapter>"""
