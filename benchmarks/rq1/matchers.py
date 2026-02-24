#!/usr/bin/env python3
"""RQ1 matching logic — LLM-based root-cause matching."""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass
class Issue:
    issue_id: str
    title: str
    description: str
    text: str
    normalized: str
    tokens: set[str]


@dataclass
class AuditItem:
    item_id: str
    description: str
    snippet: str
    file: str
    line: str
    text: str
    normalized: str
    tokens: set[str]
    classification: str | None = None


def normalize_text(text: str) -> str:
    lowered = text.lower()
    lowered = re.sub(r"[^a-z0-9_]+", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    return lowered


def tokenize(text: str) -> set[str]:
    if not text:
        return set()
    return set(re.findall(r"[a-z0-9_]+", text.lower()))


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def load_csv_issues(path: Path) -> list[Issue]:
    import csv

    issues: list[Issue] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            title = (row.get("title") or "").strip()
            description = (row.get("description") or "").strip()
            issue_id = str(row.get("number") or "").strip()
            text = f"{title}\n{description}".strip()
            normalized = normalize_text(text)
            tokens = tokenize(text)
            issues.append(Issue(issue_id, title, description, text, normalized, tokens))
    return issues


def build_audit_text(raw: dict) -> tuple[str, str, str, str, str, str, str]:
    """Extract fields from a Phase 03 audit item.

    Phase 03 schema: property_id, classification, code_path, proof_trace, attack_scenario, checklist_id
    code_path format: "file.go::func::L10-20"
    """
    item_id = str(raw.get("property_id") or "")
    description = str(raw.get("proof_trace") or "")
    snippet = str(raw.get("attack_scenario") or "")
    classification = str(raw.get("classification") or "")

    code_path = str(raw.get("code_path") or "")
    parts = code_path.split("::")
    file = parts[0] if parts else ""
    line = parts[-1] if len(parts) > 1 else ""

    text_parts = [description, snippet, file, line]
    text = "\n".join(part for part in text_parts if part).strip()
    return item_id, description, snippet, file, line, text, classification


def is_selected_audit_item(
    raw: dict,
    classification_filter: set[str] | None,
) -> bool:
    if classification_filter is None:
        return True
    value = raw.get("classification")
    if isinstance(value, str) and value.strip().lower() in classification_filter:
        return True
    return False


def extract_audit_items(
    files: Iterable[Path],
    classification_filter: set[str] | None = None,
) -> list[AuditItem]:
    items: list[AuditItem] = []
    for path in files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        raw_items: list[dict] = []
        if isinstance(payload, dict) and isinstance(payload.get("audit_items"), list):
            raw_items = [item for item in payload["audit_items"] if isinstance(item, dict)]

        if not raw_items:
            continue

        for raw in raw_items:
            if not is_selected_audit_item(raw, classification_filter):
                continue
            item_id, description, snippet, file, line, text, classification = build_audit_text(raw)
            normalized = normalize_text(text)
            tokens = tokenize(text)
            items.append(
                AuditItem(
                    item_id, description, snippet, file, line,
                    text, normalized, tokens, classification=classification,
                )
            )
    return items


def call_llm(prompt: str) -> str:
    env = os.environ.copy()
    # Prevent nested-session detection (same as runner.py)
    for var in ("CLAUDECODE", "CLAUDE_CODE_SESSION_ID"):
        env.pop(var, None)

    model = env.get("RQ1_MODEL", "haiku")
    command = ["claude", "--output-format", "json", "--model", model, "-p", prompt]

    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        print(f"[rq1] call_llm failed (rc={result.returncode}): {result.stderr[:300] if result.stderr else ''}")
        return ""

    # claude --output-format json returns {"type":"result","result":"<llm text>"}
    # Unwrap the envelope to get the raw LLM text.
    try:
        envelope = json.loads(result.stdout)
        if isinstance(envelope, dict) and "result" in envelope:
            return str(envelope["result"])
    except (json.JSONDecodeError, TypeError):
        pass
    return result.stdout


def extract_json_from_text(text: str) -> dict | None:
    if not text:
        return None
    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            return payload
        if isinstance(payload, list) and payload:
            return payload[0] if isinstance(payload[0], dict) else None
    except json.JSONDecodeError:
        pass

    try:
        wrapper = json.loads(text)
        if isinstance(wrapper, dict) and "content" in wrapper:
            content = wrapper.get("content")
            if isinstance(content, list):
                combined = "".join(part.get("text", "") for part in content if isinstance(part, dict))
            else:
                combined = str(content)
            match = re.search(r"\{.*\}", combined, flags=re.DOTALL)
            if match:
                return json.loads(match.group(0))
    except Exception:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None


def _truncate_description(description: str, max_chars: int = 300) -> str:
    if len(description) <= max_chars:
        return description
    return description[:max_chars].rstrip() + "..."


def llm_match(audit_item: AuditItem, candidates: list[Issue], llm_id: str) -> tuple[bool, str | None, float, str]:
    """Returns (matched, issue_id, confidence, raw_response)."""
    if not candidates:
        return False, None, 0.0, ""

    candidate_block = []
    for idx, issue in enumerate(candidates):
        truncated = _truncate_description(issue.description)
        candidate_block.append(
            f"[{idx}] ID={issue.issue_id}\nTitle: {issue.title}\nDescription: {truncated}\n"
        )

    prompt = (
        "Does the following audit finding share the same root cause as any candidate issue?\n"
        'Respond with JSON only: {"match": true|false, "candidate_index": number|null, "confidence": 0.0-1.0}\n\n'
        "AUDIT FINDING:\n"
        f"{audit_item.text}\n\n"
        f"CANDIDATES:\n"
        + "\n".join(candidate_block)
        + "\n"
    )

    print(f"[rq1] {llm_id}: llm_match start (candidates={len(candidates)}, prompt_chars={len(prompt)})")
    raw = call_llm(prompt)
    print(f"[rq1] {llm_id}: llm_match done (bytes={len(raw) if raw else 0})")
    if raw:
        preview = raw[:500].replace("\n", "\\n")
        print(f"[rq1] {llm_id}: raw response: {preview}")

    candidate_ids = [c.issue_id for c in candidates]
    matched, issue_id, confidence = _parse_llm_response(raw, candidate_ids, llm_id)
    return matched, issue_id, confidence, raw


def _rank_candidates_by_jaccard(
    audit_item: AuditItem,
    issues: list[Issue],
    max_candidates: int = 50,
) -> list[Issue]:
    if len(issues) <= max_candidates:
        return list(issues)
    scored = []
    for issue in issues:
        score = jaccard(audit_item.tokens, issue.tokens)
        scored.append((score, issue))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [issue for _, issue in scored[:max_candidates]]


def _parse_llm_response(
    raw: str,
    candidate_ids: list[str],
    llm_id: str,
) -> tuple[bool, str | None, float]:
    """Parse a cached LLM response into (matched, issue_id, confidence)."""
    payload = extract_json_from_text(raw) or {}
    match = bool(payload.get("match"))
    idx = payload.get("candidate_index")
    confidence = payload.get("confidence")
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.0
    if match and isinstance(idx, int) and 0 <= idx < len(candidate_ids):
        return True, candidate_ids[idx], confidence
    return False, None, confidence


def match_items(
    audit_items: list[AuditItem],
    issues: list[Issue],
    llm_max: int,
    cache_path: Path | None = None,
) -> tuple[dict[str, dict], int]:
    matches: dict[str, dict] = {}
    llm_calls = 0

    cache_handle = None
    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_handle = cache_path.open("w", encoding="utf-8")

    try:
        for item in audit_items:
            if llm_calls >= llm_max:
                break
            candidates = _rank_candidates_by_jaccard(item, issues)
            if not candidates:
                continue
            llm_calls += 1
            llm_id = item.item_id or f"item_{llm_calls}"
            matched, issue_id, confidence, raw = llm_match(item, candidates, llm_id)

            if cache_handle:
                cache_record = {
                    "item_id": item.item_id,
                    "raw": raw,
                    "candidate_ids": [c.issue_id for c in candidates],
                }
                cache_handle.write(json.dumps(cache_record, ensure_ascii=False) + "\n")
                cache_handle.flush()

            if matched and issue_id:
                matches[item.item_id] = {
                    "issue_id": issue_id,
                    "score": confidence,
                }
    finally:
        if cache_handle:
            cache_handle.close()

    return matches, llm_calls


def reparse_items(cache_path: Path) -> tuple[dict[str, dict], int]:
    """Re-parse cached LLM responses without calling the LLM again."""
    matches: dict[str, dict] = {}
    total = 0

    for line in cache_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        total += 1
        item_id = record.get("item_id", "")
        raw = record.get("raw", "")
        candidate_ids = record.get("candidate_ids", [])
        llm_id = item_id or f"item_{total}"

        matched, issue_id, confidence = _parse_llm_response(raw, candidate_ids, llm_id)
        if matched and issue_id:
            matches[item_id] = {
                "issue_id": issue_id,
                "score": confidence,
            }
        print(f"[rq1] reparse {llm_id}: matched={matched}, issue_id={issue_id}, confidence={confidence}")

    return matches, total
