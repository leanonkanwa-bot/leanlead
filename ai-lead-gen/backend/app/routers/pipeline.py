"""
Pipeline router – runs agents on a lead and updates the DB.
POST /api/pipeline/{lead_id}/qualify   → qualifier_agent
POST /api/pipeline/{lead_id}/write     → writer_agent (sets stage=contacted + messaged_at)
POST /api/pipeline/{lead_id}/reply     → reply_agent  (sets stage=replied)
PATCH /api/pipeline/{lead_id}/stage   → manual stage override
"""
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_coach
from ..database import get_db
from .. import models
from ..agents import qualifier_agent, writer_agent, reply_agent
from .leads import _serialize

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

VALID_STAGES = ["new", "contacted", "replied", "booked", "closed"]


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
    # Save intelligence fields
    psycho = result.get("psychographic", {})
    if psycho:
        lead.psychographic_profile = json.dumps(psycho)
        lead.language = psycho.get("language", "fr")
    if result.get("response_probability") is not None:
        lead.response_probability = result["response_probability"]
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
    lead.stage = "contacted"
    lead.messaged_at = datetime.utcnow()
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
    calendly = coach.calendly_link or ""

    result = reply_agent.generate_reply(
        lead_reply=req.lead_reply,
        conversation_history=req.conversation_history,
        coach_name=coach.name,
        coach_niche=coach.niche or "",
        coach_offer=coach.offer_description or "",
        calendly_link=calendly,
    )

    lead.reply_received = req.lead_reply
    lead.reply_received_at = datetime.utcnow()
    lead.suggested_reply = result["reply"]

    # Stage transitions based on classification
    classification = result.get("classification", "NEUTRE")
    if classification == "SIGNAL_ACHAT":
        lead.stage = "booked"
    elif classification == "NEGATIF":
        lead.stage = "closed"
    else:
        lead.stage = "replied"

    db.commit()

    return {
        "ok": True,
        "classification": classification,
        "reasoning": result.get("reasoning", ""),
        "suggested_reply": result["reply"],
        "inject_calendly": result.get("inject_calendly", False),
    }


class StageRequest(BaseModel):
    stage: str


@router.patch("/{lead_id}/stage")
def set_stage(
    lead_id: int,
    req: StageRequest,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    if req.stage not in VALID_STAGES:
        raise HTTPException(status_code=400, detail=f"Stage must be one of {VALID_STAGES}")
    lead = _get_lead_or_404(lead_id, coach, db)
    lead.stage = req.stage
    if req.stage == "contacted" and not lead.messaged_at:
        lead.messaged_at = datetime.utcnow()
    db.commit()
    return {"ok": True, "stage": req.stage}


@router.post("/{lead_id}/warm")
def generate_warming_comment(
    lead_id: int,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    """Generate an AI warming comment to post on the lead's content before the DM."""
    lead = _get_lead_or_404(lead_id, coach, db)
    language = getattr(lead, "language", None) or "fr"
    qualification = {
        "score": lead.qualification_score,
        "pain_points": json.loads(lead.pain_points or "[]"),
        "recommended_angle": lead.recommended_angle or "",
    }
    comment = writer_agent.write_warming_comment(
        lead_data={"name": lead.name, "bio": lead.bio or "", "posts_summary": lead.posts_summary or ""},
        coach_name=coach.name,
        qualification=qualification,
        language=language,
    )
    lead.warming_comment = comment
    lead.warming_status = "comment_ready"
    db.commit()
    return {"ok": True, "comment": comment}


class WarmingStatusRequest(BaseModel):
    status: str  # comment_ready | commented | dm_ready


@router.post("/{lead_id}/mark-warmed")
def mark_warming_step(
    lead_id: int,
    req: WarmingStatusRequest,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    valid = {"none", "comment_ready", "commented", "dm_ready"}
    if req.status not in valid:
        raise HTTPException(400, f"Status must be one of: {', '.join(valid)}")
    lead = _get_lead_or_404(lead_id, coach, db)
    lead.warming_status = req.status
    db.commit()
    return {"ok": True, "warming_status": req.status}


@router.post("/{lead_id}/write-ab")
def write_ab_variants(
    lead_id: int,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    """Generate both A/B DM variants for this lead."""
    lead = _get_lead_or_404(lead_id, coach, db)
    if not lead.qualification_reason:
        raise HTTPException(400, "Qualify this lead first")

    language = getattr(lead, "language", None) or "fr"
    qualification = {
        "score": lead.qualification_score,
        "reason": lead.qualification_reason,
        "pain_points": json.loads(lead.pain_points or "[]"),
        "recommended_angle": lead.recommended_angle or "",
    }
    va, vb = writer_agent.write_ab_variants(
        lead_data={
            "name": lead.name, "handle": lead.handle, "platform": lead.platform,
            "bio": lead.bio or "", "posts_summary": lead.posts_summary or "",
        },
        coach_name=coach.name,
        coach_niche=coach.niche or "",
        coach_offer=coach.offer_description or "",
        qualification=qualification,
        language=language,
    )
    lead.outreach_message = va
    lead.dm_variant_b = vb
    db.commit()
    return {"ok": True, "variant_a": va, "variant_b": vb}


class VariantRequest(BaseModel):
    variant: str  # "A" or "B"


@router.post("/{lead_id}/mark-variant")
def mark_variant_sent(
    lead_id: int,
    req: VariantRequest,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    """Track which DM variant was actually sent to this lead."""
    if req.variant not in ("A", "B"):
        raise HTTPException(400, "Variant must be A or B")
    lead = _get_lead_or_404(lead_id, coach, db)
    lead.dm_variant_sent = req.variant
    lead.stage = "contacted"
    lead.messaged_at = lead.messaged_at or datetime.utcnow()
    db.commit()
    return {"ok": True, "variant_sent": req.variant}
