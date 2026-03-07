"""Discord Webhook notification for phase results."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from .run_manager import RunInfo, RunStatus

logger = logging.getLogger(__name__)

# Webhook URL (ローカル専用)
DISCORD_WEBHOOK_URL = (
    "https://discord.com/api/webhooks/"
    "1464948038199017581/"
    "kEzEAfmQbrGS7-4EwiKe-paMAksGpT7880sop4SMNLV6-Lb__DxzcWXnVISOwPXCFIiI"
)

# Embed colors
COLOR_SUCCESS = 0x2ECC71  # green
COLOR_FAILED = 0xE74C3C  # red
COLOR_CANCELLED = 0x95A5A6  # grey


def _format_elapsed(start: float, end: float | None) -> str:
    if end is None:
        end = time.time()
    secs = int(end - start)
    m, s = divmod(secs, 60)
    return f"{m}m {s}s" if m > 0 else f"{s}s"


def _build_embed(run: RunInfo) -> dict[str, Any]:
    """Build a Discord embed from a completed RunInfo."""
    phase_id = run.phase_id
    status = run.status.value
    elapsed = _format_elapsed(run.created_at, run.completed_at)

    if run.status == RunStatus.COMPLETED:
        color = COLOR_SUCCESS
        title = f"Phase {phase_id} -- 完了"
    elif run.status == RunStatus.CANCELLED:
        color = COLOR_CANCELLED
        title = f"Phase {phase_id} -- キャンセル"
    else:
        color = COLOR_FAILED
        title = f"Phase {phase_id} -- 失敗"

    fields: list[dict[str, Any]] = [
        {"name": "ステータス", "value": status, "inline": True},
        {"name": "所要時間", "value": elapsed, "inline": True},
    ]

    # Extract result details
    result = run.result or {}
    total_results = result.get("total_results")
    if total_results is not None:
        fields.append({"name": "結果件数", "value": str(total_results), "inline": True})

    cost_info = result.get("cost") or {}
    cost_usd = cost_info.get("total_cost_usd")
    if cost_usd is not None:
        fields.append({"name": "コスト", "value": f"${cost_usd:.2f}", "inline": True})

    budget_pct = cost_info.get("budget_utilization_pct")
    if budget_pct is not None:
        fields.append({"name": "予算消化率", "value": f"{budget_pct:.1f}%", "inline": True})

    if run.error:
        err_text = run.error[:200] + "..." if len(run.error) > 200 else run.error
        fields.append({"name": "エラー", "value": f"```{err_text}```", "inline": False})

    return {
        "title": title,
        "color": color,
        "fields": fields,
        "footer": {"text": f"run_id: {run.run_id}"},
    }


async def send_phase_result(run: RunInfo) -> None:
    """Send phase result to Discord webhook. Errors are logged but never raised."""
    try:
        embed = _build_embed(run)
        payload = {"embeds": [embed]}

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(DISCORD_WEBHOOK_URL, json=payload)
            if resp.status_code >= 400:
                logger.warning("Discord webhook returned %d: %s", resp.status_code, resp.text[:200])
    except Exception:
        logger.warning("Failed to send Discord notification", exc_info=True)
