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
        "onboarding": {
            "account_created": True,
            "niche_set":       bool(coach.niche and coach.offer_description),
            "first_lead":      len(leads) > 0,
            "first_dm":        any(l.messaged_at for l in leads),
            "first_booking":   booked > 0 or closed > 0,
        },
    }
