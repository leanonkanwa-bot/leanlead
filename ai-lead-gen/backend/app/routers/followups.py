"""
Follow-up router
GET  /api/followups/due              – leads due for D+2 / D+4 / D+7 follow-up
POST /api/followups/{lead_id}/generate – generate follow-up message for given day
POST /api/followups/{lead_id}/mark-sent – mark follow-up as sent
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_coach
from ..database import get_db
from .. import models
from ..agents import followup_agent

router = APIRouter(prefix="/api/followups", tags=["followups"])

FOLLOWUP_DAYS = [2, 4, 7]


def _due_day(lead: models.Lead) -> int | None:
    """Return which follow-up day is due (2, 4, or 7), or None."""
    if not lead.messaged_at or lead.stage != "contacted":
        return None
    now = datetime.utcnow()
    delta = (now - lead.messaged_at).days

    if delta >= 7 and not lead.followup_d7_sent_at:
        return 7
    if delta >= 4 and not lead.followup_d4_sent_at:
        return 4
    if delta >= 2 and not lead.followup_d2_sent_at:
        return 2
    return None


@router.get("/due")
def get_due(
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    """Return all leads that have a follow-up due."""
    leads = (
        db.query(models.Lead)
        .filter(
            models.Lead.coach_id == coach.id,
            models.Lead.stage == "contacted",
            models.Lead.messaged_at.isnot(None),
        )
        .all()
    )
    due = []
    for lead in leads:
        day = _due_day(lead)
        if day is not None:
            import json
            pain_points: list = []
            try:
                pain_points = json.loads(lead.pain_points or "[]")
            except Exception:
                pass
            due.append({
                "lead_id": lead.id,
                "name": lead.name,
                "handle": lead.handle,
                "platform": lead.platform,
                "bio": lead.bio,
                "messaged_at": lead.messaged_at.isoformat(),
                "outreach_message": lead.outreach_message,
                "due_day": day,
                "followup_d2_sent_at": lead.followup_d2_sent_at.isoformat() if lead.followup_d2_sent_at else None,
                "followup_d4_sent_at": lead.followup_d4_sent_at.isoformat() if lead.followup_d4_sent_at else None,
                "followup_d7_sent_at": lead.followup_d7_sent_at.isoformat() if lead.followup_d7_sent_at else None,
                "followup_d2_message": lead.followup_d2_message,
                "followup_d4_message": lead.followup_d4_message,
                "followup_d7_message": lead.followup_d7_message,
            })
    return due


class GenerateRequest(BaseModel):
    day: int   # 2, 4, or 7


@router.post("/{lead_id}/generate")
def generate(
    lead_id: int,
    req: GenerateRequest,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    if req.day not in FOLLOWUP_DAYS:
        raise HTTPException(status_code=400, detail=f"day must be one of {FOLLOWUP_DAYS}")
    lead = db.query(models.Lead).filter(
        models.Lead.id == lead_id, models.Lead.coach_id == coach.id
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if not lead.outreach_message:
        raise HTTPException(status_code=400, detail="No original DM found for this lead")

    message = followup_agent.generate_followup(
        lead_data={"name": lead.name, "bio": lead.bio or "", "platform": lead.platform},
        original_dm=lead.outreach_message,
        coach_name=coach.name,
        coach_offer=coach.offer_description or "",
        day=req.day,
    )

    if req.day == 2:
        lead.followup_d2_message = message
    elif req.day == 4:
        lead.followup_d4_message = message
    else:
        lead.followup_d7_message = message
    db.commit()

    return {"ok": True, "message": message, "day": req.day}


class MarkSentRequest(BaseModel):
    day: int


@router.post("/{lead_id}/mark-sent")
def mark_sent(
    lead_id: int,
    req: MarkSentRequest,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    if req.day not in FOLLOWUP_DAYS:
        raise HTTPException(status_code=400, detail=f"day must be one of {FOLLOWUP_DAYS}")
    lead = db.query(models.Lead).filter(
        models.Lead.id == lead_id, models.Lead.coach_id == coach.id
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    now = datetime.utcnow()
    if req.day == 2:
        lead.followup_d2_sent_at = now
    elif req.day == 4:
        lead.followup_d4_sent_at = now
    else:
        lead.followup_d7_sent_at = now
    db.commit()

    return {"ok": True, "day": req.day}
