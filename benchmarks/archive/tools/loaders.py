#!/usr/bin/env python3
"""Loaders for tool result formats."""

from __future__ import annotations

import json
from pathlib import Path

from benchmarks.bench_utils import iter_jsonl, normalize_bool


def load_semgrep_results(path: Path) -> tuple[dict[str, bool | None], int, dict[str, dict]] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    # BUG-BEN11: Handle dict payload (wrap in list or extract results)
    if isinstance(payload, dict):
        if "results" in payload and isinstance(payload["results"], list):
            payload = payload["results"]
        else:
            payload = [payload]
    if not isinstance(payload, list):
        return None
    predictions: dict[str, bool | None] = {}
    extras: dict[str, dict] = {}
    error_count = 0
    for row in payload:
        if not isinstance(row, dict):
            continue
        func_id = row.get("func_id") or row.get("id")
        if func_id is None:
            continue
        # BUG-BEN10: Count actual errors
        if row.get("error"):
            error_count += 1
        findings = row.get("semgrep_findings") or []
        predictions[str(func_id)] = bool(findings)
        extras[str(func_id)] = {"findings_count": len(findings)}
    return predictions, error_count, extras


def load_cppcheck_results(path: Path) -> tuple[dict[str, bool | None], int, dict[str, dict]] | None:
    """Load cppcheck results (JSON list with cppcheck_findings arrays)."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        return None
    predictions: dict[str, bool | None] = {}
    extras: dict[str, dict] = {}
    error_count = 0
    for row in payload:
        if not isinstance(row, dict):
            continue
        func_id = row.get("func_id") or row.get("id")
        if func_id is None:
            continue
        if row.get("error"):
            error_count += 1
        findings = row.get("cppcheck_findings") or []
        # Filter: only count warning/error/style severity (not information)
        real_findings = [f for f in findings if f.get("severity") not in ("information", "debug", "")]
        predictions[str(func_id)] = bool(real_findings)
        extras[str(func_id)] = {"findings_count": len(real_findings), "findings": real_findings}
    return predictions, error_count, extras


def load_flawfinder_results(path: Path) -> tuple[dict[str, bool | None], int, dict[str, dict]] | None:
    """Load flawfinder results (JSON list with flawfinder_findings arrays)."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        return None
    predictions: dict[str, bool | None] = {}
    extras: dict[str, dict] = {}
    error_count = 0
    for row in payload:
        if not isinstance(row, dict):
            continue
        func_id = row.get("func_id") or row.get("id")
        if func_id is None:
            continue
        if row.get("error"):
            error_count += 1
        findings = row.get("flawfinder_findings") or []
        predictions[str(func_id)] = bool(findings)
        extras[str(func_id)] = {"findings_count": len(findings), "findings": findings}
    return predictions, error_count, extras


def load_jsonl_predictions(path: Path) -> tuple[dict[str, bool | None], int, dict[str, dict]] | None:
    try:
        rows = list(iter_jsonl(path))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None
    predictions: dict[str, bool | None] = {}
    extras: dict[str, dict] = {}
    error_count = 0
    for row in rows:
        func_id = row.get("id") or row.get("func_id") or row.get("sample_id")
        if func_id is None:
            continue
        prediction = normalize_bool(row.get("predicted_vulnerable"))
        predictions[str(func_id)] = prediction
        if row.get("error"):
            error_count += 1
        extras[str(func_id)] = row
    return predictions, error_count, extras
