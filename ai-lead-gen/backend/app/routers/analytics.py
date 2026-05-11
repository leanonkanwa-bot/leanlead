"""
Analytics router
GET /api/analytics                  → aggregated metrics for the coach's dashboard
GET /api/analytics/roi              → ROI report (cost per lead, revenue attribution, LTV)
GET /api/analytics/attribution      → multi-touch attribution breakdown
GET /api/analytics/velocity         → pipeline velocity optimization
GET /api/analytics/competitive      → competitive intelligence report
POST /api/analytics/competitive/scan → trigger fresh competitor scan
"""
import json
from collections import Counter
from datetime import datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends
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

    # ── Source attribution ──
    by_source = Counter(getattr(l, "source_tag", "direct") or "direct" for l in leads)
    converting_sources = Counter(
        getattr(l, "source_tag", "direct") or "direct"
        for l in leads if l.stage in ("replied", "booked", "closed")
    )

    # ── Churn alerts ──
    churn_alerts = [
        {"lead_id": l.id, "name": l.name or f"@{l.handle}", "handle": l.handle,
         "days_silent": (now - l.messaged_at).days if l.messaged_at else 0,
         "churn_risk": getattr(l, "churn_risk", 0) or 0,
         "has_reengagement": bool(getattr(l, "reengagement_message", None))}
        for l in leads
        if l.stage == "contacted" and not l.reply_received
        and (getattr(l, "churn_risk", 0) or 0) >= 0.7
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
        "churn_alerts":     churn_alerts[:10],
        "by_source":        dict(by_source),
        "converting_sources": dict(converting_sources),
        "onboarding": {
            "account_created": True,
            "niche_set":       bool(coach.niche and coach.offer_description),
            "first_lead":      len(leads) > 0,
            "first_dm":        any(l.messaged_at for l in leads),
            "first_booking":   booked > 0 or closed > 0,
        },
    }


@router.get("/roi")
def get_roi_report(
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    """
    Feature 10: ROI Reporting — live metrics vs agency benchmarks.
    Cost per lead, revenue attribution, LTV prediction, market share estimate.
    """
    leads = db.query(models.Lead).filter(models.Lead.coach_id == coach.id).all()
    offer_price = coach.offer_price or 0

    total_leads = len(leads)
    closed = sum(1 for l in leads if l.stage == "closed")
    booked = sum(1 for l in leads if l.stage == "booked")
    replied = sum(1 for l in leads if l.stage == "replied")

    # Cost per lead: LeanLead is €0 vs agency €50-200
    agency_cost_low = total_leads * 50
    agency_cost_high = total_leads * 200

    # Revenue attribution by source
    revenue_by_source: dict[str, float] = {}
    for lead in leads:
        if lead.stage in ("booked", "closed"):
            source = getattr(lead, "source_tag", "direct") or "direct"
            revenue_by_source[source] = revenue_by_source.get(source, 0) + offer_price

    # LTV prediction: avg score * conversion probability * price
    high_potential = [l for l in leads if l.stage in ("new", "contacted", "replied")
                      and (l.qualification_score or 0) >= 70]
    predicted_ltv = len(high_potential) * (offer_price * 0.25)  # 25% close rate for high-score

    # Market share estimate (rough: based on lead volume in niche)
    # Can't truly measure this without market data — show relative growth
    now = datetime.utcnow()
    last_30 = sum(1 for l in leads if l.created_at and l.created_at >= now - timedelta(days=30))
    prev_30 = sum(1 for l in leads if l.created_at
                  and now - timedelta(days=60) <= l.created_at < now - timedelta(days=30))
    growth_rate = ((last_30 - prev_30) / max(prev_30, 1)) * 100

    return {
        "total_leads": total_leads,
        "cost_per_lead_leanlead": 0,
        "cost_per_lead_agency_low": agency_cost_low,
        "cost_per_lead_agency_high": agency_cost_high,
        "savings_vs_agency": agency_cost_high,  # what they'd pay an agency
        "revenue_closed": closed * offer_price,
        "revenue_booked": booked * offer_price,
        "revenue_by_source": revenue_by_source,
        "predicted_ltv_pipeline": round(predicted_ltv),
        "high_potential_leads": len(high_potential),
        "leads_last_30_days": last_30,
        "leads_prev_30_days": prev_30,
        "pipeline_growth_rate": round(growth_rate, 1),
        "benchmark_agency_reply_rate": 0.08,  # agencies avg 8%
        "your_reply_rate": (replied + booked + closed) / max(total_leads, 1),
    }


@router.get("/attribution")
def get_attribution(
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    """
    Feature 2: Multi-Touch Attribution.
    Shows full conversion path: platform → angle → followup day → pain point.
    """
    leads = db.query(models.Lead).filter(models.Lead.coach_id == coach.id).all()
    converted = [l for l in leads if l.stage in ("replied", "booked", "closed")]

    # Platform performance
    platform_stats: dict[str, dict] = {}
    for l in leads:
        p = l.platform or "unknown"
        if p not in platform_stats:
            platform_stats[p] = {"total": 0, "converted": 0, "avg_score": 0}
        platform_stats[p]["total"] += 1
        if l.stage in ("replied", "booked", "closed"):
            platform_stats[p]["converted"] += 1
        platform_stats[p]["avg_score"] += (l.qualification_score or 0)
    for p in platform_stats:
        n = platform_stats[p]["total"]
        platform_stats[p]["avg_score"] = round(platform_stats[p]["avg_score"] / max(n, 1), 1)
        platform_stats[p]["conversion_rate"] = round(
            platform_stats[p]["converted"] / max(n, 1), 3
        )

    # Follow-up day that triggered reply
    followup_wins = {"direct": 0, "d2": 0, "d4": 0, "d7": 0}
    for l in converted:
        if not l.reply_received_at:
            continue
        rt = l.reply_received_at
        if l.followup_d7_sent_at and rt >= l.followup_d7_sent_at:
            followup_wins["d7"] += 1
        elif l.followup_d4_sent_at and rt >= l.followup_d4_sent_at:
            followup_wins["d4"] += 1
        elif l.followup_d2_sent_at and rt >= l.followup_d2_sent_at:
            followup_wins["d2"] += 1
        else:
            followup_wins["direct"] += 1

    # Top converting angles
    angle_counts: dict[str, int] = {}
    for l in converted:
        angle = l.recommended_angle or "unknown"
        angle_counts[angle] = angle_counts.get(angle, 0) + 1
    top_angles = sorted(angle_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    # Top converting pain points
    pain_counts: dict[str, int] = {}
    for l in converted:
        for pain in json.loads(l.pain_points or "[]"):
            pain_counts[pain] = pain_counts.get(pain, 0) + 1
    top_pains = sorted(pain_counts.items(), key=lambda x: x[1], reverse=True)[:8]

    # Source conversion funnel
    source_funnel: dict[str, dict] = {}
    for l in leads:
        src = getattr(l, "source_tag", "direct") or "direct"
        if src not in source_funnel:
            source_funnel[src] = {"leads": 0, "contacted": 0, "replied": 0, "booked": 0, "closed": 0}
        source_funnel[src]["leads"] += 1
        if l.stage in ("contacted", "replied", "booked", "closed"):
            source_funnel[src]["contacted"] += 1
        if l.stage in ("replied", "booked", "closed"):
            source_funnel[src]["replied"] += 1
        if l.stage in ("booked", "closed"):
            source_funnel[src]["booked"] += 1
        if l.stage == "closed":
            source_funnel[src]["closed"] += 1

    return {
        "platform_performance": platform_stats,
        "followup_wins": followup_wins,
        "top_converting_angles": [{"angle": a, "conversions": c} for a, c in top_angles],
        "top_converting_pains": [{"pain": p, "conversions": c} for p, c in top_pains],
        "source_funnel": source_funnel,
        "total_converted": len(converted),
    }


@router.get("/velocity")
def get_pipeline_velocity(
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    """
    Feature 7: Pipeline Velocity Optimization.
    Shows stuck leads, days in stage, predicted close dates, where to focus today.
    """
    leads = db.query(models.Lead).filter(models.Lead.coach_id == coach.id).all()
    now = datetime.utcnow()

    stage_velocity: dict[str, dict] = {}
    stuck_leads = []
    focus_today = []

    for l in leads:
        if l.stage == "closed":
            continue

        # Days in current stage
        updated = l.updated_at or l.created_at or now
        days_in_stage = (now - updated).days

        # Stage-specific stuck thresholds
        thresholds = {"new": 3, "contacted": 7, "replied": 5, "booked": 14}
        threshold = thresholds.get(l.stage, 7)
        is_stuck = days_in_stage > threshold

        if is_stuck:
            stuck_leads.append({
                "lead_id": l.id,
                "name": l.name or f"@{l.handle}",
                "handle": l.handle,
                "platform": l.platform,
                "stage": l.stage,
                "days_in_stage": days_in_stage,
                "score": l.qualification_score,
                "churn_risk": getattr(l, "churn_risk", 0) or 0,
                "has_reengagement": bool(getattr(l, "reengagement_message", None)),
            })

        # Pipeline velocity per stage
        if l.stage not in stage_velocity:
            stage_velocity[l.stage] = {"count": 0, "avg_days": 0, "stuck_count": 0}
        stage_velocity[l.stage]["count"] += 1
        stage_velocity[l.stage]["avg_days"] += days_in_stage
        if is_stuck:
            stage_velocity[l.stage]["stuck_count"] += 1

        # Focus today: high score, not stuck, within timing window
        if (l.qualification_score or 0) >= 70 and not is_stuck and l.stage in ("new", "replied"):
            focus_today.append({
                "lead_id": l.id,
                "name": l.name or f"@{l.handle}",
                "handle": l.handle,
                "stage": l.stage,
                "score": l.qualification_score,
                "action": "Envoyer DM" if l.stage == "new" else "Proposer un appel",
            })

    # Normalize averages
    for stage in stage_velocity:
        n = stage_velocity[stage]["count"]
        stage_velocity[stage]["avg_days"] = round(stage_velocity[stage]["avg_days"] / max(n, 1), 1)

    focus_today.sort(key=lambda x: x["score"], reverse=True)
    stuck_leads.sort(key=lambda x: x["score"], reverse=True)

    return {
        "stage_velocity": stage_velocity,
        "stuck_leads": stuck_leads[:15],
        "focus_today": focus_today[:10],
        "total_active": sum(1 for l in leads if l.stage not in ("closed",)),
        "avg_days_to_reply": round(
            sum(
                (l.reply_received_at - l.messaged_at).days
                for l in leads
                if l.reply_received_at and l.messaged_at
            ) / max(sum(1 for l in leads if l.reply_received_at and l.messaged_at), 1),
            1,
        ),
    }


@router.get("/competitive")
def get_competitive_intel(
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    """
    Feature 9: Competitive Intelligence.
    Returns latest scan data + positioning report for all competitor accounts.
    """
    scans = (
        db.query(models.CompetitorIntelligence)
        .filter(models.CompetitorIntelligence.coach_id == coach.id)
        .order_by(models.CompetitorIntelligence.scanned_at.desc())
        .all()
    )
    report_row = scans[0] if scans else None
    return {
        "competitors": [
            {
                "handle": s.handle,
                "platform": s.platform,
                "scan_data": json.loads(s.scan_data or "{}"),
                "scanned_at": s.scanned_at.isoformat() if s.scanned_at else None,
            }
            for s in scans
        ],
        "report": json.loads(report_row.report_data or "{}") if report_row and report_row.report_data else None,
        "last_scanned": scans[0].scanned_at.isoformat() if scans else None,
    }


@router.post("/competitive/scan")
def trigger_competitive_scan(
    background_tasks: BackgroundTasks,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    """Trigger a background competitive intelligence scan of all competitor accounts."""
    competitor_accounts = json.loads(getattr(coach, "competitor_accounts", None) or "[]")
    if not competitor_accounts:
        return {"ok": False, "message": "No competitor accounts configured"}

    def _do_scan():
        from ..database import SessionLocal
        from ..agents import competitive_agent
        _db = SessionLocal()
        try:
            coach_row = _db.query(models.Coach).filter(models.Coach.id == coach.id).first()
            if not coach_row:
                return
            scans = []
            for comp in competitor_accounts[:5]:
                try:
                    scan = competitive_agent.scan_competitor(
                        handle=comp.get("handle", ""),
                        platform=comp.get("platform", "instagram"),
                        niche=coach_row.niche or "",
                    )
                    scans.append(scan)
                    # Upsert scan record
                    existing = _db.query(models.CompetitorIntelligence).filter(
                        models.CompetitorIntelligence.coach_id == coach.id,
                        models.CompetitorIntelligence.handle == comp.get("handle", ""),
                    ).first()
                    if existing:
                        existing.scan_data = json.dumps(scan, ensure_ascii=False)
                        existing.scanned_at = datetime.utcnow()
                    else:
                        _db.add(models.CompetitorIntelligence(
                            coach_id=coach.id,
                            handle=comp.get("handle", ""),
                            platform=comp.get("platform", "instagram"),
                            scan_data=json.dumps(scan, ensure_ascii=False),
                        ))
                except Exception as e:
                    pass
            # Generate report
            if scans:
                report = competitive_agent.generate_competitive_report(
                    competitor_scans=scans,
                    coach_niche=coach_row.niche or "",
                    coach_offer=coach_row.offer_description or "",
                    coach_name=coach_row.name,
                )
                # Save report to first scan row
                first = _db.query(models.CompetitorIntelligence).filter(
                    models.CompetitorIntelligence.coach_id == coach.id
                ).first()
                if first:
                    first.report_data = json.dumps(report, ensure_ascii=False)
            _db.commit()
        except Exception:
            pass
        finally:
            _db.close()

    background_tasks.add_task(_do_scan)
    return {"ok": True, "message": f"Scanning {len(competitor_accounts)} competitor(s) in background"}
