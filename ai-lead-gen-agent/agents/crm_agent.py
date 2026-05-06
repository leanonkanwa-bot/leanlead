import time
from datetime import date, datetime
from typing import Optional

import httpx
from pyairtable import Api

from config import (
    AIRTABLE_API_KEY,
    AIRTABLE_BASE_ID,
    AIRTABLE_TABLE_NAME,
    DISCORD_WEBHOOK_URL,
    RETRY_ATTEMPTS,
    RETRY_BASE_DELAY,
)

api = Api(AIRTABLE_API_KEY)
table = api.table(AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)

STAGES = ["NEW", "CONTACTED", "REPLIED", "BOOKED", "CLOSED"]


# ── Core CRUD ─────────────────────────────────────────────────────────────────

def create_lead(lead: dict) -> dict:
    return table.create({
        "Name":         lead.get("username") or lead.get("url", ""),
        "Platform":     lead.get("platform", ""),
        "Profile URL":  lead.get("url", ""),
        "Niche":        lead.get("niche", ""),
        "Score":        lead.get("score", 0),
        "Stage":        "NEW",
        "Last Message": "",
        "Next Action":  "Send opener",
        "Calendly Sent": False,
        "Flag Human":   False,
        "Reason":       lead.get("reason", "")[:500],
        "Date Added":   datetime.now().isoformat(),
    })


def update_stage(record_id: str, stage: str, last_message: str = "") -> dict:
    if stage not in STAGES:
        raise ValueError(f"Stage invalide : {stage}")
    return table.update(record_id, {
        "Stage":        stage,
        "Last Message": last_message[:1000],
        "Updated At":   datetime.now().isoformat(),
    })


def get_lead_by_url(profile_url: str) -> Optional[dict]:
    formula = f"{{Profile URL}} = '{profile_url}'"
    records = table.all(formula=formula)
    return records[0] if records else None


def get_pipeline_stats() -> dict:
    records = table.all()
    stats = {stage: 0 for stage in STAGES}
    for record in records:
        stage = record["fields"].get("Stage", "NEW")
        if stage in stats:
            stats[stage] += 1
    total = len(records)
    contacted = total - stats.get("NEW", 0)
    replied = stats.get("REPLIED", 0) + stats.get("BOOKED", 0) + stats.get("CLOSED", 0)
    return {
        "total_leads":      total,
        "by_stage":         stats,
        "contacted":        contacted,
        "replied":          replied,
        "reply_rate_pct":   round(replied / contacted * 100, 1) if contacted else 0.0,
        "calls_booked":     stats.get("BOOKED", 0),
        "closed":           stats.get("CLOSED", 0),
        "calendly_sent":    sum(1 for r in records if r["fields"].get("Calendly Sent")),
        "flagged_for_human": sum(1 for r in records if r["fields"].get("Flag Human")),
    }


# ── Agent-facing helpers ───────────────────────────────────────────────────────

def sync_qualified_lead(qualify_result: dict, dm_sequence: dict) -> dict:
    """Create or update Airtable record after qualification + DM writing."""
    profile_url = qualify_result.get("url") or qualify_result.get("profile_url", "")
    existing = get_lead_by_url(profile_url)
    next_action = f"Envoyer opener : {dm_sequence['opener'][:120]}..."

    fields = {
        "Name":         qualify_result.get("username") or profile_url,
        "Platform":     qualify_result.get("platform", ""),
        "Profile URL":  profile_url,
        "Niche":        qualify_result.get("niche", ""),
        "Score":        qualify_result.get("score", 0),
        "Stage":        "CONTACTED",
        "Last Message": dm_sequence.get("opener", "")[:1000],
        "Next Action":  next_action,
        "Reason":       qualify_result.get("reason", "")[:500],
        "Updated At":   datetime.now().isoformat(),
    }
    if existing:
        return table.update(existing["id"], fields)
    fields["Date Added"] = datetime.now().isoformat()
    return table.create(fields)


def sync_reply_event(record_id: str, reply_result: dict, exchange_count: int) -> dict:
    """Update Airtable after a reply is generated."""
    classification = reply_result.get("classification", "NEUTRAL")
    inject_calendly = reply_result.get("inject_calendly", False)
    stage = "BOOKED" if inject_calendly else "REPLIED"
    return table.update(record_id, {
        "Stage":         stage,
        "Last Message":  reply_result.get("reply", "")[:1000],
        "Next Action":   f"Échange #{exchange_count} — {classification}",
        "Calendly Sent": inject_calendly,
        "Flag Human":    reply_result.get("flag_human", False),
        "Updated At":    datetime.now().isoformat(),
    })


# ── Daily summary ──────────────────────────────────────────────────────────────

def _post_discord(webhook_url: str, content: str) -> None:
    delay = RETRY_BASE_DELAY
    last_exc: Optional[Exception] = None
    for attempt in range(RETRY_ATTEMPTS):
        try:
            resp = httpx.post(webhook_url, json={"content": content}, timeout=10)
            resp.raise_for_status()
            return
        except httpx.HTTPError as exc:
            last_exc = exc
            if attempt < RETRY_ATTEMPTS - 1:
                time.sleep(delay)
                delay *= 2
    raise last_exc


def send_daily_summary() -> dict:
    stats = get_pipeline_stats()
    today = date.today().strftime("%d/%m/%Y")
    message = (
        f"📊 **Résumé quotidien du {today}**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📬 Total leads : **{stats['total_leads']}**\n"
        f"💬 Taux de réponse : **{stats['reply_rate_pct']}%**\n"
        f"📅 Calls réservés : **{stats['calls_booked']}**\n"
        f"✅ Closés : **{stats['closed']}**\n"
        f"🔴 À traiter manuellement : **{stats['flagged_for_human']}**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Pipeline : NEW={stats['by_stage']['NEW']} | "
        f"CONTACTED={stats['by_stage']['CONTACTED']} | "
        f"REPLIED={stats['by_stage']['REPLIED']} | "
        f"BOOKED={stats['by_stage']['BOOKED']} | "
        f"CLOSED={stats['by_stage']['CLOSED']}"
    )
    if DISCORD_WEBHOOK_URL:
        _post_discord(DISCORD_WEBHOOK_URL, message)
    return stats


# ── Pipeline (alias for API route) ────────────────────────────────────────────

def get_pipeline() -> dict:
    return get_pipeline_stats()
