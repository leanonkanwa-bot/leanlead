"""
Keyword Trigger System
GET    /api/keyword-triggers              – list
POST   /api/keyword-triggers              – create
PATCH  /api/keyword-triggers/{id}         – update
DELETE /api/keyword-triggers/{id}         – delete
POST   /api/keyword-triggers/{id}/fire    – simulate a trigger (increment count + get DM preview)
GET    /api/keyword-triggers/stats        – monthly stats
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_coach
from ..database import get_db
from .. import models

router = APIRouter(prefix="/api/keyword-triggers", tags=["keyword-triggers"])

PLATFORM_DM_URL = {
    "instagram": "https://ig.me/m/{handle}",
    "tiktok":    "https://www.tiktok.com/messages?u={handle}",
}


class TriggerIn(BaseModel):
    keyword: str
    platform: str = "instagram"
    message_template: str | None = None
    lead_magnet_id: int | None = None
    active: bool = True


def _serialize(t: models.KeywordTrigger, include_magnet: bool = True) -> dict:
    d = {
        "id": t.id,
        "keyword": t.keyword,
        "platform": t.platform,
        "message_template": t.message_template,
        "lead_magnet_id": t.lead_magnet_id,
        "trigger_count": t.trigger_count,
        "last_triggered_at": t.last_triggered_at.isoformat() if t.last_triggered_at else None,
        "active": t.active,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }
    if include_magnet and t.lead_magnet:
        d["lead_magnet"] = {
            "id": t.lead_magnet.id,
            "title": t.lead_magnet.title,
            "type": t.lead_magnet.type,
            "link": t.lead_magnet.link,
        }
    else:
        d["lead_magnet"] = None
    return d


@router.get("/stats")
def trigger_stats(
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    triggers = db.query(models.KeywordTrigger).filter(
        models.KeywordTrigger.coach_id == coach.id,
        models.KeywordTrigger.active == True,
    ).all()
    total_triggers = sum(t.trigger_count for t in triggers)
    return {
        "total_triggers": total_triggers,
        "active_keywords": len(triggers),
        "top_keywords": sorted(
            [{"keyword": t.keyword, "platform": t.platform, "count": t.trigger_count} for t in triggers],
            key=lambda x: x["count"], reverse=True
        )[:5],
    }


@router.get("")
def list_triggers(
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    items = db.query(models.KeywordTrigger).filter(
        models.KeywordTrigger.coach_id == coach.id
    ).order_by(models.KeywordTrigger.created_at.desc()).all()
    return [_serialize(t) for t in items]


@router.post("", status_code=201)
def create_trigger(
    req: TriggerIn,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    keyword = req.keyword.strip().upper()
    if not keyword:
        raise HTTPException(400, "Keyword cannot be empty")

    # Verify lead magnet belongs to coach
    if req.lead_magnet_id:
        lm = db.query(models.LeadMagnet).filter(
            models.LeadMagnet.id == req.lead_magnet_id,
            models.LeadMagnet.coach_id == coach.id,
        ).first()
        if not lm:
            raise HTTPException(404, "Lead magnet not found")

    # Build default message template if none provided
    message_template = req.message_template
    if not message_template:
        message_template = f"Hey ! Tu as commenté {keyword} sous mon post 😊 Voici ce que j'ai préparé pour toi : {{{{link}}}}"

    trigger = models.KeywordTrigger(
        coach_id=coach.id,
        keyword=keyword,
        platform=req.platform,
        message_template=message_template,
        lead_magnet_id=req.lead_magnet_id,
        active=req.active,
    )
    db.add(trigger)
    db.commit()
    db.refresh(trigger)
    return _serialize(trigger)


@router.patch("/{trigger_id}")
def update_trigger(
    trigger_id: int,
    req: TriggerIn,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    trigger = db.query(models.KeywordTrigger).filter(
        models.KeywordTrigger.id == trigger_id,
        models.KeywordTrigger.coach_id == coach.id,
    ).first()
    if not trigger:
        raise HTTPException(404, "Trigger not found")

    data = req.model_dump(exclude_unset=True)
    if "keyword" in data:
        data["keyword"] = data["keyword"].strip().upper()
    for field, value in data.items():
        setattr(trigger, field, value)
    db.commit()
    return _serialize(trigger)


@router.delete("/{trigger_id}", status_code=204)
def delete_trigger(
    trigger_id: int,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    trigger = db.query(models.KeywordTrigger).filter(
        models.KeywordTrigger.id == trigger_id,
        models.KeywordTrigger.coach_id == coach.id,
    ).first()
    if not trigger:
        raise HTTPException(404, "Trigger not found")
    db.delete(trigger)
    db.commit()


@router.post("/{trigger_id}/fire")
def fire_trigger(
    trigger_id: int,
    commenter_handle: str = "",
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    """Record a trigger event (e.g. from manual logging or webhook). Returns the DM to send."""
    trigger = db.query(models.KeywordTrigger).filter(
        models.KeywordTrigger.id == trigger_id,
        models.KeywordTrigger.coach_id == coach.id,
        models.KeywordTrigger.active == True,
    ).first()
    if not trigger:
        raise HTTPException(404, "Trigger not found or inactive")

    # Build the DM message
    link = ""
    if trigger.lead_magnet:
        link = trigger.lead_magnet.link or ""

    message = (trigger.message_template or "").replace("{{link}}", link)

    # Increment counter
    trigger.trigger_count = (trigger.trigger_count or 0) + 1
    trigger.last_triggered_at = datetime.utcnow()
    db.commit()

    # Build platform DM URL
    dm_url = ""
    if commenter_handle and trigger.platform in PLATFORM_DM_URL:
        dm_url = PLATFORM_DM_URL[trigger.platform].format(handle=commenter_handle.lstrip("@"))

    return {
        "ok": True,
        "message": message,
        "dm_url": dm_url,
        "trigger_count": trigger.trigger_count,
    }
