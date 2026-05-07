"""
Codex app-server runner.

This runner uses the Codex app-server JSON-RPC protocol instead of launching a
fresh ``codex exec`` process per batch. SPECA remains the scheduler: it creates
batches, assigns workers, owns output paths, and collects partial results. The
app-server owns long-lived Codex threads, progress notifications, turn diffs,
and thread state.
"""

from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import aiofiles

from .codex_adapter import (
    build_codex_prompt,
    codex_model_selection_from_config,
    codex_reasoning_effort_from_config,
    codex_service_tier_from_config,
)
from .codex_bin import resolve_codex_bin
from .runner import ClaudeRunner


_CODEX_BIN = resolve_codex_bin()
_READER_CANCEL_TIMEOUT_SECONDS = 2
_WEBSOCKET_CLOSE_TIMEOUT_SECONDS = 5


def _int_token(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return max(0, value)
    if isinstance(value, float):
        return max(0, int(value))
    return 0


class CodexAppServerError(RuntimeError):
    """Raised when the Codex app-server protocol fails."""


@dataclass
class TurnCapture:
    """Per-turn app-server telemetry captured for reducer/diff collection."""

    thread_id: str
    turn_id: str
    notifications: list[dict[str, Any]] = field(default_factory=list)
    text_parts: list[str] = field(default_factory=list)
    token_usage: dict[str, Any] = field(default_factory=dict)
    diff: str = ""
    completed: dict[str, Any] | None = None

    @property
    def text(self) -> str:
        return "".join(self.text_parts)


class CodexAppServerClient:
    """Small JSON-RPC client for ``codex app-server`` over websocket."""

    def __init__(
        self,
        *,
        url: str | None,
        cwd: Path,
        timeout_seconds: int,
    ) -> None:
        self.url = url
        self.cwd = cwd
        self.timeout_seconds = timeout_seconds
        self._owns_process = url is None
        self._process: subprocess.Popen[Any] | None = None
        self._ws: Any = None
        self._reader_task: asyncio.Task[None] | None = None
        self._send_lock = asyncio.Lock()
        self._next_id = 1
        self._pending: dict[int, asyncio.Future[Any]] = {}
        self._captures: dict[tuple[str, str], TurnCapture] = {}
        self._completion_waiters: dict[tuple[str, str], asyncio.Future[dict[str, Any]]] = {}
        self._completed: dict[tuple[str, str], dict[str, Any]] = {}
        self._raw_notifications: list[dict[str, Any]] = []

    async def __aenter__(self) -> "CodexAppServerClient":
        await self.connect()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def connect(self) -> None:
        if self._ws is not None:
            return

        try:
            import websockets
        except ImportError as e:  # pragma: no cover - dependency guard
            raise CodexAppServerError(
                "websockets is required for Codex app-server mode. "
                "Install uvicorn[standard] or websockets."
            ) from e

        if self.url is None:
            self.url = await self._start_local_server()

        last_error: Exception | None = None
        for _ in range(80):
            try:
                self._ws = await websockets.connect(self.url, max_size=None)
                break
            except Exception as e:  # pragma: no cover - timing dependent
                last_error = e
                if self._process and self._process.poll() is not None:
                    break
                await asyncio.sleep(0.25)

        if self._ws is None:
            raise CodexAppServerError(f"Could not connect to {self.url}: {last_error}")

        self._reader_task = asyncio.create_task(self._reader_loop())
        await self.request(
            "initialize",
            {
                "clientInfo": {
                    "name": "speca",
                    "title": "SPECA",
                    "version": "0.1.0",
                },
                "capabilities": {"experimentalApi": True},
            },
        )

    async def close(self) -> None:
        if self._reader_task is not None:
            reader_task = self._reader_task
            self._reader_task = None
            reader_task.cancel()
            try:
                await asyncio.wait_for(
                    reader_task,
                    timeout=_READER_CANCEL_TIMEOUT_SECONDS,
                )
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            except Exception:
                pass
        if self._ws is not None:
            ws = self._ws
            self._ws = None
            try:
                await asyncio.wait_for(
                    ws.close(),
                    timeout=_WEBSOCKET_CLOSE_TIMEOUT_SECONDS,
                )
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            except Exception:
                pass
        if self._process is not None and self._owns_process:
            if self._process.returncode is None:
                self._process.terminate()
                try:
                    await asyncio.to_thread(self._process.wait, timeout=5)
                except subprocess.TimeoutExpired:
                    self._process.kill()
                    await asyncio.to_thread(self._process.wait)
            self._process = None

    async def _start_local_server(self) -> str:
        port = self._reserve_loopback_port()
        url = f"ws://127.0.0.1:{port}"
        self._process = subprocess.Popen(
            [_CODEX_BIN, "app-server", "--listen", url],
            cwd=str(self.cwd),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return url

    @staticmethod
    def _reserve_loopback_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return int(s.getsockname()[1])

    async def request(self, method: str, params: Any = None) -> Any:
        if self._ws is None:
            await self.connect()

        request_id = self._next_id
        self._next_id += 1
        loop = asyncio.get_running_loop()
        future: asyncio.Future[Any] = loop.create_future()
        self._pending[request_id] = future
        payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        async with self._send_lock:
            await self._ws.send(json.dumps(payload, ensure_ascii=False))

        try:
            return await asyncio.wait_for(
                future,
                timeout=max(30, self.timeout_seconds),
            )
        finally:
            self._pending.pop(request_id, None)

    async def _reader_loop(self) -> None:
        assert self._ws is not None
        try:
            async for raw in self._ws:
                try:
                    message = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if isinstance(message, list):
                    for item in message:
                        await self._handle_message(item)
                else:
                    await self._handle_message(message)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            for future in list(self._pending.values()):
                if not future.done():
                    future.set_exception(CodexAppServerError(str(e)))

    async def _handle_message(self, message: dict[str, Any]) -> None:
        if "id" in message and ("result" in message or "error" in message):
            future = self._pending.get(message["id"])
            if not future or future.done():
                return
            if "error" in message:
                future.set_exception(CodexAppServerError(str(message["error"])))
            else:
                future.set_result(message.get("result"))
            return

        if "id" in message and "method" in message:
            await self._answer_server_request(message)
            return

        if "method" in message:
            self._handle_notification(message)

    async def _answer_server_request(self, message: dict[str, Any]) -> None:
        """Respond conservatively to server-initiated requests.

        Normal SPECA app-server runs use approvalPolicy="never" and
        sandbox="danger-full-access", so approvals should not appear. If they
        do, decline instead of silently granting privileges.
        """
        method = str(message.get("method", ""))
        request_id = message.get("id")
        if method == "item/commandExecution/requestApproval":
            result: Any = {"decision": "decline"}
        elif method == "item/fileChange/requestApproval":
            result = {"decision": "decline"}
        elif method in {"applyPatchApproval", "execCommandApproval"}:
            result = {"decision": "denied"}
        elif method == "item/tool/requestUserInput":
            result = {"answers": {}}
        elif method == "mcpServer/elicitation/request":
            result = {"action": "decline", "content": None, "_meta": None}
        else:
            error = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"SPECA client does not implement {method}",
                },
            }
            async with self._send_lock:
                await self._ws.send(json.dumps(error))
            return

        response = {"jsonrpc": "2.0", "id": request_id, "result": result}
        async with self._send_lock:
            await self._ws.send(json.dumps(response))

    def _handle_notification(self, message: dict[str, Any]) -> None:
        self._raw_notifications.append(message)
        method = message.get("method")
        params = message.get("params") or {}
        if not isinstance(params, dict):
            return

        thread_id, turn_id = self._notification_ids(params)

        if isinstance(thread_id, str) and isinstance(turn_id, str):
            key = (thread_id, turn_id)
            capture = self._captures.get(key)
            if capture is not None:
                self._apply_notification_to_capture(capture, message)

            if method == "turn/completed":
                self._completed[key] = params
                waiter = self._completion_waiters.get(key)
                if waiter and not waiter.done():
                    waiter.set_result(params)
        elif isinstance(thread_id, str) and method == "thread/tokenUsage/updated":
            for (capture_thread_id, _), capture in self._captures.items():
                if capture_thread_id == thread_id:
                    self._apply_notification_to_capture(capture, message)

    @staticmethod
    def _notification_ids(params: dict[str, Any]) -> tuple[Any, Any]:
        thread_id = params.get("threadId")
        turn = params.get("turn")
        turn_id = params.get("turnId")
        if isinstance(turn, dict):
            turn_id = turn.get("id", turn_id)
        return thread_id, turn_id

    def _register_capture(self, capture: TurnCapture) -> None:
        """Register a turn capture and replay early notifications."""
        key = (capture.thread_id, capture.turn_id)
        self._captures[key] = capture
        for message in self._raw_notifications:
            if self._notification_matches_capture(capture, message):
                self._apply_notification_to_capture(capture, message)
        if key in self._completed:
            capture.completed = self._completed[key]

    @classmethod
    def _notification_matches_capture(
        cls,
        capture: TurnCapture,
        message: dict[str, Any],
    ) -> bool:
        params = message.get("params") or {}
        if not isinstance(params, dict):
            return False
        thread_id, turn_id = cls._notification_ids(params)
        if thread_id != capture.thread_id:
            return False
        if isinstance(turn_id, str):
            return turn_id == capture.turn_id
        return message.get("method") == "thread/tokenUsage/updated"

    @staticmethod
    def _apply_notification_to_capture(
        capture: TurnCapture,
        message: dict[str, Any],
    ) -> None:
        capture.notifications.append(message)
        method = message.get("method")
        params = message.get("params") or {}
        if not isinstance(params, dict):
            return
        if method == "item/agentMessage/delta":
            delta = params.get("delta")
            if isinstance(delta, str):
                capture.text_parts.append(delta)
        elif method == "turn/diff/updated":
            diff = params.get("diff")
            if isinstance(diff, str):
                capture.diff = diff
        elif method == "thread/tokenUsage/updated":
            token_usage = params.get("tokenUsage")
            if isinstance(token_usage, dict):
                capture.token_usage = token_usage
        elif method == "turn/completed":
            capture.completed = params

    async def run_turn(
        self,
        *,
        prompt: str,
        cwd: Path,
        model: str | None,
        effort: str | None,
        service_tier: str | None,
        timeout_seconds: int,
        developer_instructions: str,
    ) -> tuple[dict[str, Any], TurnCapture]:
        thread_params: dict[str, Any] = {
            "cwd": str(cwd),
            "approvalPolicy": "never",
            "sandbox": "danger-full-access",
            "serviceName": "speca",
            "developerInstructions": developer_instructions,
            "ephemeral": False,
        }
        if model:
            thread_params["model"] = model
        if service_tier:
            thread_params["serviceTier"] = service_tier

        thread_response = await self.request("thread/start", thread_params)
        thread = thread_response["thread"]
        thread_id = thread["id"]

        turn_response = await self.request(
            "turn/start",
            {
                "threadId": thread_id,
                "input": [
                    {
                        "type": "text",
                        "text": prompt,
                        "text_elements": [],
                    }
                ],
                "cwd": str(cwd),
                "approvalPolicy": "never",
                "sandboxPolicy": {"type": "dangerFullAccess"},
                **({"model": model} if model else {}),
                **({"effort": effort} if effort else {}),
                **({"serviceTier": service_tier} if service_tier else {}),
            },
        )
        turn = turn_response["turn"]
        turn_id = turn["id"]
        capture = TurnCapture(thread_id=thread_id, turn_id=turn_id)
        key = (thread_id, turn_id)
        self._register_capture(capture)

        completed = self._completed.get(key)
        if completed is None:
            waiter: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
            self._completion_waiters[key] = waiter
            completed = await asyncio.wait_for(waiter, timeout=timeout_seconds)
        capture.completed = completed
        self._completion_waiters.pop(key, None)
        return thread_response, capture


class CodexAppRunner(ClaudeRunner):
    """Run SPECA batches as Codex app-server threads."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # App-server turns may run from isolated worktrees. Keep scheduler
        # artifacts absolute so workers do not write outputs under a worktree.
        self.output_dir = self.output_dir.resolve()
        self.log_dir = self.output_dir / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.debug_root = self.output_dir / ".codex_app_debug"
        self.debug_root.mkdir(parents=True, exist_ok=True)
        self.thread_meta_dir = self.output_dir / "codex_app_threads"
        self.thread_meta_dir.mkdir(parents=True, exist_ok=True)
        self._client: CodexAppServerClient | None = None
        self._client_lock = asyncio.Lock()
        self._worktrees: dict[int, Path] = {}

    async def _get_client(self) -> CodexAppServerClient:
        async with self._client_lock:
            if self._client is None:
                self._client = CodexAppServerClient(
                    url=self.config.codex_app_server_url
                    or self.config.runtime_env.get("SPECA_CODEX_APP_SERVER_URL"),
                    cwd=Path.cwd(),
                    timeout_seconds=self.config.timeout_seconds,
                )
                await self._client.connect()
            return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None

    async def _execute_batch(
        self,
        batch: list[dict[str, Any]],
        worker_id: int,
        batch_index: int,
    ) -> list[dict[str, Any]] | None:
        timestamp = int(time.time())
        phase_id = self.config.phase_id
        directory_mode = self.config.output_mode == "directory"

        partial_base = f"{phase_id}_PARTIAL"
        queue_path = self.output_dir / f"{phase_id}_ASYNC_QUEUE_W{worker_id}B{batch_index}_{timestamp}.json"
        context_path = self.output_dir / f"{phase_id}_CONTEXT_W{worker_id}B{batch_index}_{timestamp}.json"
        log_file = self.log_dir / f"{phase_id}_w{worker_id}b{batch_index}_{timestamp}.appserver.jsonl"

        if directory_mode:
            batch_output_dir = self.output_dir / "graphs" / f"batch_w{worker_id}b{batch_index}_{timestamp}"
            batch_output_dir.mkdir(parents=True, exist_ok=True)
            result_parse_path = batch_output_dir / ".no_result_file"
            output_kwargs: dict[str, str] = {"output_dir": str(batch_output_dir)}
        else:
            result_parse_path = self.output_dir / f"{partial_base}_W{worker_id}B{batch_index}_{timestamp}.json"
            output_kwargs = {"output_file": str(result_parse_path)}

        queue_payload = self._build_queue_payload(batch, worker_id, str(context_path))
        context_payload = self._build_context_payload(batch)
        self._save_json(queue_path, queue_payload)
        self._save_json(context_path, context_payload)

        prompt_content = self._build_prompt(
            worker_id=worker_id,
            queue_file=str(queue_path),
            context_file=str(context_path),
            batch_size=len(batch),
            iteration=batch_index,
            timestamp=timestamp,
            **output_kwargs,
        )
        cwd = self._batch_cwd(worker_id)
        client = await self._get_client()
        requested_model, model_source = codex_model_selection_from_config(self.config)
        requested_effort, effort_source = codex_reasoning_effort_from_config(self.config)
        requested_service_tier, service_tier_source = codex_service_tier_from_config(
            self.config
        )

        try:
            thread_response, capture = await client.run_turn(
                prompt=prompt_content,
                cwd=cwd,
                model=requested_model,
                effort=requested_effort,
                service_tier=requested_service_tier,
                timeout_seconds=self.config.timeout_seconds,
                developer_instructions=self._developer_instructions(),
            )
        except asyncio.TimeoutError:
            await self._write_log(
                log_file,
                [
                    {
                        "type": "result",
                        "subtype": "timeout",
                        "is_error": True,
                        "result": "Codex app-server turn timed out",
                    }
                ],
            )
            return None
        except Exception as e:
            error_text = "".join(
                traceback.format_exception(type(e), e, e.__traceback__)
            ).strip()
            await self._write_log(
                log_file,
                [
                    {
                        "type": "result",
                        "subtype": "error",
                        "is_error": True,
                        "result": error_text,
                    }
                ],
            )
            return None

        final_turn = (capture.completed or {}).get("turn", {})
        status = final_turn.get("status")
        diff_text = self._diff_for_capture(capture, cwd)
        self._save_thread_metadata(
            worker_id=worker_id,
            batch_index=batch_index,
            timestamp=timestamp,
            cwd=cwd,
            thread_response=thread_response,
            capture=capture,
            final_status=status,
            diff_text=diff_text,
            requested_model=requested_model,
            model_source=model_source,
            requested_effort=requested_effort,
            effort_source=effort_source,
            requested_service_tier=requested_service_tier,
            service_tier_source=service_tier_source,
        )

        log_messages = [
            {"type": "thread_start", "response": thread_response},
            *capture.notifications,
            {
                "type": "result",
                "subtype": "success" if status == "completed" else str(status),
                "is_error": status != "completed",
                "thread_id": capture.thread_id,
                "turn_id": capture.turn_id,
                "result": capture.text,
                "diff": diff_text,
            },
        ]
        await self._write_log(log_file, log_messages)

        if status != "completed":
            return None

        await self._record_cost_usage(capture, worker_id, batch_index)

        results = self._parse_results(result_parse_path)
        if not results:
            results = self._parse_results_from_log(log_file)
        if directory_mode and not results:
            results = self._parse_directory_results(batch_output_dir, context_path)
        if not directory_mode and results:
            result_parse_path.unlink(missing_ok=True)
        return results

    async def _record_cost_usage(
        self,
        capture: TurnCapture,
        worker_id: int,
        batch_index: int,
    ) -> None:
        if not self.cost_tracker:
            return

        usage = self._usage_from_capture(capture)
        if not any(
            usage[key]
            for key in (
                "input_tokens",
                "output_tokens",
                "cache_read_tokens",
                "cache_creation_tokens",
            )
        ):
            return

        await self.cost_tracker.record_usage(
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
            cache_read_tokens=usage["cache_read_tokens"],
            cache_creation_tokens=usage["cache_creation_tokens"],
            num_turns=usage["num_turns"],
            worker_id=worker_id,
            batch_index=batch_index,
        )

    @staticmethod
    def _usage_from_capture(capture: TurnCapture) -> dict[str, int]:
        total = capture.token_usage.get("total", {})
        if not isinstance(total, dict):
            total = {}

        input_tokens = _int_token(total.get("inputTokens"))
        cache_read_tokens = _int_token(total.get("cachedInputTokens"))
        output_tokens = _int_token(total.get("outputTokens"))

        return {
            "input_tokens": max(0, input_tokens - cache_read_tokens),
            "output_tokens": output_tokens,
            "cache_read_tokens": cache_read_tokens,
            "cache_creation_tokens": 0,
            "num_turns": 1 if input_tokens or output_tokens else 0,
        }

    def _diff_for_capture(self, capture: TurnCapture, cwd: Path) -> str:
        if not self.config.isolated_worktrees:
            return ""
        return capture.diff or self._git_diff(cwd)

    def _build_prompt(self, **kwargs: Any) -> str:
        prompt = super()._build_prompt(**kwargs)
        return build_codex_prompt(
            self.config,
            self._worker_adapter_instructions(),
            prompt,
        )

    @staticmethod
    def _developer_instructions() -> str:
        return (
            "You are a SPECA worker controlled by the SPECA scheduler. "
            "Operate only within repositories and systems the operator owns, "
            "maintains, or is explicitly authorized to assess. "
            "Treat BUG_BOUNTY_SCOPE and TARGET_INFO as the authorized boundary. "
            "Keep the queue/context/output contract exactly. Write only the "
            "requested SPECA artifacts unless the prompt explicitly asks for "
            "source edits."
        )

    @staticmethod
    def _worker_adapter_instructions() -> str:
        return """<codex_app_worker_adapter>
You are running as a Codex app-server turn under the SPECA scheduler.

Preserve the worker contract exactly:
- Read the queue/context paths named in the prompt.
- Produce the requested output file or output directory.
- Keep all normal SPECA schemas, field names, phase names, and partial-result
  conventions unchanged.
- Treat BUG_BOUNTY_SCOPE and TARGET_INFO as the authorized scope for this run.
  Do not expand analysis to unrelated repositories, live services, accounts, or
  infrastructure.
- Resolve any `outputs/...` path before reading it. Use the output root implied
  by the absolute QUEUE_FILE, CONTEXT_FILE, OUTPUT_FILE, or OUTPUT_DIR paths;
  never probe repository-root `outputs/` as a fallback for run artifacts.
- For target code, read TARGET_INFO.local_checkout from the resolved output root
  and resolve it as the target checkout root. If local_checkout is absolute, use
  it as-is. If it is relative, resolve it relative to the worker cwd/workspace,
  not relative to the output root. Never build OUTPUT_ROOT/target_workspace,
  outputs/target_workspace, or outputs/rehearsal_dvd/target_workspace. Restrict
  file reads/searches to the resolved checkout. Do not list/search its parent
  `target_workspace`, sibling paths, the SPECA repo root, or live services.
- If this worker is running in an isolated worktree, use that worktree for code
  inspection or source edits, but still write SPECA output artifacts to the
  absolute output paths named in the prompt.
- If the original phase prompt mentions `outputs/...`, translate that path to
  the output root implied by the absolute QUEUE_FILE, CONTEXT_FILE, OUTPUT_FILE,
  or OUTPUT_DIR paths instead of using repository-root `outputs/`.
- Do not edit source code, docs, prompts, tests, or config unless the worker
  prompt explicitly asks for those files.

Tool translation:
- If the prompt says Read, use shell commands to read files.
- If the prompt says Write, create the requested output file with shell commands.
- If the prompt says Grep/Glob, use fast file search commands available in the
  environment. If `rg` is unavailable or fails with "Access is denied" on
  Windows, do not retry `rg`; immediately fall back to PowerShell
  `Get-ChildItem` plus `Select-String` under the resolved checkout.
- If the prompt references a Claude slash skill, perform the described task
  directly in Codex while preserving the required JSON/output contract.
</codex_app_worker_adapter>"""

    def _batch_cwd(self, worker_id: int) -> Path:
        base_cwd = Path(self.config.workdir or Path.cwd()).resolve()
        if not self.config.isolated_worktrees:
            return base_cwd

        if worker_id in self._worktrees:
            return self._worktrees[worker_id]

        repo_root = self._git_repo_root(base_cwd)
        output_slug = self._slug(str(self.output_dir.resolve()))
        worktree_root = Path(self.config.worktree_root)
        if not worktree_root.is_absolute():
            worktree_root = repo_root / worktree_root
        worktree = worktree_root / f"{self.config.phase_id}_{output_slug}_w{worker_id}"
        if not self._looks_like_worktree(worktree):
            worktree.parent.mkdir(parents=True, exist_ok=True)
            base_ref = self.config.worktree_base_ref or "HEAD"
            env = os.environ.copy()
            env["GIT_LFS_SKIP_SMUDGE"] = "1"
            env["GIT_TERMINAL_PROMPT"] = "0"
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo_root),
                    "worktree",
                    "add",
                    "--detach",
                    str(worktree),
                    base_ref,
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
            )
        self._worktrees[worker_id] = worktree.resolve()
        return self._worktrees[worker_id]

    @staticmethod
    def _git_repo_root(cwd: Path) -> Path:
        result = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return Path(result.stdout.strip()).resolve()

    @staticmethod
    def _looks_like_worktree(path: Path) -> bool:
        return path.exists() and (path / ".git").exists()

    @staticmethod
    def _slug(text: str) -> str:
        safe = "".join(ch.lower() if ch.isalnum() else "-" for ch in text)
        safe = "-".join(part for part in safe.split("-") if part)
        return safe[-48:] or "run"

    @staticmethod
    def _git_diff(cwd: Path) -> str:
        try:
            result = subprocess.run(
                ["git", "-C", str(cwd), "diff", "--binary"],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except Exception:
            return ""
        return result.stdout if result.returncode == 0 else ""

    def _save_thread_metadata(
        self,
        *,
        worker_id: int,
        batch_index: int,
        timestamp: int,
        cwd: Path,
        thread_response: dict[str, Any],
        capture: TurnCapture,
        final_status: str | None,
        diff_text: str,
        requested_model: str | None,
        model_source: str,
        requested_effort: str | None,
        effort_source: str,
        requested_service_tier: str | None,
        service_tier_source: str,
    ) -> None:
        base = f"{self.config.phase_id}_W{worker_id}B{batch_index}_{timestamp}"
        diff_file: Path | None = None
        if diff_text:
            diff_file = self.thread_meta_dir / f"{base}.diff"
            diff_file.write_text(diff_text, encoding="utf-8")

        thread = thread_response.get("thread", {})
        metadata = {
            "run_id": self.config.runtime_env.get("SPECA_RUN_ID"),
            "phase_id": self.config.phase_id,
            "worker_id": worker_id,
            "batch_index": batch_index,
            "thread_id": capture.thread_id,
            "turn_id": capture.turn_id,
            "status": final_status,
            "cwd": str(cwd),
            "thread_path": thread.get("path"),
            "requested_model": requested_model,
            "model_source": model_source,
            "requested_effort": requested_effort,
            "effort_source": effort_source,
            "requested_service_tier": requested_service_tier,
            "service_tier_source": service_tier_source,
            "diff_file": str(diff_file) if diff_file else None,
            "has_diff": bool(diff_text),
            "notification_count": len(capture.notifications),
        }
        path = self.thread_meta_dir / f"{base}.json"
        path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    @staticmethod
    async def _write_log(path: Path, messages: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(path, mode="w", encoding="utf-8") as f:
            for message in messages:
                await f.write(json.dumps(message, ensure_ascii=False) + "\n")
