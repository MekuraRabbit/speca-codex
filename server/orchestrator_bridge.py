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
from orchestrator.runner import CircuitBreakerTripped, BudgetExceeded

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

    # Set environment variables (mirrors run_phase.py logic)
    if inputs.get("force"):
        os.environ["FORCE_EXECUTE"] = "1"
    elif "FORCE_EXECUTE" in os.environ:
        del os.environ["FORCE_EXECUTE"]

    if phase_id == "01a":
        if inputs.get("keywords"):
            os.environ["KEYWORDS"] = inputs["keywords"]
        if inputs.get("spec_urls"):
            os.environ["SPEC_URLS"] = inputs["spec_urls"]

    try:
        run.status = RunStatus.RUNNING

        orch = create_orchestrator(
            phase_id,
            num_workers=inputs.get("workers", 4),
            max_concurrent=inputs.get("max_concurrent", 8),
        )

        if inputs.get("min_severity") and orch.config.min_severity is not None:
            orch.config.min_severity = inputs["min_severity"]

        instrumented = InstrumentedOrchestrator(orch, run.bus)
        await instrumented.run()

        cost_stats = orch.cost_tracker.get_stats() if orch.cost_tracker else None
        manager.mark_complete(run.run_id, result={
            "total_results": len(orch.results),
            "cost": cost_stats,
        })
        await send_phase_result(run)
    except PhaseAbortError as e:
        manager.mark_complete(run.run_id, error=str(e))
        await send_phase_result(run)
    except asyncio.CancelledError:
        run.status = RunStatus.CANCELLED
        run.completed_at = __import__("time").time()
        await run.bus.close()
        await send_phase_result(run)
    except Exception as e:
        manager.mark_complete(run.run_id, error=str(e))
        await send_phase_result(run)
        await run.bus.close()


async def launch_phase(run: RunInfo, manager: RunManager) -> None:
    """Create a background task for the phase run."""
    run.task = asyncio.create_task(_run_phase(run, manager))
