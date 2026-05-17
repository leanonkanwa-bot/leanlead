"""
Follow-up router
GET  /api/followups/due                – leads due for D+2 / D+4 / D+7
POST /api/followups/{lead_id}/generate – generate a follow-up message (preview only)
POST /api/followups/{lead_id}/send     – generate if needed + mark as sent (primary action)
POST /api/followups/{lead_id}/mark-sent – mark sent without generating (legacy)
"""
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_coach
from ..database import get_db
from .. import models
from ..agents import followup_agent

router = APIRouter(prefix="/api/followups", tags=["followups"])

FOLLOWUP_DAYS = [2, 4, 7]


def _msg_field(day: int) -> str:
    return f"followup_d{day}_message"


def _sent_field(day: int) -> str:
    return f"followup_d{day}_sent_at"


def _due_days(lead: models.Lead) -> list[int]:
    """Return ALL follow-up days that are due and not yet sent, lowest first."""
    if not lead.messaged_at or lead.stage != "contacted":
        return []
    delta = (datetime.utcnow() - lead.messaged_at).days
    return [
        day for day in FOLLOWUP_DAYS
        if delta >= day and not getattr(lead, _sent_field(day))
    ]


def _serialize_due(lead: models.Lead) -> list[dict]:
    """One entry per due day for this lead."""
    days = _due_days(lead)
    if not days:
        return []
    base = {
        "lead_id":          lead.id,
        "name":             lead.name,
        "handle":           lead.handle,
        "platform":         lead.platform,
        "bio":              lead.bio,
        "messaged_at":      lead.messaged_at.isoformat(),
        "outreach_message": lead.outreach_message,
        "followup_d2_message":  lead.followup_d2_message,
        "followup_d2_sent_at":  lead.followup_d2_sent_at.isoformat() if lead.followup_d2_sent_at else None,
        "followup_d4_message":  lead.followup_d4_message,
        "followup_d4_sent_at":  lead.followup_d4_sent_at.isoformat() if lead.followup_d4_sent_at else None,
        "followup_d7_message":  lead.followup_d7_message,
        "followup_d7_sent_at":  lead.followup_d7_sent_at.isoformat() if lead.followup_d7_sent_at else None,
    }
    return [{**base, "due_day": day} for day in days]


@router.get("/due")
def get_due(
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    leads = (
        db.query(models.Lead)
        .filter(
            models.Lead.coach_id == coach.id,
            models.Lead.stage == "contacted",
            models.Lead.messaged_at.isnot(None),
        )
        .all()
    )
    result = []
    for lead in leads:
        result.extend(_serialize_due(lead))
    # Sort: most urgent (day 7) first, then by messaged_at descending
    result.sort(key=lambda x: (-x["due_day"], x["messaged_at"]))
    return result


class DayRequest(BaseModel):
    day: int


def _get_lead(lead_id: int, coach_id: int, db: Session) -> models.Lead:
    lead = db.query(models.Lead).filter(
        models.Lead.id == lead_id,
        models.Lead.coach_id == coach_id,
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead introuvable")
    return lead


@router.post("/{lead_id}/generate")
def generate(
    lead_id: int,
    req: DayRequest,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    if req.day not in FOLLOWUP_DAYS:
        raise HTTPException(status_code=400, detail=f"day doit être dans {FOLLOWUP_DAYS}")
    lead = _get_lead(lead_id, coach.id, db)
    if not lead.outreach_message:
        raise HTTPException(status_code=400, detail="Aucun DM original trouvé pour ce lead")

    message = followup_agent.generate_followup(
        lead_data={"name": lead.name, "bio": lead.bio or "", "platform": lead.platform},
        original_dm=lead.outreach_message,
        coach_name=coach.name,
        coach_niche=coach.niche or "",
        coach_offer=coach.offer_description or "",
        day=req.day,
    )
    setattr(lead, _msg_field(req.day), message)
    db.commit()
    return {"ok": True, "message": message, "day": req.day}


@router.post("/{lead_id}/send")
def send_followup(
    lead_id: int,
    req: DayRequest,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    """Generate message if not yet written, then mark as sent. Primary one-click action."""
    if req.day not in FOLLOWUP_DAYS:
        raise HTTPException(status_code=400, detail=f"day doit être dans {FOLLOWUP_DAYS}")
    lead = _get_lead(lead_id, coach.id, db)

    message = getattr(lead, _msg_field(req.day))

    if not message:
        if not lead.outreach_message:
            raise HTTPException(status_code=400, detail="Aucun DM original — générez d'abord le message de prospection")
        message = followup_agent.generate_followup(
            lead_data={"name": lead.name, "bio": lead.bio or "", "platform": lead.platform},
            original_dm=lead.outreach_message,
            coach_name=coach.name,
            coach_niche=coach.niche or "",
            coach_offer=coach.offer_description or "",
            day=req.day,
        )
        setattr(lead, _msg_field(req.day), message)

    setattr(lead, _sent_field(req.day), datetime.utcnow())
    db.commit()
    return {"ok": True, "message": message, "day": req.day}


@router.post("/{lead_id}/mark-sent")
def mark_sent(
    lead_id: int,
    req: DayRequest,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    if req.day not in FOLLOWUP_DAYS:
        raise HTTPException(status_code=400, detail=f"day doit être dans {FOLLOWUP_DAYS}")
    lead = _get_lead(lead_id, coach.id, db)
    setattr(lead, _sent_field(req.day), datetime.utcnow())
    db.commit()
    return {"ok": True, "day": req.day}
