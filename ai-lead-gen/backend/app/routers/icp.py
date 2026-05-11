"""
ICP Router — Ideal Client Profile management.
POST /api/icp/generate      → Claude generates ICP from coach data + leads
GET  /api/icp               → current ICP
PATCH /api/icp              → manual update
GET  /api/icp/questions     → onboarding interview questions
POST /api/icp/learn         → trigger ICP learning from recent conversions
"""
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_coach
from ..database import get_db
from .. import models
from ..agents import icp_agent

router = APIRouter(prefix="/api/icp", tags=["icp"])


class ICPGenerateRequest(BaseModel):
    answers: dict | None = None


class ICPUpdateRequest(BaseModel):
    data: dict


@router.get("/questions")
def get_questions():
    return {"questions": icp_agent.get_onboarding_questions()}


@router.get("")
def get_icp(
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    icp = db.query(models.CoachICP).filter(models.CoachICP.coach_id == coach.id).first()
    if not icp:
        return {"icp": None, "generated_at": None, "version": 0}
    return {
        "icp": json.loads(icp.icp_data or "{}"),
        "generated_at": icp.generated_at.isoformat() if icp.generated_at else None,
        "version": icp.version,
    }


@router.post("/generate")
def generate_icp(
    req: ICPGenerateRequest,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    if not coach.niche or not coach.offer_description:
        raise HTTPException(400, "Complete onboarding before generating ICP")

    # Gather top leads for context
    leads = (
        db.query(models.Lead)
        .filter(models.Lead.coach_id == coach.id)
        .order_by(models.Lead.qualification_score.desc())
        .limit(20)
        .all()
    )
    sample_leads = [
        {
            "handle": l.handle, "platform": l.platform,
            "qualification_score": l.qualification_score,
            "pain_points": l.pain_points or "[]",
        }
        for l in leads
    ]

    # Gather leads who replied (ground truth)
    replied_leads = [l for l in leads if l.reply_received]
    reply_data = [
        {
            "name": l.name or l.handle,
            "platform": l.platform,
            "angle": l.recommended_angle or "",
        }
        for l in replied_leads
    ]

    result = icp_agent.generate_icp(
        coach_name=coach.name,
        coach_niche=coach.niche,
        coach_offer=coach.offer_description,
        target_audience=coach.target_audience or "",
        coach_answers=req.answers,
        sample_leads=sample_leads if sample_leads else None,
        reply_data=reply_data if reply_data else None,
    )

    # Save/update ICP
    icp = db.query(models.CoachICP).filter(models.CoachICP.coach_id == coach.id).first()
    if icp:
        icp.icp_data = json.dumps(result, ensure_ascii=False)
        icp.generated_at = datetime.utcnow()
        icp.version += 1
    else:
        icp = models.CoachICP(
            coach_id=coach.id,
            icp_data=json.dumps(result, ensure_ascii=False),
            generated_at=datetime.utcnow(),
            version=1,
        )
        db.add(icp)
    db.commit()

    return {"ok": True, "icp": result, "version": icp.version}


@router.patch("")
def update_icp(
    req: ICPUpdateRequest,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    icp = db.query(models.CoachICP).filter(models.CoachICP.coach_id == coach.id).first()
    if not icp:
        raise HTTPException(404, "No ICP found — generate one first")
    icp.icp_data = json.dumps(req.data, ensure_ascii=False)
    icp.generated_at = datetime.utcnow()
    db.commit()
    return {"ok": True}


@router.post("/learn")
def trigger_icp_learning(
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    """
    Trigger ICP self-learning from recent conversion data.
    Analyzes what angles/pain points actually got replies and updates ICP accordingly.
    """
    icp = db.query(models.CoachICP).filter(models.CoachICP.coach_id == coach.id).first()
    if not icp:
        raise HTTPException(404, "No ICP found — generate one first")

    # Leads who replied — what worked
    replied = db.query(models.Lead).filter(
        models.Lead.coach_id == coach.id,
        models.Lead.reply_received.isnot(None),
    ).limit(30).all()

    # Leads who were contacted but never replied
    no_reply = db.query(models.Lead).filter(
        models.Lead.coach_id == coach.id,
        models.Lead.stage == "contacted",
        models.Lead.reply_received.is_(None),
    ).limit(30).all()

    successful_angles = [l.recommended_angle for l in replied if l.recommended_angle]
    successful_pains = list({
        p for l in replied
        for p in (json.loads(l.pain_points or "[]") if l.pain_points else [])
    })
    failed_angles = [l.recommended_angle for l in no_reply if l.recommended_angle]

    current_icp = json.loads(icp.icp_data or "{}")
    updated = icp_agent.update_icp_from_conversions(
        current_icp=current_icp,
        successful_angles=successful_angles[:10],
        successful_pain_points=successful_pains[:10],
        failed_angles=failed_angles[:10],
        coach_niche=coach.niche or "",
    )

    icp.icp_data = json.dumps(updated, ensure_ascii=False)
    icp.generated_at = datetime.utcnow()
    icp.version += 1
    db.commit()

    return {
        "ok": True,
        "icp": updated,
        "version": icp.version,
        "learned_from": {
            "successful_replies": len(replied),
            "failed_contacts": len(no_reply),
        },
    }
