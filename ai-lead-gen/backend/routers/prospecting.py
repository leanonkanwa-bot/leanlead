"""
Prospecting router
POST /api/prospecting/run         – start an Apify scraping job (background task)
GET  /api/prospecting/jobs        – list coach's prospecting jobs
GET  /api/prospecting/suggest-hashtags – AI-suggest hashtags from niche
"""
import json
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_coach
from ..database import get_db
from .. import models
from ..agents import prospector_agent, qualifier_agent

router = APIRouter(prefix="/api/prospecting", tags=["prospecting"])


class ProspectRequest(BaseModel):
    platform: str = "instagram"     # instagram | tiktok
    hashtags: list[str]
    max_results: int = 20
    auto_qualify: bool = True


def _run_job(job_id: int, coach_id: int, req: ProspectRequest) -> None:
    """Background task — runs Apify, qualifies leads, stores in DB."""
    from ..database import SessionLocal
    db = SessionLocal()
    try:
        job = db.query(models.ProspectingJob).filter(models.ProspectingJob.id == job_id).first()
        coach = db.query(models.Coach).filter(models.Coach.id == coach_id).first()
        if not job or not coach:
            return

        job.status = "running"
        db.commit()

        apify_key = coach.apify_api_key or None
        raw_profiles = prospector_agent.prospect(
            platform=req.platform,
            hashtags=req.hashtags,
            max_results=req.max_results,
            apify_api_key=apify_key,
        )

        added = 0
        for profile in raw_profiles:
            handle = (profile.get("handle") or "").strip().lower()
            if not handle:
                continue
            # Skip duplicates already in coach's pipeline
            exists = db.query(models.Lead).filter(
                models.Lead.coach_id == coach_id,
                models.Lead.handle == handle,
            ).first()
            if exists:
                continue

            lead = models.Lead(
                coach_id=coach_id,
                name=profile.get("name", ""),
                handle=handle,
                platform=profile.get("platform", req.platform),
                profile_url=profile.get("profile_url", ""),
                bio=profile.get("bio", ""),
                followers=profile.get("followers", 0),
                posts_summary=profile.get("posts_summary", ""),
                stage="new",
            )
            db.add(lead)
            db.flush()  # get lead.id

            if req.auto_qualify and coach.niche and coach.offer_description:
                try:
                    result = qualifier_agent.qualify_lead(
                        lead_data={
                            "name": lead.name,
                            "handle": lead.handle,
                            "platform": lead.platform,
                            "bio": lead.bio or "",
                            "followers": lead.followers,
                            "posts_summary": lead.posts_summary or "",
                        },
                        coach_niche=coach.niche,
                        coach_offer=coach.offer_description,
                    )
                    lead.qualification_score = result.get("score", 0)
                    lead.qualification_reason = result.get("reason", "")
                    lead.pain_points = json.dumps(result.get("pain_points", []))
                    lead.recommended_angle = result.get("recommended_angle", "")
                    if lead.qualification_score >= 6:
                        lead.stage = "new"  # stays new, user decides to contact
                except Exception:
                    pass  # qualification failure shouldn't abort the job

            added += 1

        job.status = "done"
        job.leads_found = added
        job.finished_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        db = SessionLocal()
        job = db.query(models.ProspectingJob).filter(models.ProspectingJob.id == job_id).first()
        if job:
            job.status = "error"
            job.error_message = str(e)
            job.finished_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()


@router.post("/run", status_code=202)
def run_prospecting(
    req: ProspectRequest,
    background_tasks: BackgroundTasks,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    if req.max_results > 100:
        raise HTTPException(status_code=400, detail="max_results cannot exceed 100")
    if not req.hashtags:
        raise HTTPException(status_code=400, detail="Provide at least one hashtag")

    job = models.ProspectingJob(
        coach_id=coach.id,
        platform=req.platform,
        hashtags=json.dumps(req.hashtags),
        max_results=req.max_results,
        status="pending",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(_run_job, job.id, coach.id, req)
    return {"job_id": job.id, "status": "pending"}


@router.get("/jobs")
def list_jobs(
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    jobs = (
        db.query(models.ProspectingJob)
        .filter(models.ProspectingJob.coach_id == coach.id)
        .order_by(models.ProspectingJob.started_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": j.id,
            "platform": j.platform,
            "hashtags": json.loads(j.hashtags or "[]"),
            "max_results": j.max_results,
            "status": j.status,
            "leads_found": j.leads_found,
            "error_message": j.error_message,
            "started_at": j.started_at.isoformat() if j.started_at else None,
            "finished_at": j.finished_at.isoformat() if j.finished_at else None,
        }
        for j in jobs
    ]


@router.get("/suggest-hashtags")
def suggest_hashtags(
    coach: models.Coach = Depends(get_current_coach),
):
    if not coach.niche:
        raise HTTPException(status_code=400, detail="Complete onboarding first")
    hashtags = prospector_agent.suggest_hashtags(
        niche=coach.niche,
        target_audience=coach.target_audience or "",
    )
    return {"hashtags": hashtags}
