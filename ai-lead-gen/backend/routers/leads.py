import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_coach
from ..database import get_db
from .. import models

router = APIRouter(prefix="/api/leads", tags=["leads"])

STAGES = ["new", "qualified", "messaged", "replied", "booked", "closed"]


class LeadCreate(BaseModel):
    name: str
    handle: str
    platform: str = "instagram"
    profile_url: str | None = None
    bio: str | None = None
    followers: int = 0
    posts_summary: str | None = None
    notes: str | None = None


class LeadUpdate(BaseModel):
    stage: str | None = None
    notes: str | None = None
    reply_received: str | None = None
    outreach_message: str | None = None


def _serialize(lead: models.Lead) -> dict:
    pain_points: list = []
    if lead.pain_points:
        try:
            pain_points = json.loads(lead.pain_points)
        except Exception:
            pain_points = [lead.pain_points]
    return {
        "id": lead.id,
        "coach_id": lead.coach_id,
        "name": lead.name,
        "handle": lead.handle,
        "platform": lead.platform,
        "profile_url": lead.profile_url,
        "bio": lead.bio,
        "followers": lead.followers,
        "posts_summary": lead.posts_summary,
        "qualification_score": lead.qualification_score,
        "qualification_reason": lead.qualification_reason,
        "pain_points": pain_points,
        "recommended_angle": lead.recommended_angle,
        "stage": lead.stage,
        "outreach_message": lead.outreach_message,
        "reply_received": lead.reply_received,
        "suggested_reply": lead.suggested_reply,
        "notes": lead.notes,
        "airtable_record_id": lead.airtable_record_id,
        "created_at": lead.created_at.isoformat() if lead.created_at else None,
        "updated_at": lead.updated_at.isoformat() if lead.updated_at else None,
    }


@router.get("")
def list_leads(
    stage: str | None = None,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    q = db.query(models.Lead).filter(models.Lead.coach_id == coach.id)
    if stage:
        q = q.filter(models.Lead.stage == stage)
    leads = q.order_by(models.Lead.created_at.desc()).all()
    return [_serialize(l) for l in leads]


@router.post("", status_code=201)
def create_lead(
    req: LeadCreate,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    lead = models.Lead(coach_id=coach.id, **req.model_dump())
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return _serialize(lead)


@router.get("/{lead_id}")
def get_lead(
    lead_id: int,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    lead = db.query(models.Lead).filter(
        models.Lead.id == lead_id, models.Lead.coach_id == coach.id
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return _serialize(lead)


@router.patch("/{lead_id}")
def update_lead(
    lead_id: int,
    req: LeadUpdate,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    lead = db.query(models.Lead).filter(
        models.Lead.id == lead_id, models.Lead.coach_id == coach.id
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if req.stage is not None:
        if req.stage not in STAGES:
            raise HTTPException(status_code=400, detail=f"Invalid stage. Must be one of {STAGES}")
        lead.stage = req.stage
    if req.notes is not None:
        lead.notes = req.notes
    if req.reply_received is not None:
        lead.reply_received = req.reply_received
    if req.outreach_message is not None:
        lead.outreach_message = req.outreach_message
    db.commit()
    db.refresh(lead)
    return _serialize(lead)


@router.delete("/{lead_id}", status_code=204)
def delete_lead(
    lead_id: int,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    lead = db.query(models.Lead).filter(
        models.Lead.id == lead_id, models.Lead.coach_id == coach.id
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    db.delete(lead)
    db.commit()
