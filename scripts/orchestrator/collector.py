"""
Result Collector Module

Handles collection, aggregation, and saving of results.
Includes Pydantic-based output validation to catch malformed
LLM outputs before they are persisted to disk.
"""

import json
import os
import sys
import tempfile
import time
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .config import PhaseConfig
from .paths import get_output_root
from .schemas import (
    Phase01bPartial,
    Phase01ePartial,
    Phase02cPartial,
    Phase03Partial,
    Phase04Partial,
    PartialMetadata,
)


# Map phase_id → Pydantic model for the *result_key* wrapper.
# The collector validates the full output envelope (result_key + metadata).
_PHASE_OUTPUT_MODELS: dict[str, type] = {
    "01b": Phase01bPartial,
    "01e": Phase01ePartial,
    "02c": Phase02cPartial,
    "03": Phase03Partial,
    "04": Phase04Partial,
}


_TRUTHY = {"1", "true", "yes", "on"}


def strict_schema_enabled() -> bool:
    """Return whether collector validation failures should block saves."""
    return os.environ.get("SPECA_STRICT_SCHEMA", "").strip().lower() in _TRUTHY


class ResultCollector:
    """
    Collects and saves results from phase execution.

    Responsibilities:
    - Save partial results per batch to disk immediately
    - Validate output data against Pydantic schemas before saving
    - Report validation warnings without blocking saves (lenient mode)
    """

    def __init__(self, config: PhaseConfig):
        self.config = config
        self.output_dir = get_output_root()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.strict_schema = strict_schema_enabled()

        # Validation statistics (accessible for monitoring / circuit breaker)
        self.total_saves: int = 0
        self.validation_warnings: int = 0
        self.validation_errors: int = 0

    def save_partial(
        self,
        results: list[dict[str, Any]],
        worker_id: int,
        batch_index: int,
        timestamp: int | None = None,
    ) -> Path:
        """
        Save partial results from a single batch.

        The output file is validated against the phase-specific Pydantic model.
        Validation failures are logged as warnings but do **not** prevent saving,
        because partial / degraded results are still valuable for resume.

        Args:
            timestamp: Optional timestamp from the batch execution context.
                       Falls back to ``int(time.time())`` if not provided.
        """
        if timestamp is None:
            timestamp = int(time.time())
        # Always use simple {phase_id}_PARTIAL_* naming - no prefix needed
        partial_base = f"{self.config.phase_id}_PARTIAL"

        output_path = self._partial_path(partial_base, worker_id, batch_index, timestamp)

        # Extract processed IDs for fast resume lookup
        id_field = self.config.effective_result_id_field
        processed_ids = [
            str(item[id_field])
            for item in results
            if isinstance(item, dict) and id_field in item
        ]

        # Apply output field filtering if configured
        if self.config.output_fields:
            results = [
                {k: item[k] for k in self.config.output_fields if k in item}
                for item in results
                if isinstance(item, dict)
            ]
        results = self._normalize_results(results)

        output_data = {
            self.config.result_key: results,
            "metadata": {
                "phase": self.config.phase_id,
                "worker_id": worker_id,
                "batch_index": batch_index,
                "item_count": len(results),
                "timestamp": timestamp,
                "processed_ids": processed_ids,
            },
        }

        # --- Output validation ---
        self.total_saves += 1
        self._validate_output(output_data, output_path)

        # Atomic write: write to temp file then rename to prevent
        # partial reads by concurrent workers (e.g. resume scanning).
        fd, tmp_path = tempfile.mkstemp(
            dir=str(self.output_dir), suffix=".json.tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2)
            os.replace(tmp_path, str(output_path))
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

        return output_path

    def _partial_path(
        self,
        partial_base: str,
        worker_id: int,
        batch_index: int,
        timestamp: int,
    ) -> Path:
        """Return a non-clobbering partial path for this worker/batch/timestamp."""
        output_path = (
            self.output_dir
            / f"{partial_base}_W{worker_id}B{batch_index}_{timestamp}.json"
        )
        if not output_path.exists():
            return output_path

        suffix = 1
        while True:
            candidate = (
                self.output_dir
                / f"{partial_base}_W{worker_id}B{batch_index}_{timestamp}_{suffix}.json"
            )
            if not candidate.exists():
                return candidate
            suffix += 1

    def _normalize_results(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Normalize known worker output quirks before validation and save."""
        if self.config.phase_id != "02c":
            return results

        normalized: list[dict[str, Any]] = []
        for item in results:
            if not isinstance(item, dict):
                continue
            entry = dict(item)
            code_scope = entry.get("code_scope")
            if isinstance(code_scope, dict) and isinstance(code_scope.get("locations"), dict):
                code_scope = dict(code_scope)
                code_scope["locations"] = [code_scope["locations"]]
                entry["code_scope"] = code_scope
            self._normalize_02c_location_fields(entry)
            self._filter_02c_locations_to_scope(entry)
            normalized.append(entry)
        return normalized

    def _normalize_02c_location_fields(self, entry: dict[str, Any]) -> None:
        """Normalize loose 02c code location fields before persisting JSON."""
        code_scope = entry.get("code_scope")
        if not isinstance(code_scope, dict):
            return
        locations = code_scope.get("locations")
        if not isinstance(locations, list):
            return

        allowed_roles = {"primary", "caller", "callee", "related"}
        for location in locations:
            if not isinstance(location, dict):
                continue

            if isinstance(location.get("role"), list):
                role = next(
                    (
                        item.strip()
                        for item in location["role"]
                        if isinstance(item, str) and item.strip() in allowed_roles
                    ),
                    "",
                )
                location["role"] = role or "primary"

            note = location.get("note")
            if isinstance(note, list):
                location["note"] = "; ".join(
                    str(item).strip()
                    for item in note
                    if item is not None and str(item).strip()
                )
            elif note is None:
                location["note"] = ""
            elif "note" in location and not isinstance(note, str):
                location["note"] = str(note)

    def _filter_02c_locations_to_scope(self, entry: dict[str, Any]) -> None:
        """Remove 02c code locations outside BUG_BOUNTY_SCOPE components."""
        code_scope = entry.get("code_scope")
        if not isinstance(code_scope, dict):
            return
        locations = code_scope.get("locations")
        if not isinstance(locations, list):
            return

        components, local_checkout = self._load_scope_path_constraints()
        if not components:
            return

        kept = []
        changed = False
        dropped_any = False
        for loc in locations:
            if not isinstance(loc, dict):
                changed = True
                dropped_any = True
                continue

            scoped_path = self._scope_relative_location_path(
                str(loc.get("file", "")),
                components,
                local_checkout,
            )
            if not scoped_path:
                changed = True
                dropped_any = True
                continue

            if scoped_path != loc.get("file"):
                loc = dict(loc)
                loc["file"] = scoped_path
                changed = True
            kept.append(loc)

        if not changed:
            return

        code_scope["locations"] = kept
        if not kept and code_scope.get("resolution_status") == "resolved":
            code_scope["resolution_status"] = "out_of_scope"
            code_scope["resolution_error"] = (
                "Resolved locations were outside BUG_BOUNTY_SCOPE in-scope components"
            )
        elif kept and dropped_any:
            note = "Dropped out-of-scope code locations from BUG_BOUNTY_SCOPE filtering"
            existing = str(code_scope.get("resolution_error") or "")
            code_scope["resolution_error"] = f"{existing}; {note}".strip("; ")

    def _load_scope_path_constraints(self) -> tuple[list[str], str]:
        scope_path = self.output_dir / "BUG_BOUNTY_SCOPE.json"
        target_path = self.output_dir / "TARGET_INFO.json"
        components: list[str] = []
        local_checkout = ""

        try:
            scope_data = json.loads(scope_path.read_text(encoding="utf-8-sig"))
            raw_components = (
                scope_data.get("in_scope", {}).get("components", [])
                if isinstance(scope_data, dict)
                else []
            )
            components = [
                self._normalize_path_string(component)
                for component in raw_components
                if isinstance(component, str) and component.strip()
            ]
        except (OSError, json.JSONDecodeError):
            components = []

        try:
            target_data = json.loads(target_path.read_text(encoding="utf-8-sig"))
            if isinstance(target_data, dict):
                local_checkout = self._normalize_path_string(
                    str(target_data.get("local_checkout") or "")
                )
        except (OSError, json.JSONDecodeError):
            local_checkout = ""

        return components, local_checkout

    @classmethod
    def _is_in_scope_location(
        cls,
        file_path: str,
        components: list[str],
        local_checkout: str,
    ) -> bool:
        return cls._scope_relative_location_path(file_path, components, local_checkout) is not None

    @classmethod
    def _scope_relative_location_path(
        cls,
        file_path: str,
        components: list[str],
        local_checkout: str,
    ) -> str | None:
        candidate = cls._normalize_path_string(file_path)
        candidates = [candidate]
        checkout = local_checkout.rstrip("/")
        for prefix in cls._local_checkout_prefixes(checkout):
            if candidate.startswith(prefix + "/"):
                candidates.insert(0, candidate[len(prefix) + 1:])

        for path in candidates:
            if any(cls._matches_component(path, component) for component in components):
                return path
        return None

    @staticmethod
    def _local_checkout_prefixes(local_checkout: str) -> list[str]:
        prefixes: list[str] = []
        checkout = local_checkout.rstrip("/")
        if checkout:
            prefixes.append(checkout)
            marker = "target_workspace/"
            if marker in checkout:
                prefixes.append(checkout[checkout.index(marker):])

        seen: set[str] = set()
        unique: list[str] = []
        for prefix in prefixes:
            if prefix and prefix not in seen:
                seen.add(prefix)
                unique.append(prefix)
        return unique

    @staticmethod
    def _matches_component(path: str, component: str) -> bool:
        if not component:
            return False
        if not any(char in component for char in "*?[]"):
            component = component.rstrip("/")
            return path == component or path.startswith(component + "/")
        return (
            fnmatchcase(path, component)
            or fnmatchcase(path, component.replace("**/", ""))
        )

    @staticmethod
    def _normalize_path_string(path: str) -> str:
        return path.replace("\\", "/").strip().lstrip("./")

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def _validate_output(
        self,
        output_data: dict[str, Any],
        output_path: Path,
    ) -> None:
        """
        Validate *output_data* against the phase-specific Pydantic model.

        By default, validation is lenient: warnings are printed to stderr and
        counters are incremented, but the save is never blocked. Set
        ``SPECA_STRICT_SCHEMA=1`` to make validation failures raise before
        writing the partial file.
        """
        # 1. Validate metadata envelope
        meta_raw = output_data.get("metadata", {})
        try:
            PartialMetadata.model_validate(meta_raw)
        except ValidationError as ve:
            self.validation_warnings += 1
            print(
                f"Warning: Output metadata validation warning ({output_path.name}): "
                f"{ve.error_count()} error(s)",
                file=sys.stderr,
            )
            for err in ve.errors():
                print(f"    {err['loc']}: {err['msg']}", file=sys.stderr)
            if self.strict_schema:
                raise

        # 2. Validate result payload against phase-specific model
        model_cls = _PHASE_OUTPUT_MODELS.get(self.config.phase_id)
        if model_cls is None:
            # Phase 01a has no structured partial output
            return

        try:
            model_cls.model_validate(output_data)
        except ValidationError as ve:
            self.validation_errors += 1
            print(
                f"Warning: Output schema validation warning ({output_path.name}): "
                f"{ve.error_count()} error(s)",
                file=sys.stderr,
            )
            for err in ve.errors():
                print(f"    {err['loc']}: {err['msg']}", file=sys.stderr)
            if self.strict_schema:
                raise

    def get_validation_summary(self) -> dict[str, int]:
        """Return a summary of validation statistics."""
        return {
            "total_saves": self.total_saves,
            "validation_warnings": self.validation_warnings,
            "validation_errors": self.validation_errors,
        }
