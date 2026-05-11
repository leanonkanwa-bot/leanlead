import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_coach
from ..database import get_db
from .. import models

router = APIRouter(prefix="/api/leads", tags=["leads"])

STAGES = ["new", "contacted", "replied", "booked", "closed"]


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
    warming_status: str | None = None
    dm_variant_sent: str | None = None


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
        "messaged_at": lead.messaged_at.isoformat() if lead.messaged_at else None,
        "followup_d2_message": lead.followup_d2_message,
        "followup_d2_sent_at": lead.followup_d2_sent_at.isoformat() if lead.followup_d2_sent_at else None,
        "followup_d4_message": lead.followup_d4_message,
        "followup_d4_sent_at": lead.followup_d4_sent_at.isoformat() if lead.followup_d4_sent_at else None,
        "followup_d7_message": lead.followup_d7_message,
        "followup_d7_sent_at": lead.followup_d7_sent_at.isoformat() if lead.followup_d7_sent_at else None,
        "reply_received": lead.reply_received,
        "suggested_reply": lead.suggested_reply,
        "notes": lead.notes,
        "airtable_record_id": lead.airtable_record_id,
        # Intelligence fields v3
        "language": getattr(lead, "language", None),
        "psychographic_profile": _parse_json(getattr(lead, "psychographic_profile", None)),
        "response_probability": getattr(lead, "response_probability", None),
        "dm_variant_b": getattr(lead, "dm_variant_b", None),
        "dm_variant_sent": getattr(lead, "dm_variant_sent", None),
        "warming_status": getattr(lead, "warming_status", "none") or "none",
        "warming_comment": getattr(lead, "warming_comment", None),
        "source_tag": getattr(lead, "source_tag", None),
        # Intelligence fields v4
        "predicted_objection": getattr(lead, "predicted_objection", None),
        "score_delta": getattr(lead, "score_delta", None),
        "escalation_alert": bool(getattr(lead, "escalation_alert", False)),
        # Intelligence fields v5
        "aspiration_gap_score": getattr(lead, "aspiration_gap_score", None),
        "created_at": lead.created_at.isoformat() if lead.created_at else None,
        "updated_at": lead.updated_at.isoformat() if lead.updated_at else None,
    }


def _parse_json(val: str | None) -> dict | list | None:
    if not val:
        return None
    try:
        return json.loads(val)
    except Exception:
        return None


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
        if req.stage == "contacted" and not lead.messaged_at:
            lead.messaged_at = datetime.utcnow()
    if req.notes is not None:
        lead.notes = req.notes
    if req.reply_received is not None:
        lead.reply_received = req.reply_received
    if req.outreach_message is not None:
        lead.outreach_message = req.outreach_message
    if req.warming_status is not None:
        lead.warming_status = req.warming_status
    if req.dm_variant_sent is not None:
        lead.dm_variant_sent = req.dm_variant_sent
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
