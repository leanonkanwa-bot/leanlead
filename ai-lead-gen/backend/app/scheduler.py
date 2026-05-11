"""APScheduler-based scheduler for autonomous lead generation jobs."""
import logging
import threading
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    _APSCHEDULER_AVAILABLE = True
except ImportError:
    _APSCHEDULER_AVAILABLE = False
    logger.warning("APScheduler not installed — autonomous agent disabled")

_scheduler = None
_scheduler_lock = threading.Lock()


def get_scheduler():
    global _scheduler
    if not _APSCHEDULER_AVAILABLE:
        return None
    with _scheduler_lock:
        if _scheduler is None:
            _scheduler = BackgroundScheduler(daemon=True, timezone="UTC")
    return _scheduler


def start_scheduler():
    s = get_scheduler()
    if s is None:
        return
    if not s.running:
        s.start()
        logger.info("APScheduler started")


def stop_scheduler():
    s = get_scheduler()
    if s is not None and s.running:
        s.shutdown(wait=False)


def schedule_coach(coach_id: int, frequency_hours: int = 6, run_immediately: bool = False):
    """Add or replace a coach's autonomous recurring job + daily escalation rescan."""
    s = get_scheduler()
    if s is None:
        return
    job_id = f"autonomous_{coach_id}"
    if s.get_job(job_id):
        s.remove_job(job_id)
    next_run = datetime.utcnow() + (timedelta(seconds=5) if run_immediately else timedelta(hours=frequency_hours))
    s.add_job(
        _run_for_coach,
        trigger=IntervalTrigger(hours=frequency_hours, timezone="UTC"),
        id=job_id,
        args=[coach_id],
        replace_existing=True,
        next_run_time=next_run,
    )
    # Daily pain escalation rescan (staggered 3h after autonomous job)
    rescan_job_id = f"escalation_{coach_id}"
    if not s.get_job(rescan_job_id):
        s.add_job(
            _rescan_for_coach,
            trigger=IntervalTrigger(hours=24, timezone="UTC"),
            id=rescan_job_id,
            args=[coach_id],
            replace_existing=True,
            next_run_time=datetime.utcnow() + timedelta(hours=3),
        )
    # Daily churn prevention scan (staggered 6h after autonomous job)
    churn_job_id = f"churn_{coach_id}"
    if not s.get_job(churn_job_id):
        s.add_job(
            _churn_scan_for_coach,
            trigger=IntervalTrigger(hours=24, timezone="UTC"),
            id=churn_job_id,
            args=[coach_id],
            replace_existing=True,
            next_run_time=datetime.utcnow() + timedelta(hours=6),
        )
    logger.info("Scheduled autonomous job for coach %d every %d hours", coach_id, frequency_hours)


def unschedule_coach(coach_id: int):
    s = get_scheduler()
    if s is None:
        return
    for job_id in [f"autonomous_{coach_id}", f"escalation_{coach_id}", f"churn_{coach_id}"]:
        if s.get_job(job_id):
            s.remove_job(job_id)
    logger.info("Removed all jobs for coach %d", coach_id)


def get_next_run(coach_id: int) -> datetime | None:
    s = get_scheduler()
    if s is None:
        return None
    job = s.get_job(f"autonomous_{coach_id}")
    return job.next_run_time if job else None


def trigger_now(coach_id: int):
    """Trigger an immediate run in a background thread (non-blocking)."""
    t = threading.Thread(target=_run_for_coach, args=[coach_id], daemon=True)
    t.start()


def _run_for_coach(coach_id: int):
    """Called by APScheduler or trigger_now — runs a full autonomous cycle."""
    import json
    from .database import SessionLocal
    from . import models
    from .agents import autonomous_agent, prospector_agent

    db = SessionLocal()
    run = None
    try:
        coach = db.query(models.Coach).filter(models.Coach.id == coach_id).first()
        if not coach or not getattr(coach, "agent_enabled", False) or not coach.onboarded:
            return
        if not coach.niche or not coach.offer_description:
            return

        platforms = json.loads(getattr(coach, "agent_platforms", None) or
                               '["instagram","tiktok","linkedin","twitter","reddit"]')
        icp_pain_points = json.loads(coach.icp_pain_points or "[]") or None
        max_per_platform = getattr(coach, "agent_max_results_per_platform", None) or 20
        dm_threshold = getattr(coach, "agent_dm_threshold", None) or 70

        run = models.AgentRun(
            coach_id=coach_id,
            status="running",
            platforms_searched=json.dumps(platforms),
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        # Generate search terms for each platform
        search_terms: dict[str, list[str]] = {}
        for platform in platforms:
            try:
                terms = prospector_agent.suggest_hashtags(
                    niche=coach.niche,
                    target_audience=coach.target_audience or "",
                    icp_pain_points=icp_pain_points,
                    platform=platform,
                )
                search_terms[platform] = terms[:5]
            except Exception as e:
                logger.warning("suggest_hashtags failed for %s: %s", platform, e)
                search_terms[platform] = []

        existing = db.query(models.Lead.handle).filter(models.Lead.coach_id == coach_id).all()
        existing_handles = {row[0] for row in existing if row[0]}

        competitor_accounts = json.loads(getattr(coach, "competitor_accounts", None) or "[]") or None

        result = autonomous_agent.run_autonomous(
            coach_id=coach_id,
            coach_niche=coach.niche,
            coach_offer=coach.offer_description,
            coach_name=coach.name,
            icp_pain_points=icp_pain_points,
            platforms=platforms,
            search_terms_per_platform=search_terms,
            max_per_platform=max_per_platform,
            dm_threshold=dm_threshold,
            existing_handles=existing_handles,
            competitor_accounts=competitor_accounts,
        )

        for lead_data in result.get("leads", []):
            lead = models.Lead(
                coach_id=coach_id,
                name=lead_data.get("name", ""),
                handle=lead_data["handle"],
                platform=lead_data.get("platform", "unknown"),
                profile_url=lead_data.get("profile_url", ""),
                bio=lead_data.get("bio", ""),
                followers=lead_data.get("followers", 0),
                posts_summary=lead_data.get("posts_summary", ""),
                qualification_score=lead_data.get("qualification_score", 0),
                qualification_reason=lead_data.get("qualification_reason", ""),
                pain_points=lead_data.get("pain_points", "[]"),
                recommended_angle=lead_data.get("recommended_angle", ""),
                outreach_message=lead_data.get("outreach_message"),
                dm_variant_b=lead_data.get("dm_variant_b"),
                language=lead_data.get("language", "fr"),
                psychographic_profile=lead_data.get("psychographic_profile"),
                response_probability=lead_data.get("response_probability"),
                source_tag=lead_data.get("source_tag", "hashtag"),
                predicted_objection=lead_data.get("predicted_objection"),
                aspiration_gap_score=lead_data.get("aspiration_gap_score", 0),
                price_tier=lead_data.get("price_tier", "mid"),
                trust_velocity=lead_data.get("trust_velocity", "unknown"),
                voice_tone_intensity=lead_data.get("voice_tone_intensity", 0),
                stage="new",
            )
            db.add(lead)

        run.status = "done"
        run.leads_found = result["leads_found"]
        run.leads_qualified = result["leads_qualified"]
        run.dms_generated = result["dms_generated"]
        run.high_score_leads = result["high_score_leads"]
        run.finished_at = datetime.utcnow()
        coach.agent_last_run_at = datetime.utcnow()
        db.commit()

        logger.info(
            "Autonomous run done for coach %d: %d leads, %d DMs, %d high-score",
            coach_id, result["leads_found"], result["dms_generated"], result["high_score_leads"],
        )

        if result["high_score_leads"] > 0 and getattr(coach, "webhook_url", None):
            _fire_webhook(coach.webhook_url, coach_id, result)

    except Exception as e:
        logger.exception("Autonomous run failed for coach %d: %s", coach_id, e)
        if run:
            try:
                run.status = "error"
                run.error_message = str(e)[:500]
                run.finished_at = datetime.utcnow()
                db.commit()
            except Exception:
                pass
    finally:
        db.close()


def _fire_webhook(url: str, coach_id: int, result: dict):
    try:
        import httpx
        httpx.post(url, json={
            "event": "high_score_leads",
            "coach_id": coach_id,
            "leads_found": result["leads_found"],
            "high_score_leads": result["high_score_leads"],
            "dms_generated": result["dms_generated"],
        }, timeout=10)
    except Exception as e:
        logger.warning("Webhook delivery failed: %s", e)


def _rescan_for_coach(coach_id: int):
    """
    Daily pain escalation rescan — re-qualifies contacted/replied leads
    and sets escalation_alert=True when score increases by ≥10 points.
    Fires webhook if new escalations found.
    """
    import json
    from .database import SessionLocal
    from . import models
    from .agents import qualifier_agent

    db = SessionLocal()
    try:
        coach = db.query(models.Coach).filter(models.Coach.id == coach_id).first()
        if not coach or not getattr(coach, "agent_enabled", False) or not coach.onboarded:
            return
        if not coach.niche or not coach.offer_description:
            return

        rescan_stages = {"new", "contacted", "replied"}
        leads = db.query(models.Lead).filter(
            models.Lead.coach_id == coach_id,
            models.Lead.stage.in_(rescan_stages),
        ).all()

        escalated = []
        for lead in leads:
            try:
                old_score = lead.qualification_score or 0
                result = qualifier_agent.qualify_lead(
                    lead_data={
                        "name": lead.name, "handle": lead.handle, "platform": lead.platform,
                        "bio": lead.bio or "", "followers": lead.followers,
                        "posts_summary": lead.posts_summary or "",
                    },
                    coach_niche=coach.niche,
                    coach_offer=coach.offer_description,
                )
                new_score = result.get("score", 0)
                delta = new_score - old_score
                lead.qualification_score = new_score
                lead.score_delta = delta
                lead.escalation_alert = delta >= 10
                if result.get("pain_points"):
                    lead.pain_points = json.dumps(result["pain_points"])
                if result.get("predicted_objection"):
                    lead.predicted_objection = result["predicted_objection"]
                if delta >= 10:
                    escalated.append({"id": lead.id, "name": lead.name, "delta": delta})
            except Exception as e:
                logger.warning("Rescan failed for lead %d: %s", lead.id, e)
        db.commit()

        if escalated:
            logger.info("Escalation rescan for coach %d: %d leads escalated", coach_id, len(escalated))
            if getattr(coach, "webhook_url", None):
                try:
                    import httpx
                    httpx.post(coach.webhook_url, json={
                        "event": "pain_escalation",
                        "coach_id": coach_id,
                        "escalated_leads": escalated,
                    }, timeout=10)
                except Exception:
                    pass
    except Exception as e:
        logger.exception("Escalation rescan failed for coach %d: %s", coach_id, e)
    finally:
        db.close()


def _churn_scan_for_coach(coach_id: int):
    """
    Feature 6: Predictive Churn Prevention.
    Detects leads going cold in the pipeline.
    Leads contacted >5 days ago with no reply get a churn_risk score.
    Leads >10 days silent get an auto-generated re-engagement message.
    """
    import json
    from datetime import timedelta
    from .database import SessionLocal
    from . import models
    from .agents import writer_agent

    db = SessionLocal()
    try:
        coach = db.query(models.Coach).filter(models.Coach.id == coach_id).first()
        if not coach or not coach.onboarded:
            return

        now = datetime.utcnow()
        # Find all contacted leads with no reply
        leads = db.query(models.Lead).filter(
            models.Lead.coach_id == coach_id,
            models.Lead.stage == "contacted",
            models.Lead.reply_received.is_(None),
            models.Lead.messaged_at.isnot(None),
        ).all()

        reengaged = 0
        for lead in leads:
            days_silent = (now - lead.messaged_at).days
            # Progressive churn risk: 0 at day 0, 1.0 at day 14+
            churn_risk = min(1.0, days_silent / 14.0)
            lead.churn_risk = churn_risk

            # Generate re-engagement message for leads going very cold (10+ days)
            if days_silent >= 10 and not lead.reengagement_message:
                try:
                    msg = writer_agent.write_reengagement_message(
                        lead_data={
                            "name": lead.name,
                            "bio": lead.bio or "",
                            "recommended_angle": lead.recommended_angle or "",
                            "notes": lead.notes or "",
                        },
                        coach_name=coach.name,
                        coach_niche=coach.niche or "",
                        days_silent=days_silent,
                        language=getattr(lead, "language", None) or "fr",
                        coach_id=coach_id,
                    )
                    lead.reengagement_message = msg
                    reengaged += 1
                except Exception as e:
                    logger.warning("Re-engagement DM failed for lead %d: %s", lead.id, e)

        db.commit()
        if reengaged:
            logger.info("Churn scan for coach %d: %d re-engagement DMs generated", coach_id, reengaged)

    except Exception as e:
        logger.exception("Churn scan failed for coach %d: %s", coach_id, e)
    finally:
        db.close()
