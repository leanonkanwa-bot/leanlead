"""
Analytics router
GET /api/analytics  → aggregated metrics for the coach's dashboard
"""
import json
from collections import Counter
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import get_current_coach
from ..database import get_db
from .. import models

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _pipeline_forecast(leads: list, offer_price: float) -> dict:
    """
    Weighted revenue forecast for active pipeline leads.
    Conversion probability tiers: score ≥80 → 30%, 60-79 → 15%, 40-59 → 7%, <40 → 2%
    """
    active_stages = {"new", "contacted", "replied"}
    weighted_value = 0.0
    for lead in leads:
        if lead.stage not in active_stages:
            continue
        score = lead.qualification_score or 0
        if score >= 80:
            prob = 0.30
        elif score >= 60:
            prob = 0.15
        elif score >= 40:
            prob = 0.07
        else:
            prob = 0.02
        weighted_value += prob * offer_price
    active_count = sum(1 for l in leads if l.stage in active_stages)
    return {
        "weighted_value": round(weighted_value),
        "active_leads": active_count,
    }


def _current_contact_windows() -> list[str]:
    """Return best_contact_time values that match the current UTC time."""
    now = datetime.utcnow()
    hour = now.hour
    weekday = now.weekday()  # 0=Mon … 6=Sun
    windows = ["anytime"]
    if 6 <= hour < 12:
        windows.append("morning")
    if 17 <= hour < 22:
        windows.append("evening")
    if weekday >= 5:
        windows.append("weekend")
    return windows


@router.get("")
def get_analytics(
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    leads = db.query(models.Lead).filter(models.Lead.coach_id == coach.id).all()

    # ── Volume ──
    leads_this_week = sum(1 for l in leads if l.created_at and l.created_at >= week_ago)
    leads_this_month = sum(1 for l in leads if l.created_at and l.created_at >= month_ago)

    # ── Stage breakdown ──
    by_stage = Counter(l.stage for l in leads)
    contacted = by_stage.get("contacted", 0)
    replied   = by_stage.get("replied",   0)
    booked    = by_stage.get("booked",    0)
    closed    = by_stage.get("closed",    0)

    # Reply rate: share of messaged leads that replied
    reply_denom = contacted + replied + booked + closed
    reply_rate  = (replied + booked + closed) / reply_denom if reply_denom else 0

    # Booking rate: share of replied leads that booked
    booking_denom = replied + booked + closed
    booking_rate  = (booked + closed) / booking_denom if booking_denom else 0

    # ── Hashtag performance (from completed prospecting jobs) ──
    jobs = (
        db.query(models.ProspectingJob)
        .filter(
            models.ProspectingJob.coach_id == coach.id,
            models.ProspectingJob.status == "done",
        )
        .all()
    )
    hashtag_leads: dict[str, float] = {}
    for job in jobs:
        tags = json.loads(job.hashtags or "[]")
        if not tags:
            continue
        per_tag = job.leads_found / len(tags)
        for tag in tags:
            hashtag_leads[tag] = hashtag_leads.get(tag, 0) + per_tag

    top_hashtags = sorted(hashtag_leads.items(), key=lambda x: x[1], reverse=True)[:6]

    # ── Follow-up conversion (which D-day triggered the reply?) ──
    d2_conv = d4_conv = d7_conv = direct_conv = 0
    for lead in leads:
        if lead.stage not in ("replied", "booked", "closed"):
            continue
        if not lead.reply_received_at:
            continue
        rt = lead.reply_received_at
        if lead.followup_d7_sent_at and rt >= lead.followup_d7_sent_at:
            d7_conv += 1
        elif lead.followup_d4_sent_at and rt >= lead.followup_d4_sent_at:
            d4_conv += 1
        elif lead.followup_d2_sent_at and rt >= lead.followup_d2_sent_at:
            d2_conv += 1
        else:
            direct_conv += 1

    followup_conversions = [
        {"label": "Sans relance", "count": direct_conv},
        {"label": "D+2",         "count": d2_conv},
        {"label": "D+4",         "count": d4_conv},
        {"label": "D+7",         "count": d7_conv},
    ]

    # ── Follow-up send counts ──
    followup_sent = {
        "d2": sum(1 for l in leads if l.followup_d2_sent_at),
        "d4": sum(1 for l in leads if l.followup_d4_sent_at),
        "d7": sum(1 for l in leads if l.followup_d7_sent_at),
    }

    # ── Revenue projection ──
    offer_price   = coach.offer_price or 0
    projected_mrr = closed * offer_price

    # ── Pipeline revenue forecast (weighted by score + conversion probability) ──
    forecast = _pipeline_forecast(leads, offer_price)

    # ── Timing intelligence — leads ready to contact now ──
    windows = _current_contact_windows()
    timing_ready: list[dict] = []
    for lead in leads:
        if lead.stage not in ("new", "contacted"):
            continue
        psycho_raw = getattr(lead, "psychographic_profile", None)
        if not psycho_raw:
            continue
        try:
            psycho = json.loads(psycho_raw)
        except Exception:
            continue
        bct = psycho.get("best_contact_time", "anytime")
        if bct in windows:
            timing_ready.append({"lead_id": lead.id, "name": lead.name or f"@{lead.handle}",
                                  "handle": lead.handle, "best_contact_time": bct,
                                  "score": lead.qualification_score})
    timing_ready.sort(key=lambda x: x["score"], reverse=True)

    # ── Pain escalation alerts ──
    escalation_alerts = [
        {"lead_id": l.id, "name": l.name or f"@{l.handle}", "handle": l.handle,
         "score": l.qualification_score, "score_delta": getattr(l, "score_delta", 0)}
        for l in leads
        if getattr(l, "escalation_alert", False)
    ]

    return {
        "leads_this_week":  leads_this_week,
        "leads_this_month": leads_this_month,
        "total_leads":      len(leads),
        "by_stage":         dict(by_stage),
        "reply_rate":       round(reply_rate, 4),
        "booking_rate":     round(booking_rate, 4),
        "top_hashtags":     [{"tag": t, "leads": round(c, 1)} for t, c in top_hashtags],
        "followup_conversions": followup_conversions,
        "followup_sent":    followup_sent,
        "closed_leads":     closed,
        "offer_price":      offer_price,
        "projected_mrr":    projected_mrr,
        "pipeline_forecast": forecast,
        "timing_ready":     timing_ready[:10],
        "escalation_alerts": escalation_alerts,
        "onboarding": {
            "account_created": True,
            "niche_set":       bool(coach.niche and coach.offer_description),
            "first_lead":      len(leads) > 0,
            "first_dm":        any(l.messaged_at for l in leads),
            "first_booking":   booked > 0 or closed > 0,
        },
    }
