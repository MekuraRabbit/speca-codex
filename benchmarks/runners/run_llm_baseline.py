#!/usr/bin/env python3
"""Run an LLM baseline benchmark runner (command-template driven)."""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from benchmarks.bench_utils import (
    extract_code,
    extract_id,
    guess_extension,
    iter_jsonl,
    normalize_bool,
    sanitize_filename,
    write_jsonl,
)
from benchmarks.runners.base_runner import (
    add_common_args,
    command_spec_from_args,
    default_metadata_path,
    default_prediction_loader,
    default_results_path,
    run_command,
    write_metadata,
)

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = ROOT_DIR / "benchmarks" / "data" / "primevul" / "primevul_test_paired.jsonl"
DEFAULT_TMP = ROOT_DIR / "benchmarks" / "tmp" / "llm_baseline"
DEFAULT_METADATA = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run LLM baseline benchmark runner.")
    add_common_args(parser)
    parser.set_defaults(
        dataset=DEFAULT_DATASET,
        tmp_dir=DEFAULT_TMP,
        tool_name="llm_baseline",
    )
    return parser.parse_args()


def _resolve_llm_config() -> tuple[str, dict]:
    """Resolve LLM model and extra kwargs from environment.

    Priority:
    1. LLM_BASE_URL + LLM_API_KEY (OpenAI-compatible endpoint)
    2. ANTHROPIC_API_KEY (direct Anthropic)
    3. Default claude model (requires ANTHROPIC_API_KEY at runtime)
    """
    base_url = os.environ.get("LLM_BASE_URL", "").strip()
    llm_key = os.environ.get("LLM_API_KEY", "").strip()
    llm_model = os.environ.get("LLM_MODEL", "").strip()

    if base_url and llm_key:
        model = llm_model or "openai/gpt-4o-mini"
        return model, {"api_base": base_url, "api_key": llm_key}

    if llm_model:
        return llm_model, {}

    return "claude-sonnet-4-20250514", {}


def call_llm(prompt: str, model: str | None = None) -> tuple[str, str | None]:
    """Call LLM via litellm (API-based, more reliable than CLI in CI)."""
    try:
        import litellm

        resolved_model, extra_kwargs = _resolve_llm_config()
        use_model = model or resolved_model

        response = litellm.completion(
            model=use_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=256,
            temperature=0,
            **extra_kwargs,
        )
        text = response.choices[0].message.content or ""
        return text, None
    except ImportError:
        return _call_claude_cli(prompt)
    except Exception as e:
        return "", f"litellm_error: {str(e)[:200]}"


def _call_claude_cli(prompt: str) -> tuple[str, str | None]:
    """Fallback: call claude CLI directly."""
    if shutil.which("claude") is None:
        return "", "claude_not_found"
    # Remove CLAUDECODE env var to allow nested invocation from within
    # a Claude Code session (e.g. when running benchmarks in CI).
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
    result = subprocess.run(
        ["claude", "--output-format", "json", "-p", prompt],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        return "", f"claude_error: {stderr[:200]}" if stderr else "claude_error"
    return result.stdout, None


def extract_text_from_claude(raw: str) -> str:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return raw
    if isinstance(payload, dict) and "content" in payload:
        content = payload.get("content")
        if isinstance(content, list):
            return "".join(part.get("text", "") for part in content if isinstance(part, dict))
        return str(content)
    return raw


def parse_prediction(text: str) -> bool | None:
    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            for key in ("predicted_vulnerable", "vulnerable", "is_vulnerable"):
                if key in payload:
                    return normalize_bool(payload.get(key))
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        try:
            payload = json.loads(match.group(0))
            if isinstance(payload, dict):
                for key in ("predicted_vulnerable", "vulnerable", "is_vulnerable"):
                    if key in payload:
                        return normalize_bool(payload.get(key))
        except json.JSONDecodeError:
            pass

    return normalize_bool(text)


def build_prompt(code: str) -> str:
    return (
        "You are a security classifier. Determine if the following code is vulnerable. "
        'Respond with JSON: {"predicted_vulnerable": true/false}.\n\n'
        f"{code}"
    )


def main() -> int:
    args = parse_args()
    if not args.dataset.exists():
        print(f"Dataset not found: {args.dataset}", file=sys.stderr)
        return 1

    if args.output is None:
        args.output = default_results_path("llm_baseline", args.dataset)
    if args.metadata is None:
        args.metadata = default_metadata_path("llm_baseline", args.dataset)
    spec = command_spec_from_args(args)
    spec.tmp_dir.mkdir(parents=True, exist_ok=True)
    results = []

    for idx, record in enumerate(iter_jsonl(spec.dataset)):
        if spec.limit and idx >= spec.limit:
            break

        case_id = extract_id(record, idx)
        code = extract_code(record)
        if not code:
            results.append(
                {
                    "id": case_id,
                    "predicted_vulnerable": None,
                    "error": "missing_code",
                }
            )
            continue

        ext = guess_extension(record)
        safe_id = sanitize_filename(case_id)
        code_path = spec.tmp_dir / f"{safe_id}.{ext}"
        code_path.write_text(code, encoding="utf-8", errors="ignore")

        output_path = spec.tmp_dir / f"{safe_id}.prediction.json"

        if spec.command:
            return_code, stderr = run_command(
                spec.command, code_path, output_path, case_id, spec.use_shell, spec.timeout
            )
            prediction, extras, error = default_prediction_loader(output_path)
            if error:
                results.append(
                    {
                        "id": case_id,
                        "predicted_vulnerable": None,
                        "error": error,
                        "exit_code": return_code,
                        "stderr": stderr,
                    }
                )
            else:
                row = {"id": case_id, "predicted_vulnerable": prediction, "exit_code": return_code}
                if extras:
                    row.update(extras)
                results.append(row)
        else:
            prompt = build_prompt(code)
            raw, err = call_llm(prompt)
            if err:
                results.append(
                    {
                        "id": case_id,
                        "predicted_vulnerable": None,
                        "error": err,
                    }
                )
                continue
            text = extract_text_from_claude(raw)
            prediction = parse_prediction(text)
            if prediction is None:
                results.append(
                    {
                        "id": case_id,
                        "predicted_vulnerable": None,
                        "error": "llm_unparseable_output",
                    }
                )
            else:
                results.append(
                    {
                        "id": case_id,
                        "predicted_vulnerable": prediction,
                    }
                )

    write_jsonl(spec.output, results)
    extra = {"provider": "litellm"} if not spec.command else None
    write_metadata(spec, extra=extra)
    print(f"Wrote {len(results)} LLM baseline results to {spec.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
