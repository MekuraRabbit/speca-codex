"""
Base Orchestrator Module

Provides the abstract base class for all phase orchestrators.
"""

import asyncio
import hashlib
import json
import os
import re
import sys
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from pydantic import ValidationError
from tqdm import tqdm

from .config import PhaseConfig, get_phase_config
from .paths import get_output_root
from .queue import QueueManager
from .batch import BatchStrategy, TokenBasedBatch, CountBasedBatch
from .runner import ClaudeRunner, CircuitBreaker, CircuitBreakerTripped, BudgetExceeded
from .codex_runner import CodexRunner
from .codex_app_runner import CodexAppRunner
from .codex_adapter import codex_model_from_config
from .api_runner import APIRunner
from .watchdog import CostTracker


class PhaseAbortError(Exception):
    """Raised when a phase must abort (replaces sys.exit calls)."""
    pass
from .collector import ResultCollector
from .resume import ResumeManager
from .schemas import (
    Phase01aState,
    Phase01bPartial,
    Phase01ePartial,
    Phase02cPartial,
    Phase03Partial,
    AuditMapItem,
    Severity,
    validate_audit_map_item,
    validate_subgraph,
    validate_property,
    validate_reviewed_item,
)


# ---------------------------------------------------------------------------
# Helper: log Pydantic validation warnings
# ---------------------------------------------------------------------------

def _log_validation_warning(
    filepath: str,
    ve: ValidationError,
    *,
    prefix: str = "",
) -> None:
    """Print structured Pydantic validation warnings to stderr."""
    label = f"{prefix} " if prefix else ""
    print(
        f"Warning: {label}Schema validation warning for {filepath}: "
        f"{ve.error_count()} error(s)",
        file=sys.stderr,
    )
    for err in ve.errors():
        print(f"    {err['loc']}: {err['msg']}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Helper: generate slug from text for meaningful IDs
# ---------------------------------------------------------------------------

_SLUG_ABBREVS = {
    "transaction": "txn", "p2p": "p2p", "engine api": "engapi",
    "consensus": "cons", "validator": "val", "attestation": "attest",
    "beacon": "beacon", "execution": "exec", "block": "blk",
    "state": "state", "sync": "sync", "gossip": "gossip",
    "networking": "net", "devp2p": "devp2p", "libp2p": "libp2p",
}


def generate_slug(text: str, max_len: int = 12) -> str:
    """Generate a short slug from descriptive text for use in IDs.

    Uses a known abbreviation map first, then falls back to
    alphanumeric slugification, and finally a hash if nothing remains.
    """
    lower = text.lower().strip()
    for phrase, abbrev in _SLUG_ABBREVS.items():
        if phrase in lower:
            return abbrev[:max_len]
    slug = re.sub(r'[^a-z0-9]+', '-', lower).strip('-')
    if len(slug) > max_len:
        slug = slug[:max_len].rstrip('-')
    return slug or hashlib.sha256(text.encode()).hexdigest()[:8]


# ---------------------------------------------------------------------------
# Helper: path traversal guard for LLM-supplied file paths
# ---------------------------------------------------------------------------

def _is_safe_output_path(file_path: str) -> bool:
    """Check that *file_path* resolves to within the ``outputs/`` directory.

    LLM output JSON may contain ``file_path`` or ``subgraph_file`` fields
    that are subsequently opened.  This guard prevents path-traversal attacks
    (e.g. ``../../../../etc/passwd``) by ensuring the resolved path stays
    inside the ``outputs/`` directory relative to the current working
    directory.

    Returns ``True`` when the path is safe, ``False`` otherwise.
    """
    try:
        outputs_dir = get_output_root().resolve()
        resolved = Path(file_path).resolve()
        return resolved.is_relative_to(outputs_dir)
    except (ValueError, OSError):
        return False


class BaseOrchestrator(ABC):
    """
    Abstract base class for phase orchestrators.
    
    Provides common functionality for:
    - Queue management
    - Batch creation
    - Parallel worker execution
    - Result collection
    - **Circuit breaker** for anomaly detection and cost control
    - **Cost tracking** with automatic budget enforcement
    
    Subclasses can override specific methods for phase-specific behavior.
    """
    
    def __init__(
        self,
        phase_id: str,
        num_workers: int = 4,
        max_concurrent: int = 8,
    ):
        self.config = get_phase_config(phase_id)
        self.num_workers = max(1, num_workers)
        self.max_concurrent = max(1, max_concurrent)
        self.semaphore: asyncio.Semaphore | None = None
        self.force_execute: bool | None = None
        
        # Shared circuit breaker for all workers in this phase
        self.circuit_breaker = CircuitBreaker(self.config)

        # Cost tracker — shared across all workers
        self.cost_tracker: CostTracker | None = None
        if self.config.max_budget_usd > 0:
            self.cost_tracker = CostTracker(
                max_budget_usd=self.config.max_budget_usd,
            )

        # Components (runner is created lazily in run() after event loop starts)
        self.queue_manager = QueueManager(self.config)
        self.batch_strategy = self._create_batch_strategy()
        self.runner: ClaudeRunner | CodexRunner | CodexAppRunner | APIRunner | None = None
        self.collector = ResultCollector(self.config)
        self.resume_manager = ResumeManager(self.config)
        
        # State
        self.results: list[dict[str, Any]] = []
        self.failed_batches: list[tuple[int, int]] = []
        self._batch_counter = 0
        self._circuit_breaker_tripped = False
        self._budget_exceeded = False
    
    def _create_batch_strategy(self) -> BatchStrategy:
        """Create the appropriate batch strategy based on config."""
        if self.config.batch_strategy == "token":
            return TokenBasedBatch(
                max_tokens=self.config.max_context_tokens,
                base_tokens=self.config.base_prompt_tokens,
            )
        else:
            return CountBasedBatch(
                max_size=self.config.max_batch_size,
            )
    
    async def run(self) -> None:
        """
        Main execution method.
        
        1. Load items from queue
        2. Apply early exit logic
        3. Create batches
        4. Execute batches in parallel
        5. Collect and save results
        6. Report circuit breaker / validation statistics
        """
        # Lazily create asyncio primitives now that the event loop is running
        self.semaphore = asyncio.Semaphore(self.max_concurrent)

        # Select runner. CLI/CI keep the historical Claude default unless
        # explicitly overridden; the SPECA app server sets runner_type=codex-app.
        # App-server runs set this on their copied PhaseConfig to avoid
        # process-wide env races while multiple runs are active.
        runner_type = (self.config.runner_type or os.environ.get("ORCHESTRATOR_RUNNER", "claude")).lower()
        if runner_type in {"codex-app", "codex_app", "app-server", "app_server"}:
            self.runner = CodexAppRunner(
                self.config,
                self.semaphore,
                circuit_breaker=self.circuit_breaker,
                cost_tracker=self.cost_tracker,
            )
            model_label = codex_model_from_config(self.config) or "default Codex model"
            print(f"  Runner: CodexAppRunner ({model_label})")
        elif runner_type == "codex":
            self.runner = CodexRunner(
                self.config,
                self.semaphore,
                circuit_breaker=self.circuit_breaker,
                cost_tracker=self.cost_tracker,
            )
            model_label = codex_model_from_config(self.config) or "default Codex model"
            print(f"  Runner: CodexRunner ({model_label})")
        elif runner_type == "api":
            self.runner = APIRunner(
                self.config,
                self.semaphore,
                circuit_breaker=self.circuit_breaker,
                cost_tracker=self.cost_tracker,
            )
            print(f"  Runner: APIRunner ({self.runner.model})")
        else:
            self.runner = ClaudeRunner(
                self.config,
                self.semaphore,
                circuit_breaker=self.circuit_breaker,
                cost_tracker=self.cost_tracker,
            )

        print(f"\n{'='*60}")
        print(f"Phase {self.config.phase_id}: {self.config.name}")
        print(f"{'='*60}")

        start_time = time.time()
        
        # Step 1: Load items
        all_items = self.load_items()
        print(f"Loaded {len(all_items)} items")

        if not all_items:
            print("No items to process. Exiting.")
            return

        # Step 1.5: Resume — skip already-processed items
        force_execute = (
            self.force_execute
            if self.force_execute is not None
            else os.environ.get("FORCE_EXECUTE", "") == "1"
        )
        if force_execute:
            print("FORCE_EXECUTE=1: skipping resume filter")
        else:
            all_items, skipped = self.resume_manager.filter_remaining(all_items)
            if skipped:
                print(f"Resume: skipped {skipped} already-processed items, {len(all_items)} remaining")
            if not all_items:
                print("All items already processed. Nothing to do.")
                return

        # Step 2: Apply early exit logic
        early_exit_results, items_to_process = self.apply_early_exit(all_items)
        print(f"Early exit: {len(early_exit_results)} items")
        print(f"To process: {len(items_to_process)} items")

        # Persist early-exit results so resume sees them
        if early_exit_results:
            self.collector.save_partial(early_exit_results, 0, -1)

        # Step 3: Enrich items (phase-specific)
        enriched_items = self.enrich_items(items_to_process)
        
        # Step 4: Create batches
        batches = self.batch_strategy.create_batches(enriched_items)
        print(f"Created {len(batches)} batches")
        
        # Step 5: Execute batches in parallel
        if batches:
            await self.execute_batches(batches)
        
        duration = time.time() - start_time
        total_results = len(early_exit_results) + len(self.results)

        # Step 6: Print statistics
        await self._print_run_statistics(duration, total_results)
        
        # Step 7: Report failures
        if self._budget_exceeded:
            print(
                f"\nPhase {self.config.phase_id} ABORTED - budget exceeded "
                f"after {duration:.1f}s",
                file=sys.stderr,
            )
            print(f"   Saved results so far: {total_results}")
            raise PhaseAbortError(
                f"Phase {self.config.phase_id} ABORTED - budget exceeded after {duration:.1f}s"
            )

        if self._circuit_breaker_tripped:
            print(
                f"\nPhase {self.config.phase_id} ABORTED by circuit breaker "
                f"after {duration:.1f}s",
                file=sys.stderr,
            )
            print(f"   Saved results so far: {total_results}")
            raise PhaseAbortError(
                f"Phase {self.config.phase_id} ABORTED by circuit breaker after {duration:.1f}s"
            )

        if self.failed_batches:
            print(f"\nWarning: {len(self.failed_batches)} batch(es) failed (successful results saved as partials)", file=sys.stderr)
            for worker_id, batch_index in self.failed_batches:
                print(f"  - Worker {worker_id}, Batch {batch_index}", file=sys.stderr)
            print(f"   Saved results: {total_results}")
            raise PhaseAbortError(
                f"Phase {self.config.phase_id}: {len(self.failed_batches)} batch(es) failed"
            )

        self._after_batches_completed()

        print(f"\nPhase {self.config.phase_id} completed in {duration:.1f}s")
        print(f"   Total results: {total_results}")

    def _after_batches_completed(self) -> None:
        """Run phase-specific finalization after worker batches finish."""
        return None

    async def _print_run_statistics(self, duration: float, total_results: int) -> None:
        """Print circuit breaker and validation statistics."""
        cb_stats = await self.circuit_breaker.get_stats()
        val_stats = self.collector.get_validation_summary()

        print(f"\n{'-'*40}")
        print(f"Run Statistics (Phase {self.config.phase_id})")
        print(f"{'-'*40}")
        print(f"  Duration:              {duration:.1f}s")
        print(f"  Total results:         {total_results}")
        print(f"  Batch successes:       {cb_stats['total_successes']}")
        print(f"  Batch failures:        {cb_stats['total_failures']}")
        print(f"  Total retries:         {cb_stats['total_retries']}")
        print(f"  Empty results:         {cb_stats['empty_results']}")
        print(f"  Validation warnings:   {val_stats['validation_warnings']}")
        print(f"  Validation errors:     {val_stats['validation_errors']}")

        # Token usage statistics. CostTracker still handles budget enforcement,
        # but the normal run summary avoids dollar estimates that look like
        # actual billing for non-API runners such as Codex app-server.
        cost_stats = None
        if self.cost_tracker:
            cost_stats = self.cost_tracker.get_stats()
            print(f"  ---- Token Usage ----")
            print(f"  Input tokens:          {cost_stats['total_input_tokens']:,}")
            print(f"  Cache read tokens:     {cost_stats['total_cache_read_tokens']:,}")
            print(f"  Cache create tokens:   {cost_stats['total_cache_creation_tokens']:,}")
            print(f"  Output tokens:         {cost_stats['total_output_tokens']:,}")
            print(f"  Total tokens:          {cost_stats['total_tokens']:,}")
            print(f"  Total turns:           {cost_stats['total_turns']:,}")
        _sep = "-" * 40
        print(_sep)

        # Write to GitHub Step Summary if running in GitHub Actions
        self._write_github_step_summary(
            duration, total_results, cb_stats, val_stats, cost_stats,
        )

    def _write_github_step_summary(
        self,
        duration: float,
        total_results: int,
        cb_stats: dict[str, Any],
        val_stats: dict[str, Any],
        cost_stats: dict[str, Any] | None,
    ) -> None:
        """
        Write a Markdown summary to ``$GITHUB_STEP_SUMMARY``.

        This renders a rich table in the GitHub Actions "Summary" tab for
        each workflow run, making it easy to spot anomalies at a glance.
        If the environment variable is not set (i.e. running locally),
        this method is a no-op.
        """
        summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
        if not summary_path:
            return

        # Determine status emoji
        if self._budget_exceeded:
            status = "Budget Exceeded"
        elif self._circuit_breaker_tripped:
            status = "Circuit Breaker Tripped"
        elif self.failed_batches:
            status = "Partial Failure"
        else:
            status = "Success"

        lines: list[str] = []
        lines.append(f"## Phase {self.config.phase_id}: {self.config.name}")
        lines.append("")
        lines.append(f"**Status:** {status}")
        lines.append("")

        # --- Execution summary table ---
        lines.append("### Execution Summary")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("| :--- | ---: |")
        lines.append(f"| Duration | {duration:.1f}s |")
        lines.append(f"| Total results | {total_results} |")
        lines.append(f"| Batch successes | {cb_stats['total_successes']} |")
        lines.append(f"| Batch failures | {cb_stats['total_failures']} |")
        lines.append(f"| Total retries | {cb_stats['total_retries']} |")
        lines.append(f"| Empty results | {cb_stats['empty_results']} |")
        lines.append(f"| Validation warnings | {val_stats['validation_warnings']} |")
        lines.append(f"| Validation errors | {val_stats['validation_errors']} |")
        lines.append("")

        # --- Token usage table (if available) ---
        if cost_stats:
            total_tokens = cost_stats.get("total_tokens")
            if total_tokens is None:
                total_tokens = (
                    cost_stats.get("total_input_tokens", 0)
                    + cost_stats.get("total_cache_read_tokens", 0)
                    + cost_stats.get("total_cache_creation_tokens", 0)
                    + cost_stats.get("total_output_tokens", 0)
                )

            lines.append("### Token Usage")
            lines.append("")
            lines.append("| Metric | Value |")
            lines.append("| :--- | ---: |")
            lines.append(f"| Input tokens | {cost_stats.get('total_input_tokens', 0):,} |")
            lines.append(f"| Cache read tokens | {cost_stats.get('total_cache_read_tokens', 0):,} |")
            lines.append(f"| Cache creation tokens | {cost_stats.get('total_cache_creation_tokens', 0):,} |")
            lines.append(f"| Output tokens | {cost_stats.get('total_output_tokens', 0):,} |")
            lines.append(f"| Total tokens | {total_tokens:,} |")
            lines.append(f"| Total turns | {cost_stats.get('total_turns', 0):,} |")
            lines.append("")

        # --- Failed batches detail ---
        if self.failed_batches:
            lines.append("### Failed Batches")
            lines.append("")
            lines.append("| Worker | Batch |")
            lines.append("| :---: | :---: |")
            for worker_id, batch_index in self.failed_batches:
                lines.append(f"| {worker_id} | {batch_index} |")
            lines.append("")

        md = "\n".join(lines)

        try:
            with open(summary_path, "a", encoding="utf-8") as f:
                f.write(md)
                f.write("\n")
        except OSError as e:
            print(f"Warning: could not write to GITHUB_STEP_SUMMARY: {e}", file=sys.stderr)

    def load_items(self) -> list[dict[str, Any]]:
        """Load items from input sources. Override for custom loading logic."""
        return self.queue_manager.load_all_items()
    
    def apply_early_exit(
        self,
        items: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Apply early exit logic to items.
        
        Returns:
            Tuple of (early_exit_results, items_to_process)
        """
        if not self.config.early_exit_check:
            return [], items
        
        early_exit_results = []
        items_to_process = []
        
        for item in items:
            if self.config.early_exit_check(item):
                if self.config.early_exit_builder:
                    early_exit_results.append(self.config.early_exit_builder(item))
            else:
                items_to_process.append(item)
        
        return early_exit_results, items_to_process
    
    def enrich_items(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Enrich items with additional context.
        Override in subclasses for phase-specific enrichment.
        """
        return items
    
    async def execute_batches(self, batches: list[list[dict[str, Any]]]) -> None:
        """
        Execute all batches in parallel with progress tracking.

        Integrates circuit breaker: if ``CircuitBreakerTripped`` is raised by
        any worker, all remaining tasks are cancelled and partial results are
        preserved.
        """

        async def _run_with_meta(
            batch: list[dict[str, Any]],
            worker_id: int,
            batch_index: int,
        ) -> tuple[list[dict[str, Any]] | None, int, int, int]:
            """Wrap runner call to carry metadata through asyncio.as_completed."""
            try:
                result = await self.runner.run_batch(batch, worker_id, batch_index)
            except (CircuitBreakerTripped, BudgetExceeded):
                raise  # Propagate immediately with original traceback
            except Exception as e:
                raise RuntimeError(
                    f"W{worker_id}B{batch_index}: {e}"
                ) from e
            return result, worker_id, batch_index, len(batch)

        tasks: list[asyncio.Task] = []
        for batch in batches:
            worker_id = self._batch_counter % self.num_workers
            batch_index = self._batch_counter
            self._batch_counter += 1

            tasks.append(asyncio.create_task(
                _run_with_meta(batch, worker_id, batch_index)
            ))

        total_items = sum(len(b) for b in batches)

        with tqdm(total=total_items, desc=f"Processing {self.config.name}", unit="item") as pbar:
            for coro in asyncio.as_completed(tasks):
                batch_size = 0
                try:
                    result, worker_id, batch_index, batch_size = await coro
                    if result is None:
                        self.failed_batches.append((worker_id, batch_index))
                    else:
                        self.results.extend(result)
                        if result:
                            self.collector.save_partial(result, worker_id, batch_index)
                except CircuitBreakerTripped as cb:
                    self._circuit_breaker_tripped = True
                    print(
                        f"\nCircuit breaker tripped: {cb.reason}",
                        file=sys.stderr,
                    )
                    print(
                        f"   Stats: {cb.stats}",
                        file=sys.stderr,
                    )
                    # Cancel all remaining tasks
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    break
                except BudgetExceeded as be:
                    self._budget_exceeded = True
                    print(
                        f"\nBudget exceeded: {be}",
                        file=sys.stderr,
                    )
                    print(
                        f"   Stats: {be.stats}",
                        file=sys.stderr,
                    )
                    # Cancel all remaining tasks
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    break
                except Exception as e:
                    print(f"Task failed with error: {e}", file=sys.stderr)
                    # Extract worker/batch from RuntimeError message (W{id}B{idx}: ...)
                    _m = re.match(r"W(\d+)B(\d+):", str(e))
                    if _m:
                        self.failed_batches.append((int(_m.group(1)), int(_m.group(2))))
                    else:
                        self.failed_batches.append((0, 0))
                finally:
                    pbar.update(batch_size)

        # Wait for cancelled tasks to finish cleanup (subprocess kill etc.)
        # Without this, orphan Claude CLI processes keep running after exit.
        pending = [t for t in tasks if not t.done()]
        if pending:
            print(
                f"Waiting for {len(pending)} task(s) to shut down...",
                file=sys.stderr,
            )
            await asyncio.gather(*pending, return_exceptions=True)
    


class Phase01Orchestrator(BaseOrchestrator):
    """Orchestrator for Phase 01 (Specification Analysis) sub-phases."""

    def load_items(self) -> list[dict[str, Any]]:
        """
        Load items for Phase 01 with Pydantic validation at phase boundaries.

        - 01a: Returns a single seed item (no input file).
        - 01b: Loads discovered specs from 01a_STATE.json with validation.
        - 01e: Loads trust model outputs with validation.
        - Others: Standard queue loading.
        """
        if self.config.phase_id == "01a":
            return self._load_01a_items()

        if self.config.phase_id == "01b":
            return self._load_01b_items()

        if self.config.phase_id == "01e":
            return self._load_01e_items()

        return super().load_items()

    def _load_01a_items(self) -> list[dict[str, Any]]:
        """Load one Phase 01a discovery item per configured seed URL."""
        spec_urls = self.config.runtime_env.get("SPEC_URLS") or os.environ.get("SPEC_URLS", "")
        urls = [url.strip() for url in re.split(r"[\n,]+", spec_urls) if url.strip()]
        if not urls:
            return [{"id": "seed", "source": "manual"}]
        return [
            {"id": f"seed-{index}", "url": url, "source": "manual"}
            for index, url in enumerate(urls)
        ]

    def _after_batches_completed(self) -> None:
        if self.config.phase_id != "01a" or not self.results:
            return None
        if self.failed_batches or self._budget_exceeded or self._circuit_breaker_tripped:
            return None

        merged_specs: list[dict[str, Any]] = []
        seen_urls: set[str] = set()
        start_urls: list[str] = []
        urls_visited: list[str] = []

        for result in self.results:
            start_url = result.get("start_url")
            if isinstance(start_url, str) and start_url and start_url not in start_urls:
                start_urls.append(start_url)

            metadata = result.get("metadata")
            if isinstance(metadata, dict):
                for visited in metadata.get("urls_visited", []):
                    if isinstance(visited, str) and visited not in urls_visited:
                        urls_visited.append(visited)

            found_specs = result.get("found_specs", [])
            if not isinstance(found_specs, list):
                continue
            for spec in found_specs:
                if not isinstance(spec, dict):
                    continue
                url = spec.get("url")
                if not isinstance(url, str) or not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                merged_specs.append(spec)

        state = {
            "found_specs": merged_specs,
            "metadata": {
                "phase": "01a",
                "seed_urls": start_urls,
                "urls_visited": urls_visited,
                "merged_batches": len(self.results),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
        }
        state_path = get_output_root() / "01a_STATE.json"
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        print(f"  Wrote merged 01a state: {state_path}")

    # -- Phase 01b: load discovered specs from 01a output ----------------

    def _load_01b_items(self) -> list[dict[str, Any]]:
        """Load discovered specs from 01a_STATE.json with Pydantic validation."""
        import glob as glob_mod
        from .config import resolve_pattern

        items: list[dict[str, Any]] = []
        for pattern in self.config.input_patterns:
            for filepath in sorted(glob_mod.glob(resolve_pattern(pattern))):
                try:
                    with open(filepath, encoding="utf-8-sig") as f:
                        data = json.load(f)

                    # Validate 01a output structure
                    try:
                        state = Phase01aState.model_validate(data)
                        print(
                            f"  OK {filepath}: {len(state.found_specs)} specs validated"
                        )
                    except ValidationError as ve:
                        _log_validation_warning(filepath, ve, prefix="01a->01b")
                        # Fall through to raw parsing

                    for spec in data.get("found_specs", []):
                        if isinstance(spec, dict) and spec.get("url"):
                            items.append(spec)
                except Exception as e:
                    print(
                        f"Warning: Failed to load {filepath}: {e}",
                        file=sys.stderr,
                    )
        return items

    # -- Phase 01e: load subgraph files for property generation -----------

    def _load_01e_items(self) -> list[dict[str, Any]]:
        """Load subgraph files for property generation with Pydantic validation."""
        import glob as glob_mod
        from .config import resolve_pattern

        items: list[dict[str, Any]] = []
        validation_warnings = 0

        for pattern in self.config.input_patterns:
            for filepath in sorted(glob_mod.glob(resolve_pattern(pattern))):
                try:
                    with open(filepath, encoding="utf-8-sig") as f:
                        data = json.load(f)

                    # Validate 01b partial structure
                    try:
                        Phase01bPartial.model_validate(data)
                    except ValidationError as ve:
                        _log_validation_warning(filepath, ve, prefix="01b->01e")
                        validation_warnings += 1

                    items.append({"file_path": filepath})
                except Exception as e:
                    print(
                        f"Warning: Failed to load {filepath}: {e}",
                        file=sys.stderr,
                    )

        if validation_warnings:
            print(
                f"Warning: {validation_warnings} file(s) had schema validation warnings (01b->01e)",
                file=sys.stderr,
            )
        return items

    def enrich_items(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Enrich items with necessary context."""
        if self.config.phase_id == "01a":
            # For 01a, we need to ensure KEYWORDS and SPEC_URLS are available
            keywords = self.config.runtime_env.get("KEYWORDS") or os.environ.get("KEYWORDS")
            spec_urls = self.config.runtime_env.get("SPEC_URLS") or os.environ.get("SPEC_URLS")
            if not keywords or not spec_urls:
                missing = [
                    name
                    for name, value in (
                        ("KEYWORDS", keywords),
                        ("SPEC_URLS", spec_urls),
                    )
                    if not value
                ]
                print(f"Warning: {', '.join(missing)} not set")
            return items

        if self.config.phase_id == "01e":
            items = self._assign_property_id_prefixes(items)
            items = self._inject_bug_bounty_scope(items)
            return self._enrich_with_subgraph_context(items)
        return items

    def _assign_property_id_prefixes(
        self,
        items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Assign meaningful _id_prefix to each item for property ID generation.

        Derives a slug from 01b partial data (spec title or source_url),
        ensuring uniqueness via a disambiguation counter.
        """
        slug_counters: dict[str, int] = {}
        for item in items:
            file_path = item.get("file_path", "")
            slug = self._derive_slug_from_partial(file_path)
            count = slug_counters.get(slug, 0)
            slug_counters[slug] = count + 1
            unique_slug = slug if count == 0 else f"{slug}{count}"
            item["_id_prefix"] = f"PROP-{unique_slug}"
        return items

    def _derive_slug_from_partial(self, file_path: str) -> str:
        """Derive a slug from 01b partial data.

        Reads the 01b partial JSON and uses the spec title or source_url
        to generate a meaningful slug (e.g., "EIP-7594" -> "eip-7594").
        Falls back to a hash of the file name on failure.
        """
        if not file_path:
            return hashlib.sha256(b"unknown").hexdigest()[:8]

        # SEC-C02: Guard against path traversal in LLM-supplied file_path
        if not _is_safe_output_path(file_path):
            print(
                f"Warning: path traversal blocked in _derive_slug_from_partial: {file_path!r}",
                file=sys.stderr,
            )
            return hashlib.sha256(file_path.encode()).hexdigest()[:8]

        try:
            with open(file_path, encoding="utf-8-sig") as f:
                data = json.load(f)

            # Try specs[].title or specs[].source_url
            specs = data.get("specs", [])
            if specs and isinstance(specs, list):
                first_spec = specs[0] if isinstance(specs[0], dict) else {}
                title = first_spec.get("title", "")
                if title:
                    return generate_slug(title)
                source_url = first_spec.get("source_url", "")
                if source_url:
                    # Extract meaningful part from URL (e.g. "eip-7594" from path)
                    url_stem = Path(source_url.rstrip("/")).stem
                    return generate_slug(url_stem)

            # Fallback: use the file name stem
            stem = Path(file_path).stem
            return generate_slug(stem)
        except Exception:
            # Hash fallback
            return hashlib.sha256(file_path.encode()).hexdigest()[:8]

    def _inject_bug_bounty_scope(
        self,
        items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Inject bug_bounty_scope from BUG_BOUNTY_SCOPE.json into each item.

        The file is **required** — if missing or unparseable, the orchestrator
        aborts with a non-zero exit code.
        """
        scope_path = get_output_root() / "BUG_BOUNTY_SCOPE.json"
        if not scope_path.exists():
            raise PhaseAbortError(
                f"{scope_path} not found. "
                f"bug_bounty_scope is required for Phase 01e. "
                f"Create the file before running this phase."
            )

        try:
            with open(scope_path, encoding="utf-8-sig") as f:
                scope_data = json.load(f)
            print(f"  Injected bug_bounty_scope from {scope_path}")
        except Exception as e:
            raise PhaseAbortError(
                f"Failed to parse {scope_path}: {e}"
            ) from e

        for item in items:
            item["bug_bounty_scope"] = scope_data
        return items
    
    def _enrich_with_subgraph_context(
        self,
        items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Add subgraph data to items."""
        subgraph_cache: dict[str, dict] = {}

        enriched = []
        for item in items:
            enriched_item = item.copy()

            subgraph_file = item.get("subgraph_file")

            # Fallback for Phase 01e items: use file_path if subgraph_file is absent
            if not subgraph_file and item.get("file_path"):
                subgraph_file = item["file_path"]

            if subgraph_file:
                # SEC-C02: Guard against path traversal in LLM-supplied subgraph_file
                if not _is_safe_output_path(subgraph_file):
                    print(
                        f"Warning: path traversal blocked in _enrich_with_subgraph_context: {subgraph_file!r}",
                        file=sys.stderr,
                    )
                    subgraph_cache[subgraph_file] = {}
                elif subgraph_file not in subgraph_cache:
                    try:
                        with open(subgraph_file, encoding="utf-8-sig") as f:
                            subgraph_cache[subgraph_file] = json.load(f)
                    except Exception:
                        subgraph_cache[subgraph_file] = {}

                subgraph_id = item.get("subgraph_id")
                if subgraph_id:
                    for sg in subgraph_cache[subgraph_file].get("sub_graphs", []):
                        if sg.get("id") == subgraph_id:
                            enriched_item["subgraph"] = sg
                            break
                elif subgraph_file in subgraph_cache:
                    # No subgraph_id — attach all subgraphs from the file as context
                    all_sgs = subgraph_cache[subgraph_file].get("sub_graphs", [])
                    if all_sgs:
                        enriched_item["subgraphs"] = all_sgs

            enriched.append(enriched_item)

        return enriched


class Phase02cOrchestrator(BaseOrchestrator):
    """Orchestrator for Phase 02c (Code Location Pre-resolution).

    Loads properties directly from 01e partials, applies scope/severity
    filtering, and sends them for code location resolution.
    """

    def _build_subgraph_index(self) -> None:
        """Build and save 01b subgraph index for worker context."""
        import glob as glob_mod

        index = []
        for filepath in sorted(glob_mod.glob(str(get_output_root() / "01b_PARTIAL_*.json"))):
            try:
                with open(filepath, encoding="utf-8-sig") as f:
                    data = json.load(f)
                for spec in data.get("specs", []):
                    entry = {
                        "spec_title": spec.get("title", ""),
                        "source_url": spec.get("source_url", ""),
                        "subgraphs": [
                            {
                                "id": sg["id"],
                                "name": sg.get("name", ""),
                                "mermaid_file": sg.get("mermaid_file", ""),
                            }
                            for sg in spec.get("sub_graphs", [])
                            if sg.get("id")
                        ],
                    }
                    if entry["subgraphs"]:
                        index.append(entry)
            except Exception as e:
                print(f"Warning: Failed to read {filepath} for subgraph index: {e}", file=sys.stderr)

        out_path = get_output_root() / "01b_SUBGRAPH_INDEX.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2)

        total_sg = sum(len(e["subgraphs"]) for e in index)
        print(f"  Built subgraph index: {len(index)} specs, {total_sg} subgraphs -> {out_path}")

    def load_items(self) -> list[dict[str, Any]]:
        """Load properties from 01e partials with Pydantic validation and deduplication."""
        import glob

        self._build_subgraph_index()  # Generate index for workers

        items = {}  # Deduplication map
        validation_warnings = 0

        for filepath in sorted(glob.glob(str(get_output_root() / "01e_PARTIAL_*.json"))):
            try:
                with open(filepath, encoding="utf-8-sig") as f:
                    data = json.load(f)

                # Validate 01e partial structure
                try:
                    partial = Phase01ePartial.model_validate(data)
                    print(
                        f"  OK {filepath}: {len(partial.properties)} properties validated"
                    )
                except ValidationError as ve:
                    _log_validation_warning(filepath, ve, prefix="01e->02c")
                    validation_warnings += 1

                # Derive a fallback prefix from the file name for ID generation
                file_stem = Path(filepath).stem  # e.g. "01e_PARTIAL_W0B1_1771748647"
                fallback_hash = hashlib.sha256(file_stem.encode()).hexdigest()[:8]
                auto_id_counter = 0

                for prop in data.get("properties", []):
                    if isinstance(prop, dict):
                        parsed, errs = validate_property(prop)
                        if errs:
                            prop_id_raw = prop.get("property_id", "<unknown>")
                            for err in errs:
                                print(
                                    f"    Warning: {filepath} property {prop_id_raw}: {err}",
                                    file=sys.stderr,
                                )

                        prop_id = prop.get("property_id")
                        if not prop_id:
                            # Auto-generate property_id when worker didn't include one
                            auto_id_counter += 1
                            prop_type = prop.get("type", "unk")
                            type_abbrev = {"invariant": "inv", "precondition": "pre",
                                           "postcondition": "post", "assumption": "asm"}.get(prop_type, "unk")
                            prop_id = f"PROP-{fallback_hash}-{type_abbrev}-{auto_id_counter:03d}"
                            prop["property_id"] = prop_id
                            print(
                                f"    Warning: {filepath}: auto-assigned {prop_id} (worker omitted property_id)",
                                file=sys.stderr,
                            )
                        if prop_id not in items:
                            # Flatten property fields as top-level item fields
                            item = dict(prop)
                            item["source_file"] = filepath
                            items[prop_id] = item
            except Exception as e:
                print(f"Warning: Failed to load {filepath}: {e}", file=sys.stderr)

        if validation_warnings:
            print(
                f"Warning: {validation_warnings} file(s) had schema validation warnings (01e->02c)",
                file=sys.stderr,
            )

        return list(items.values())

    def apply_early_exit(
        self,
        items: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Apply early exit for properties without required fields.

        Filters applied (in order):
        1. Missing property ID -> skip
        2. Bug-bounty out-of-scope -> skip
        3. Severity below ``min_severity`` config threshold -> skip
        """
        early_exit_results = []
        items_to_process = []

        min_sev = Severity.from_str(self.config.min_severity) if self.config.min_severity else None
        if min_sev is not None:
            print(f"  Severity gate: min_severity={min_sev.value} (dropping below)")

        severity_skipped = 0

        for item in items:
            prop_id = item.get("property_id")
            if not prop_id:
                early_exit_results.append(self._build_skip_result(item, "missing property id"))
                continue

            reachability = item.get("reachability", {})
            if isinstance(reachability, dict):
                bug_bounty_scope = reachability.get("bug_bounty_scope", "unknown")
            else:
                bug_bounty_scope = "unknown"

            if bug_bounty_scope == "out-of-scope":
                early_exit_results.append(self._build_skip_result(item, "out-of-scope"))
                continue

            if min_sev is not None:
                prop_severity = Severity.from_str(item.get("severity", ""))
                if prop_severity is None or prop_severity < min_sev:
                    label = item.get("severity", "(empty)")
                    early_exit_results.append(
                        self._build_skip_result(item, f"below min_severity ({label})")
                    )
                    severity_skipped += 1
                    continue

            items_to_process.append(item)

        if severity_skipped and min_sev is not None:
            print(f"  Severity gate: skipped {severity_skipped} properties below {min_sev.value}")

        return early_exit_results, items_to_process

    def _build_skip_result(self, item: dict[str, Any], reason: str) -> dict[str, Any]:
        """Build a skip result for early exit items."""
        prop_id = item.get("property_id", "unknown")
        result = dict(item)
        result.update({
            "property_id": prop_id,
            "skipped": True,
            "skip_reason": reason,
            "code_scope": {
                "locations": [],
                "resolution_status": "out_of_scope",
                "resolution_error": reason,
            },
            "code_excerpt": "",
        })
        return result

    def enrich_items(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Assign _id_prefix from property_id."""
        for item in items:
            prop_id = item.get("property_id", "")
            item["_id_prefix"] = prop_id
        return items


class Phase03Orchestrator(BaseOrchestrator):
    """Orchestrator for Phase 03 (Audit Map Generation)."""

    def __init__(self, num_workers: int = 4, max_concurrent: int = 8):
        super().__init__("03", num_workers, max_concurrent)

    def enrich_items(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Anchor 02c code locations to the pinned local target checkout."""
        local_checkout = self._target_local_checkout()

        for item in items:
            item["target_local_checkout"] = local_checkout
            code_scope = item.get("code_scope", {})
            if not isinstance(code_scope, dict):
                continue

            locations = code_scope.get("locations", [])
            if not isinstance(locations, list):
                continue

            for location in locations:
                if not isinstance(location, dict):
                    continue

                file_path = location.get("file")
                if isinstance(file_path, str):
                    location["file"] = self._anchor_code_path(file_path, local_checkout)

        return items

    def _target_local_checkout(self) -> str:
        """Return the configured local checkout root, falling back to legacy layout."""
        target_info = get_output_root() / "TARGET_INFO.json"
        if target_info.exists():
            try:
                data = json.loads(target_info.read_text(encoding="utf-8-sig"))
                local_checkout = data.get("local_checkout")
                if isinstance(local_checkout, str) and local_checkout.strip():
                    return self._normalize_code_path(local_checkout).rstrip("/")
            except Exception as e:
                print(
                    f"Warning: Failed to read {target_info}: {e}",
                    file=sys.stderr,
                )

        return "target_workspace"

    @classmethod
    def _anchor_code_path(cls, file_path: str, local_checkout: str) -> str:
        """Resolve repo-relative code paths under the pinned checkout root."""
        candidate = cls._normalize_code_path(file_path)
        checkout = cls._normalize_code_path(local_checkout).rstrip("/")
        if not candidate or not checkout:
            return candidate

        if candidate == checkout or candidate.startswith(f"{checkout}/"):
            return candidate

        if candidate.startswith(("http://", "https://")):
            return candidate

        if re.match(r"^[A-Za-z]:/", candidate) or candidate.startswith("/"):
            return candidate

        if candidate.startswith("target_workspace/") and checkout != "target_workspace":
            remainder = candidate[len("target_workspace/"):]
            return f"{checkout}/{remainder}"

        return f"{checkout}/{candidate}"

    @staticmethod
    def _normalize_code_path(path: str) -> str:
        """Normalize path separators for worker prompts and JSON context."""
        normalized = path.replace("\\", "/").strip()
        while normalized.startswith("./"):
            normalized = normalized[2:]
        return normalized

    def load_items(self) -> list[dict[str, Any]]:
        """Load properties with code from 02c partials with Pydantic validation."""
        import glob

        items = {}
        validation_warnings = 0

        for filepath in sorted(glob.glob(str(get_output_root() / "02c_PARTIAL_*.json"))):
            try:
                with open(filepath, encoding="utf-8-sig") as f:
                    data = json.load(f)

                try:
                    partial = Phase02cPartial.model_validate(data)
                    print(
                        f"  OK {filepath}: {len(partial.properties_with_code)} properties validated"
                    )
                    entries_raw = partial.model_dump().get("properties_with_code", [])
                except ValidationError as ve:
                    _log_validation_warning(filepath, ve, prefix="02c->03")
                    validation_warnings += 1
                    entries_raw = data.get("properties_with_code", [])

                for entry in entries_raw:
                    if not isinstance(entry, dict):
                        continue

                    parsed, errs = validate_property(entry)
                    if errs:
                        prop_id_raw = entry.get("property_id", "<unknown>")
                        for err in errs:
                            print(
                                f"    Warning: {filepath} property {prop_id_raw}: {err}",
                                file=sys.stderr,
                            )

                    prop_id = entry.get("property_id")
                    if not prop_id:
                        continue

                    if prop_id in items:
                        continue

                    item = dict(entry)
                    item["property_id"] = prop_id
                    item["source_file"] = filepath
                    items[prop_id] = item

            except Exception as e:
                print(f"Warning: Failed to load {filepath}: {e}", file=sys.stderr)

        if validation_warnings:
            print(
                f"Warning: {validation_warnings} file(s) had schema validation warnings (02c->03)",
                file=sys.stderr,
            )

        return list(items.values())

    def apply_early_exit(
        self,
        items: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Apply early exit for out-of-scope and skipped items."""
        early_exit_results = []
        items_to_process = []

        for item in items:
            code_scope = item.get("code_scope", {})

            if isinstance(code_scope, dict) and code_scope.get("resolution_status") == "out_of_scope":
                early_exit_results.append(self._build_early_exit_result(item, "out-of-scope"))
                continue

            if isinstance(code_scope, dict) and code_scope.get("resolution_status") == "skipped":
                early_exit_results.append(self._build_early_exit_result(item, "skipped"))
                continue

            items_to_process.append(item)

        return early_exit_results, items_to_process

    def _build_early_exit_result(self, item: dict[str, Any], reason: str) -> dict[str, Any]:
        """Build early exit result for out-of-scope or skipped items."""
        prop_id = item.get("property_id", "")
        code_scope = item.get("code_scope", {})

        return {
            "property_id": prop_id,
            "check_id": prop_id,  # Downstream compat
            "code_scope": code_scope,
            "classification": reason,
            "bug_bounty_eligible": False,
            "summary": f"Early exit: {reason}.",
            "audit_trail": {
                "phase1_abstract_interpretation": {
                    "summary": f"Early exit: {reason}.",
                    "state_anomalies_found": [],
                },
                "phase2_symbolic_execution": {
                    "summary": "Not performed due to early exit.",
                    "counterexample_found": False,
                    "counterexample": None,
                },
                "phase2_5_reachability_analysis": {
                    "summary": "Not performed due to early exit.",
                    "entry_points": [],
                    "data_flow_path": "",
                    "validation_layers": [],
                    "attacker_controlled": False,
                    "classification": "unreachable",
                    "notes": "",
                },
                "phase3_invariant_proving": {
                    "summary": "Not performed due to early exit.",
                    "proof_successful": False,
                    "guard_identified": None,
                },
                "phase3_5_scope_filtering": {
                    "bug_bounty_eligible": False,
                    "reason": f"Early exit: {reason}.",
                    "recommendation": "",
                    "notes": "",
                },
            },
        }


class Phase04Orchestrator(BaseOrchestrator):
    """Orchestrator for Phase 04 (Audit Review)."""

    @property
    def _required_files(self) -> list[str]:
        root = get_output_root()
        return [
            str(root / "BUG_BOUNTY_SCOPE.json"),
            str(root / "TARGET_INFO.json"),
            str(root / "01b_SUBGRAPH_INDEX.json"),
        ]

    def load_items(self) -> list[dict[str, Any]]:
        """Load audit results from 03 partials with Pydantic validation."""
        import glob

        # Verify required context files exist before processing
        for path in self._required_files:
            if not Path(path).exists():
                raise PhaseAbortError(
                    f"{path} not found. "
                    f"Phase 04 requires this file for severity calibration and spec cross-reference."
                )

        items_dict: dict[str, dict] = {}  # keyed by property_id for dedup
        validation_warnings = 0
        for filepath in sorted(glob.glob(str(get_output_root() / "03_PARTIAL_*.json"))):
            try:
                with open(filepath, encoding="utf-8-sig") as f:
                    data = json.load(f)

                try:
                    Phase03Partial.model_validate(data)
                except ValidationError as ve:
                    _log_validation_warning(filepath, ve, prefix="03->04")
                    validation_warnings += 1

                audit_items = data.get("audit_items", [])
                for item in audit_items:
                    if not isinstance(item, dict):
                        continue
                    prop_id = item.get("property_id") or item.get("check_id")
                    if not prop_id:
                        continue
                    parsed, errs = validate_audit_map_item(item)
                    if errs:
                        for err in errs:
                            print(
                                f"    Warning: {filepath} item {prop_id}: {err}",
                                file=sys.stderr,
                            )
                    items_dict[prop_id] = {
                        "property_id": prop_id,
                        "audit_result": item,
                        "source_file": filepath,
                    }
            except Exception as e:
                print(f"Warning: Failed to load {filepath}: {e}", file=sys.stderr)

        if validation_warnings:
            print(
                f"Warning: {validation_warnings} file(s) had schema validation warnings (03->04)",
                file=sys.stderr,
            )

        items = list(items_dict.values())
        return items

    # Only these classifications need LLM review.
    _NEEDS_REVIEW = {"vulnerability", "potential-vulnerability"}

    def apply_early_exit(
        self,
        items: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Skip non-findings. Only vulnerability/potential-vulnerability go to LLM."""
        early_exit_results = []
        items_to_process = []

        for item in items:
            audit_result = item.get("audit_result", {})
            classification = audit_result.get("classification", "")

            if classification in self._NEEDS_REVIEW:
                items_to_process.append(item)
            else:
                early_exit_results.append({
                    "property_id": item.get("property_id", ""),
                    "review_verdict": "PASS_THROUGH",
                    "original_classification": classification,
                    "adjusted_severity": audit_result.get("severity", "Informational"),
                    "reviewer_notes": f"Auto-passed: Phase 03 classified as {classification}",
                    "spec_reference": "",
                })

        return early_exit_results, items_to_process

    def enrich_items(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Enrich items with original property data from 02c PARTIALs."""
        import glob as glob_mod

        # Build property lookup from 02c PARTIALs
        prop_lookup: dict[str, dict[str, Any]] = {}
        for filepath in sorted(glob_mod.glob(str(get_output_root() / "02c_PARTIAL_*.json"))):
            try:
                with open(filepath, encoding="utf-8-sig") as f:
                    data = json.load(f)
                for prop in data.get("properties_with_code", []):
                    pid = prop.get("property_id", "")
                    if pid:
                        prop_lookup[pid] = prop
            except Exception:
                pass

        # Merge relevant fields into each item
        MERGE_FIELDS = ["text", "assertion", "covers", "severity", "type"]
        for item in items:
            pid = item.get("property_id", "")
            upstream = prop_lookup.get(pid, {})
            for field in MERGE_FIELDS:
                if field not in item and field in upstream:
                    item[field] = upstream[field]

        return items
