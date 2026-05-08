"""Bridge between FastAPI and the existing orchestrator.

Wraps the orchestrator to emit progress events via ProgressBus,
replacing tqdm output with SSE-compatible events.
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
from pathlib import Path
from typing import Any

# Ensure scripts/ is importable
_scripts_dir = str(Path(__file__).resolve().parent.parent / "scripts")
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from orchestrator import create_orchestrator
from orchestrator.base import BaseOrchestrator, PhaseAbortError
from orchestrator.codex_gui_model import resolve_codex_gui_settings
from orchestrator.paths import get_output_root, output_root_context
from orchestrator.runner import CircuitBreakerTripped, BudgetExceeded
from orchestrator.target_checkout import validate_target_checkout_for_phase

from .progress import ProgressBus, ProgressEvent, EventType
from .run_manager import RunManager, RunInfo, RunStatus
from .discord import send_phase_result


class InstrumentedOrchestrator:
    """Wraps an orchestrator to emit progress events instead of tqdm output."""

    def __init__(self, orch: BaseOrchestrator, bus: ProgressBus) -> None:
        self.orch = orch
        self.bus = bus
        # Replace execute_batches with our instrumented version
        self.orch.execute_batches = self._execute_batches_with_progress  # type: ignore[assignment]

    async def run(self) -> None:
        config = self.orch.config
        await self.bus.publish(ProgressEvent(
            type=EventType.PHASE_START,
            data={
                "phase_id": config.phase_id,
                "phase_name": config.name,
                "max_budget_usd": config.max_budget_usd,
            },
        ))

        try:
            await self.orch.run()

            cost_stats = None
            if self.orch.cost_tracker:
                cost_stats = self.orch.cost_tracker.get_stats()

            await self.bus.publish(ProgressEvent(
                type=EventType.PHASE_COMPLETE,
                data={
                    "phase_id": config.phase_id,
                    "total_results": len(self.orch.results),
                    "failed_batches": len(self.orch.failed_batches),
                    "estimated_token_cost": cost_stats,
                    "cost": cost_stats,
                },
            ))
        except PhaseAbortError as e:
            await self.bus.publish(ProgressEvent(
                type=EventType.PHASE_ERROR,
                data={"phase_id": config.phase_id, "error": str(e)},
            ))
            raise
        except Exception as e:
            await self.bus.publish(ProgressEvent(
                type=EventType.PHASE_ERROR,
                data={"phase_id": config.phase_id, "error": str(e)},
            ))
            raise
        finally:
            runner_close = getattr(getattr(self.orch, "runner", None), "close", None)
            if runner_close is not None:
                await runner_close()
            await self.bus.close()

    async def _execute_batches_with_progress(
        self, batches: list[list[dict[str, Any]]]
    ) -> None:
        """Replacement for execute_batches that emits SSE events instead of tqdm."""
        orch = self.orch
        total_items = sum(len(b) for b in batches)
        completed_items = 0

        await self.bus.publish(ProgressEvent(
            type=EventType.ITEMS_LOADED,
            data={"total_items": total_items, "total_batches": len(batches)},
        ))

        async def _run_with_meta(
            batch: list[dict[str, Any]],
            worker_id: int,
            batch_index: int,
        ) -> tuple[list[dict[str, Any]] | None, int, int, int]:
            try:
                result = await orch.runner.run_batch(batch, worker_id, batch_index)
            except (CircuitBreakerTripped, BudgetExceeded):
                raise
            except Exception as e:
                raise RuntimeError(f"W{worker_id}B{batch_index}: {e}") from e
            return result, worker_id, batch_index, len(batch)

        tasks: list[asyncio.Task[Any]] = []
        for batch in batches:
            worker_id = orch._batch_counter % orch.num_workers
            batch_index = orch._batch_counter
            orch._batch_counter += 1
            tasks.append(asyncio.create_task(
                _run_with_meta(batch, worker_id, batch_index)
            ))

        for coro in asyncio.as_completed(tasks):
            batch_size = 0
            try:
                result, worker_id, batch_index, batch_size = await coro
                completed_items += batch_size

                if result is None:
                    orch.failed_batches.append((worker_id, batch_index))
                    await self.bus.publish(ProgressEvent(
                        type=EventType.BATCH_FAILED,
                        data={
                            "worker_id": worker_id,
                            "batch_index": batch_index,
                            "completed": completed_items,
                            "total": total_items,
                        },
                    ))
                else:
                    orch.results.extend(result)
                    if result:
                        orch.collector.save_partial(result, worker_id, batch_index)
                    await self.bus.publish(ProgressEvent(
                        type=EventType.BATCH_COMPLETE,
                        data={
                            "worker_id": worker_id,
                            "batch_index": batch_index,
                            "results_count": len(result) if result else 0,
                            "completed": completed_items,
                            "total": total_items,
                        },
                    ))

                # Emit cost update after each batch
                if orch.cost_tracker:
                    await self.bus.publish(ProgressEvent(
                        type=EventType.COST_UPDATE,
                        data=orch.cost_tracker.get_stats(),
                    ))

            except CircuitBreakerTripped as cb:
                orch._circuit_breaker_tripped = True
                await self.bus.publish(ProgressEvent(
                    type=EventType.CIRCUIT_BREAKER,
                    data={"reason": cb.reason, "stats": cb.stats},
                ))
                for task in tasks:
                    if not task.done():
                        task.cancel()
                break
            except BudgetExceeded as be:
                orch._budget_exceeded = True
                await self.bus.publish(ProgressEvent(
                    type=EventType.CIRCUIT_BREAKER,
                    data={"reason": str(be), "stats": be.stats},
                ))
                for task in tasks:
                    if not task.done():
                        task.cancel()
                break
            except Exception as e:
                completed_items += batch_size
                _m = re.match(r"W(\d+)B(\d+):", str(e))
                if _m:
                    orch.failed_batches.append((int(_m.group(1)), int(_m.group(2))))
                else:
                    orch.failed_batches.append((0, 0))

        # Wait for cancelled tasks to finish cleanup
        pending = [t for t in tasks if not t.done()]
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)


async def _run_phase(run: RunInfo, manager: RunManager) -> None:
    """Background task that runs the orchestrator with progress instrumentation."""
    inputs = run.inputs
    phase_id = inputs["phase_id"]

    try:
        manager.mark_running(run.run_id)

        with output_root_context(run.output_dir):
            validate_target_checkout_for_phase(phase_id)

            if phase_id == "05":
                from orchestrator.phase05_candidates import write_poc_candidate_index

                output_root = get_output_root()
                candidate_path = output_root / "05_POC_CANDIDATES.json"
                if inputs.get("force") and candidate_path.exists():
                    candidate_path.unlink()

                await run.bus.publish(ProgressEvent(
                    type=EventType.PHASE_START,
                    data={
                        "phase_id": phase_id,
                        "phase_name": "PoC Candidate Selection",
                        "max_budget_usd": 0,
                    },
                ))
                index = write_poc_candidate_index(output_root, candidate_path)
                metadata = index.get("metadata", {})
                result = {
                    "total_results": metadata.get("candidate_count", 0),
                    "reviewed_candidate_items": metadata.get(
                        "reviewed_candidate_items",
                        0,
                    ),
                    "output_dir": str(get_output_root()),
                    "candidate_file": str(candidate_path),
                }
                await run.bus.publish(ProgressEvent(
                    type=EventType.PHASE_COMPLETE,
                    data={
                        "phase_id": phase_id,
                        "total_results": result["total_results"],
                        "failed_batches": 0,
                        "estimated_token_cost": None,
                        "cost": None,
                    },
                ))
                manager.mark_complete(run.run_id, result=result)
                await run.bus.close()
                await send_phase_result(run)
                return

            orch = create_orchestrator(
                phase_id,
                num_workers=inputs.get("workers", 4),
                max_concurrent=inputs.get("max_concurrent", 8),
            )
            orch.force_execute = bool(inputs.get("force"))

            runtime_env: dict[str, str] = {
                "SPECA_OUTPUT_DIR": str(get_output_root()),
                "SPECA_RUN_ID": run.run_id,
                "SPECA_PHASE_ID": phase_id,
            }
            if inputs.get("keywords"):
                runtime_env["KEYWORDS"] = str(inputs["keywords"])
            if inputs.get("spec_urls"):
                runtime_env["SPEC_URLS"] = str(inputs["spec_urls"])
            if inputs.get("api_base_url"):
                runtime_env["API_RUNNER_BASE_URL"] = str(inputs["api_base_url"])
            if inputs.get("codex_thread_id"):
                runtime_env["SPECA_CODEX_THREAD_ID"] = str(inputs["codex_thread_id"])
            api_key_env = inputs.get("api_key_env")
            if api_key_env and os.environ.get(str(api_key_env)):
                runtime_env["API_RUNNER_API_KEY"] = os.environ[str(api_key_env)]

            orch.config.runtime_env.update(runtime_env)

            # Codex App work uses the app-server protocol by default. Claude
            # and codex-exec remain available when explicitly requested for
            # backwards compatibility and debugging.
            orch.config.runner_type = inputs.get("runner") or "codex-app"
            if inputs.get("app_server_url"):
                orch.config.codex_app_server_url = str(inputs["app_server_url"])
            if inputs.get("isolated_worktrees"):
                orch.config.isolated_worktrees = True
            if inputs.get("worktree_root"):
                orch.config.worktree_root = str(inputs["worktree_root"])
            if inputs.get("worktree_base_ref"):
                orch.config.worktree_base_ref = str(inputs["worktree_base_ref"])

            effective_runner = (
                orch.config.runner_type
                or os.environ.get("ORCHESTRATOR_RUNNER", "claude")
            ).lower()
            codex_runner = effective_runner in {
                "codex",
                "codex-app",
                "codex_app",
                "app-server",
                "app_server",
            }
            use_gui_settings = codex_runner and (
                inputs.get("use_codex_gui_model", True)
                or inputs.get("use_codex_gui_reasoning_effort", True)
                or inputs.get("use_codex_gui_service_tier", True)
            )
            gui_settings = (
                resolve_codex_gui_settings({**os.environ, **runtime_env})
                if use_gui_settings
                else None
            )
            if inputs.get("model"):
                if effective_runner == "api":
                    orch.config.runtime_env["API_RUNNER_MODEL"] = str(inputs["model"])
                elif codex_runner:
                    orch.config.model = str(inputs["model"])
                    orch.config.runtime_env["SPECA_CODEX_MODEL"] = str(inputs["model"])
                    orch.config.runtime_env["SPECA_CODEX_MODEL_SOURCE"] = "explicit"
                else:
                    orch.config.model = str(inputs["model"])
            elif inputs.get("use_codex_gui_model", True) and gui_settings:
                if gui_settings.model:
                    orch.config.runtime_env["SPECA_CODEX_MODEL"] = gui_settings.model
                    orch.config.runtime_env["SPECA_CODEX_MODEL_SOURCE"] = "codex-gui"

            if inputs.get("reasoning_effort"):
                orch.config.runtime_env["SPECA_CODEX_REASONING_EFFORT"] = str(
                    inputs["reasoning_effort"]
                )
                orch.config.runtime_env[
                    "SPECA_CODEX_REASONING_EFFORT_SOURCE"
                ] = "explicit"
            elif inputs.get("use_codex_gui_reasoning_effort", True) and gui_settings:
                if gui_settings.reasoning_effort:
                    orch.config.runtime_env["SPECA_CODEX_REASONING_EFFORT"] = (
                        gui_settings.reasoning_effort
                    )
                    orch.config.runtime_env[
                        "SPECA_CODEX_REASONING_EFFORT_SOURCE"
                    ] = "codex-gui"

            if inputs.get("service_tier"):
                orch.config.runtime_env["SPECA_CODEX_SERVICE_TIER"] = str(
                    inputs["service_tier"]
                )
                orch.config.runtime_env["SPECA_CODEX_SERVICE_TIER_SOURCE"] = "explicit"
            elif inputs.get("use_codex_gui_service_tier", True) and gui_settings:
                if gui_settings.service_tier:
                    orch.config.runtime_env["SPECA_CODEX_SERVICE_TIER"] = (
                        gui_settings.service_tier
                    )
                    orch.config.runtime_env[
                        "SPECA_CODEX_SERVICE_TIER_SOURCE"
                    ] = "codex-gui"

            if inputs.get("min_severity") and orch.config.min_severity is not None:
                orch.config.min_severity = inputs["min_severity"]

            instrumented = InstrumentedOrchestrator(orch, run.bus)
            await instrumented.run()

            cost_stats = orch.cost_tracker.get_stats() if orch.cost_tracker else None
            manager.mark_complete(run.run_id, result={
                "total_results": len(orch.results),
                "estimated_token_cost": cost_stats,
                "cost_kind": "estimated_token_usage",
                "cost": cost_stats,
                "output_dir": str(get_output_root()),
            })
        await send_phase_result(run)
    except PhaseAbortError as e:
        manager.mark_complete(run.run_id, error=str(e))
        await send_phase_result(run)
    except asyncio.CancelledError:
        manager.mark_cancelled(run.run_id)
        await run.bus.close()
        await send_phase_result(run)
    except Exception as e:
        manager.mark_complete(run.run_id, error=str(e))
        await send_phase_result(run)
        await run.bus.close()


async def launch_phase(run: RunInfo, manager: RunManager) -> None:
    """Create a background task for the phase run."""
    run.task = asyncio.create_task(_run_phase(run, manager))
