"""Airtable CRM integration — thin wrapper around pyairtable."""

from datetime import date
from typing import Optional
from pyairtable import Api
from config import AIRTABLE_API_KEY, AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME

PIPELINE_STAGES = ["NEW", "CONTACTED", "REPLIED", "BOOKED", "CLOSED"]

_api = Api(AIRTABLE_API_KEY)
_table = _api.table(AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)


def _table_ref():
    return _api.table(AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)


def upsert_lead(
    *,
    record_id: Optional[str] = None,
    name: str,
    platform: str,
    profile_url: str,
    niche: str = "",
    score: int = 0,
    stage: str = "NEW",
    last_message: str = "",
    next_action: str = "",
    calendly_sent: bool = False,
    flag_human: bool = False,
    reason: str = "",
) -> dict:
    """Create or update a lead record. Returns the Airtable record dict."""
    t = _table_ref()
    fields = {
        "Name": name,
        "Platform": platform,
        "Profile URL": profile_url,
        "Niche": niche,
        "Score": score,
        "Stage": stage,
        "Last Message": last_message[:1000] if last_message else "",
        "Next Action": next_action,
        "Calendly Sent": calendly_sent,
        "Flag Human": flag_human,
        "Reason": reason[:500] if reason else "",
        "Last Updated": date.today().isoformat(),
    }
    if record_id:
        return t.update(record_id, fields)
    return t.create(fields)


def get_lead_by_url(profile_url: str) -> Optional[dict]:
    t = _table_ref()
    formula = f"{{Profile URL}} = '{profile_url}'"
    records = t.all(formula=formula)
    return records[0] if records else None


def update_stage(record_id: str, stage: str) -> dict:
    if stage not in PIPELINE_STAGES:
        raise ValueError(f"Invalid stage '{stage}'. Must be one of {PIPELINE_STAGES}")
    t = _table_ref()
    return t.update(record_id, {"Stage": stage, "Last Updated": date.today().isoformat()})


def get_pipeline_stats() -> dict:
    t = _table_ref()
    records = t.all()
    stats: dict = {s: 0 for s in PIPELINE_STAGES}
    total = len(records)
    calendly_sent = sum(1 for r in records if r["fields"].get("Calendly Sent"))
    flagged = sum(1 for r in records if r["fields"].get("Flag Human"))

    for rec in records:
        stage = rec["fields"].get("Stage", "NEW")
        if stage in stats:
            stats[stage] += 1

    contacted = total - stats.get("NEW", 0)
    replied = stats.get("REPLIED", 0) + stats.get("BOOKED", 0) + stats.get("CLOSED", 0)
    reply_rate = round(replied / contacted * 100, 1) if contacted else 0.0

    return {
        "total_leads": total,
        "by_stage": stats,
        "contacted": contacted,
        "replied": replied,
        "reply_rate_pct": reply_rate,
        "calls_booked": stats.get("BOOKED", 0),
        "closed": stats.get("CLOSED", 0),
        "calendly_sent": calendly_sent,
        "flagged_for_human": flagged,
    }


def get_daily_summary() -> dict:
    stats = get_pipeline_stats()
    t = _table_ref()
    today = date.today().isoformat()
    today_records = t.all(formula=f"{{Last Updated}} = '{today}'")
    stats["contacted_today"] = sum(
        1 for r in today_records if r["fields"].get("Stage") != "NEW"
    )
    return stats
