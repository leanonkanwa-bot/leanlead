"""
Pipeline router – runs agents on a lead and updates the DB.
POST /api/pipeline/{lead_id}/qualify   → qualifier_agent
POST /api/pipeline/{lead_id}/write     → writer_agent
POST /api/pipeline/{lead_id}/reply     → reply_agent
POST /api/pipeline/{lead_id}/sync-crm  → crm_agent (Airtable)
"""
import json
import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_coach
from ..database import get_db
from .. import models
from ..agents import qualifier_agent, writer_agent, reply_agent, crm_agent

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


def _get_lead_or_404(lead_id: int, coach: models.Coach, db: Session) -> models.Lead:
    lead = db.query(models.Lead).filter(
        models.Lead.id == lead_id, models.Lead.coach_id == coach.id
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.post("/{lead_id}/qualify")
def qualify(
    lead_id: int,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    if not coach.niche or not coach.offer_description:
        raise HTTPException(status_code=400, detail="Complete onboarding before qualifying leads")
    lead = _get_lead_or_404(lead_id, coach, db)

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
    lead.stage = "qualified"
    db.commit()
    db.refresh(lead)

    return {"ok": True, "result": result}


@router.post("/{lead_id}/write")
def write(
    lead_id: int,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    lead = _get_lead_or_404(lead_id, coach, db)
    if not lead.qualification_reason:
        raise HTTPException(status_code=400, detail="Qualify this lead first")

    qualification = {
        "score": lead.qualification_score,
        "reason": lead.qualification_reason,
        "pain_points": json.loads(lead.pain_points or "[]"),
        "recommended_angle": lead.recommended_angle or "",
    }
    message = writer_agent.write_outreach_message(
        lead_data={"name": lead.name, "bio": lead.bio or ""},
        coach_name=coach.name,
        coach_niche=coach.niche or "",
        coach_offer=coach.offer_description or "",
        qualification=qualification,
    )
    lead.outreach_message = message
    lead.stage = "messaged"
    db.commit()

    return {"ok": True, "message": message}


class ReplyRequest(BaseModel):
    lead_reply: str
    conversation_history: str = ""


@router.post("/{lead_id}/reply")
def reply(
    lead_id: int,
    req: ReplyRequest,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    lead = _get_lead_or_404(lead_id, coach, db)
    calendly = coach.calendly_link or os.getenv("CALENDLY_LINK", "")

    suggested = reply_agent.generate_reply(
        lead_reply=req.lead_reply,
        conversation_history=req.conversation_history,
        coach_name=coach.name,
        coach_offer=coach.offer_description or "",
        calendly_link=calendly,
    )
    lead.reply_received = req.lead_reply
    lead.suggested_reply = suggested
    lead.stage = "replied"
    db.commit()

    return {"ok": True, "suggested_reply": suggested}


@router.post("/{lead_id}/sync-crm")
def sync_crm(
    lead_id: int,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    lead = _get_lead_or_404(lead_id, coach, db)

    base_id = coach.airtable_base_id or os.getenv("AIRTABLE_BASE_ID", "appfdB2W41J5sVZ2U")
    api_key = coach.airtable_api_key or os.getenv("AIRTABLE_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=400, detail="No Airtable API key configured")

    pain_points_str = ""
    if lead.pain_points:
        try:
            pain_points_str = ", ".join(json.loads(lead.pain_points))
        except Exception:
            pain_points_str = lead.pain_points

    lead_data = {
        "name": lead.name,
        "handle": lead.handle,
        "platform": lead.platform,
        "profile_url": lead.profile_url or "",
        "bio": lead.bio or "",
        "followers": lead.followers,
        "qualification_score": lead.qualification_score,
        "qualification_reason": (lead.qualification_reason or "") + (f"\nPain points: {pain_points_str}" if pain_points_str else ""),
        "stage": lead.stage,
        "outreach_message": lead.outreach_message or "",
        "notes": lead.notes or "",
    }

    try:
        record_id = crm_agent.sync_lead(
            lead_data=lead_data,
            airtable_base_id=base_id,
            airtable_api_key=api_key,
            record_id=lead.airtable_record_id,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Airtable sync failed: {e}")

    lead.airtable_record_id = record_id
    db.commit()

    return {"ok": True, "airtable_record_id": record_id}
