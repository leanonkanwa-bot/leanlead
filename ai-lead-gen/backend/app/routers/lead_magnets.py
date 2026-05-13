"""
Lead Magnet Library
GET    /api/lead-magnets          – list coach's lead magnets
POST   /api/lead-magnets          – create new lead magnet
PATCH  /api/lead-magnets/{id}     – update
DELETE /api/lead-magnets/{id}     – delete
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_coach
from ..database import get_db
from .. import models

router = APIRouter(prefix="/api/lead-magnets", tags=["lead-magnets"])

VALID_TYPES = {"pdf", "video", "ebook", "call", "course", "other"}


class LeadMagnetIn(BaseModel):
    title: str
    description: str | None = None
    type: str = "pdf"
    link: str | None = None


def _serialize(lm: models.LeadMagnet) -> dict:
    return {
        "id": lm.id,
        "coach_id": lm.coach_id,
        "title": lm.title,
        "description": lm.description,
        "type": lm.type,
        "link": lm.link,
        "created_at": lm.created_at.isoformat() if lm.created_at else None,
    }


@router.get("")
def list_lead_magnets(
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    items = db.query(models.LeadMagnet).filter(
        models.LeadMagnet.coach_id == coach.id
    ).order_by(models.LeadMagnet.created_at.desc()).all()
    return [_serialize(lm) for lm in items]


@router.post("", status_code=201)
def create_lead_magnet(
    req: LeadMagnetIn,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    if req.type not in VALID_TYPES:
        raise HTTPException(400, f"Invalid type. Must be one of: {', '.join(VALID_TYPES)}")
    lm = models.LeadMagnet(
        coach_id=coach.id,
        title=req.title.strip(),
        description=req.description,
        type=req.type,
        link=req.link,
    )
    db.add(lm)
    db.commit()
    db.refresh(lm)
    return _serialize(lm)


@router.patch("/{lm_id}")
def update_lead_magnet(
    lm_id: int,
    req: LeadMagnetIn,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    lm = db.query(models.LeadMagnet).filter(
        models.LeadMagnet.id == lm_id,
        models.LeadMagnet.coach_id == coach.id,
    ).first()
    if not lm:
        raise HTTPException(404, "Lead magnet not found")
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(lm, field, value)
    db.commit()
    return _serialize(lm)


@router.delete("/{lm_id}", status_code=204)
def delete_lead_magnet(
    lm_id: int,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    lm = db.query(models.LeadMagnet).filter(
        models.LeadMagnet.id == lm_id,
        models.LeadMagnet.coach_id == coach.id,
    ).first()
    if not lm:
        raise HTTPException(404, "Lead magnet not found")
    db.delete(lm)
    db.commit()
