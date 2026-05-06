"""Agent 4 — CRM: sync lead data to Airtable and dispatch daily summaries."""

import asyncio
import json
from datetime import date
from typing import Optional

import httpx

from config import DISCORD_WEBHOOK_URL, RETRY_ATTEMPTS, RETRY_BASE_DELAY
from integrations import airtable


async def _post_discord(webhook_url: str, content: str) -> None:
    delay = RETRY_BASE_DELAY
    last_exc: Optional[Exception] = None
    async with httpx.AsyncClient() as client:
        for attempt in range(RETRY_ATTEMPTS):
            try:
                resp = await client.post(
                    webhook_url,
                    json={"content": content},
                    timeout=10,
                )
                resp.raise_for_status()
                return
            except httpx.HTTPError as exc:
                last_exc = exc
                if attempt < RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(delay)
                    delay *= 2
    raise last_exc


async def sync_qualified_lead(qualify_result: dict, dm_sequence: dict) -> dict:
    """
    Create or update an Airtable record after qualification + DM writing.

    Returns the Airtable record dict.
    """
    profile_url = qualify_result.get("url") or qualify_result.get("profile_url", "")
    existing = await asyncio.to_thread(airtable.get_lead_by_url, profile_url)

    next_action = f"Envoyer opener : {dm_sequence['opener'][:120]}..."

    if existing:
        record = await asyncio.to_thread(
            airtable.upsert_lead,
            record_id=existing["id"],
            name=qualify_result.get("username", ""),
            platform=qualify_result.get("platform", ""),
            profile_url=profile_url,
            niche=qualify_result.get("niche", ""),
            score=qualify_result.get("score", 0),
            stage="CONTACTED",
            last_message=dm_sequence["opener"],
            next_action=next_action,
            reason=qualify_result.get("reason", ""),
        )
    else:
        record = await asyncio.to_thread(
            airtable.upsert_lead,
            name=qualify_result.get("username", ""),
            platform=qualify_result.get("platform", ""),
            profile_url=profile_url,
            niche=qualify_result.get("niche", ""),
            score=qualify_result.get("score", 0),
            stage="CONTACTED",
            last_message=dm_sequence["opener"],
            next_action=next_action,
            reason=qualify_result.get("reason", ""),
        )
    return record


async def sync_reply_event(
    record_id: str,
    reply_result: dict,
    exchange_count: int,
) -> dict:
    """Update Airtable after a reply is sent/received."""
    classification = reply_result.get("classification", "NEUTRAL")
    inject_calendly = reply_result.get("inject_calendly", False)
    flag_human = reply_result.get("flag_human", False)

    stage_map = {
        "POSITIVE": "REPLIED",
        "NEUTRAL": "REPLIED",
        "BUYING_SIGNAL": "REPLIED",
        "NEGATIVE": "REPLIED",
    }
    stage = stage_map.get(classification, "REPLIED")
    if inject_calendly:
        stage = "BOOKED"

    record = await asyncio.to_thread(
        airtable.upsert_lead,
        record_id=record_id,
        name="",
        platform="",
        profile_url="",
        stage=stage,
        last_message=reply_result.get("reply", "")[:500],
        next_action=f"Échange #{exchange_count} — classification: {classification}",
        calendly_sent=inject_calendly,
        flag_human=flag_human,
    )
    return record


async def send_daily_summary() -> dict:
    """Compute and dispatch the daily pipeline summary."""
    summary = await asyncio.to_thread(airtable.get_daily_summary)
    today = date.today().strftime("%d/%m/%Y")

    message = (
        f"📊 **Résumé quotidien du {today}**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📬 Contactés aujourd'hui : **{summary.get('contacted_today', 0)}**\n"
        f"💬 Taux de réponse global : **{summary.get('reply_rate_pct', 0)}%**\n"
        f"📅 Calls réservés : **{summary.get('calls_booked', 0)}**\n"
        f"✅ Closés : **{summary.get('closed', 0)}**\n"
        f"🔴 À traiter manuellement : **{summary.get('flagged_for_human', 0)}**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Total pipeline : {summary.get('total_leads', 0)} leads"
    )

    if DISCORD_WEBHOOK_URL:
        await _post_discord(DISCORD_WEBHOOK_URL, message)

    return summary


async def get_pipeline() -> dict:
    return await asyncio.to_thread(airtable.get_pipeline_stats)
