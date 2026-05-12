"""
Prospecting router
POST /api/prospecting/run         – start a prospecting job (background task)
GET  /api/prospecting/jobs        – list coach's prospecting jobs
GET  /api/prospecting/suggest-hashtags – AI-suggest search terms from niche
"""
import json
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_coach, decrypt_handle
from ..database import get_db
from .. import models
from ..agents import prospector_agent, qualifier_agent, writer_agent
from .leads import _serialize

router = APIRouter(prefix="/api/prospecting", tags=["prospecting"])

PLAN_LIMITS: dict[str, int | None] = {"free": 20, "growth": 200, "agency": None}


class ProspectRequest(BaseModel):
    platform: str = "instagram"     # instagram | tiktok | linkedin | twitter | reddit
    hashtags: list[str]             # hashtags (IG/TT), keywords (LI/TW), subreddits (Reddit)
    max_results: int = 20
    auto_qualify: bool = True


def _run_job(job_id: int, coach_id: int, req: ProspectRequest) -> None:
    """Background task — searches profiles, qualifies leads, stores in DB."""
    from ..database import SessionLocal
    db = SessionLocal()
    try:
        job = db.query(models.ProspectingJob).filter(models.ProspectingJob.id == job_id).first()
        coach = db.query(models.Coach).filter(models.Coach.id == coach_id).first()
        if not job or not coach:
            return

        job.status = "running"
        db.commit()

        # Augment hashtags with coach's own handle so the prospector can
        # find people who engage with similar content / competitor audiences.
        search_terms = list(req.hashtags)
        ig_handle = decrypt_handle(getattr(coach, "instagram_handle", None))
        tt_handle = decrypt_handle(getattr(coach, "tiktok_handle", None))
        if req.platform == "instagram" and ig_handle:
            search_terms.append(ig_handle)
        elif req.platform == "tiktok" and tt_handle:
            search_terms.append(tt_handle)

        raw_profiles = prospector_agent.prospect(
            platform=req.platform,
            hashtags=search_terms,
            max_results=req.max_results,
        )

        # Check plan lead limit
        coach_plan = getattr(coach, "plan", "free") or "free"
        plan_limit = PLAN_LIMITS.get(coach_plan)
        if plan_limit is not None:
            current_count = db.query(models.Lead).filter(models.Lead.coach_id == coach_id).count()
            if current_count >= plan_limit:
                job.status = "done"
                job.leads_found = 0
                job.error_message = f"Limite du plan {coach_plan} atteinte ({plan_limit} leads). Passez au plan supérieur pour continuer."
                job.finished_at = datetime.utcnow()
                db.commit()
                return

        added = 0
        for profile in raw_profiles:
            handle = (profile.get("handle") or "").strip().lower()
            if not handle:
                continue
            exists = db.query(models.Lead).filter(
                models.Lead.coach_id == coach_id,
                models.Lead.handle == handle,
            ).first()
            if exists:
                continue

            # Stop if plan limit reached mid-run
            if plan_limit is not None:
                current_total = db.query(models.Lead).filter(models.Lead.coach_id == coach_id).count()
                if current_total >= plan_limit:
                    break

            lead = models.Lead(
                coach_id=coach_id,
                name=profile.get("name", ""),
                handle=handle,
                platform=profile.get("platform", req.platform),
                profile_url=profile.get("profile_url", ""),
                bio=profile.get("bio", ""),
                followers=profile.get("followers", 0),
                posts_summary=profile.get("posts_summary", ""),
                profile_pic_url=profile.get("profile_pic_url"),
                stage="new",
            )
            db.add(lead)
            db.flush()

            if req.auto_qualify and coach.niche and coach.offer_description:
                try:
                    icp_pains = json.loads(coach.icp_pain_points) if coach.icp_pain_points else None
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
                        icp_pain_points=icp_pains,
                    )
                    lead.qualification_score = result.get("score", 0)
                    lead.qualification_reason = result.get("reason", "")
                    lead.pain_points = json.dumps(result.get("pain_points", []))
                    lead.recommended_angle = result.get("recommended_angle", "")
                except Exception:
                    pass

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
        raise HTTPException(status_code=400, detail="Provide at least one term")

    # Enforce plan lead limits
    coach_plan = getattr(coach, "plan", "free") or "free"
    plan_limit = PLAN_LIMITS.get(coach_plan)
    if plan_limit is not None:
        current_count = db.query(models.Lead).filter(models.Lead.coach_id == coach.id).count()
        if current_count >= plan_limit:
            raise HTTPException(
                status_code=429,
                detail=f"Limite du plan {coach_plan} atteinte ({plan_limit} leads). Passez au plan supérieur pour continuer.",
            )

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


class FromUrlRequest(BaseModel):
    profile_url: str
    auto_write: bool = True


@router.post("/from-url")
def prospect_from_url(
    req: FromUrlRequest,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    """Synchronously scrape a single profile URL, qualify + write message, save lead."""
    profile = prospector_agent.prospect_by_url(
        profile_url=req.profile_url,
    )

    handle = (profile.get("handle") or "").strip().lower()
    if not handle:
        raise HTTPException(status_code=400, detail="Impossible d'extraire l'identifiant depuis l'URL.")

    existing = db.query(models.Lead).filter(
        models.Lead.coach_id == coach.id,
        models.Lead.handle == handle,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Ce lead (@{handle}) est déjà dans votre pipeline.")

    lead = models.Lead(
        coach_id=coach.id,
        name=profile.get("name", handle),
        handle=handle,
        platform=profile.get("platform", "unknown"),
        profile_url=profile.get("profile_url", req.profile_url),
        bio=profile.get("bio", ""),
        followers=profile.get("followers", 0),
        posts_summary=profile.get("posts_summary", ""),
        stage="new",
    )
    db.add(lead)
    db.flush()

    if coach.niche and coach.offer_description:
        try:
            icp_pains = json.loads(coach.icp_pain_points) if coach.icp_pain_points else None
            result = qualifier_agent.qualify_lead(
                lead_data={
                    "name": lead.name, "handle": lead.handle, "platform": lead.platform,
                    "bio": lead.bio or "", "followers": lead.followers,
                    "posts_summary": lead.posts_summary or "",
                },
                coach_niche=coach.niche,
                coach_offer=coach.offer_description,
                icp_pain_points=icp_pains,
            )
            lead.qualification_score = result.get("score", 0)
            lead.qualification_reason = result.get("reason", "")
            lead.pain_points = json.dumps(result.get("pain_points", []))
            lead.recommended_angle = result.get("recommended_angle", "")
        except Exception:
            pass

        if req.auto_write:
            try:
                dm = writer_agent.write_outreach_message(
                    lead_data={
                        "name": lead.name, "handle": lead.handle, "platform": lead.platform,
                        "bio": lead.bio or "", "followers": lead.followers,
                        "posts_summary": lead.posts_summary or "",
                    },
                    coach_name=coach.name,
                    coach_niche=coach.niche,
                    coach_offer=coach.offer_description,
                    qualification={
                        "score": lead.qualification_score,
                        "reason": lead.qualification_reason or "",
                        "pain_points": json.loads(lead.pain_points or "[]"),
                        "recommended_angle": lead.recommended_angle or "",
                    },
                )
                lead.outreach_message = dm
            except Exception:
                pass

    db.commit()
    db.refresh(lead)
    return _serialize(lead)


@router.get("/suggest-hashtags")
def suggest_hashtags(
    platform: str = "instagram",
    coach: models.Coach = Depends(get_current_coach),
):
    if not coach.niche:
        raise HTTPException(status_code=400, detail="Complete onboarding first")
    icp_pains = json.loads(coach.icp_pain_points) if coach.icp_pain_points else None
    hashtags = prospector_agent.suggest_hashtags(
        niche=coach.niche,
        target_audience=coach.target_audience or "",
        icp_pain_points=icp_pains,
    )
    return {"hashtags": hashtags}
