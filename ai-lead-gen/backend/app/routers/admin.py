import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _require_admin(x_admin_key: str = Header(default="")):
    admin_key = os.getenv("ADMIN_KEY", "")
    if not admin_key or x_admin_key != admin_key:
        raise HTTPException(status_code=401, detail="Invalid admin key")


@router.get("/stats")
def admin_stats(db: Session = Depends(get_db), _=Depends(_require_admin)):
    coaches = db.query(models.Coach).all()
    now = datetime.utcnow()

    total = len(coaches)
    active_trials = sum(
        1 for c in coaches
        if getattr(c, "trial_end_date", None) and c.trial_end_date > now
    )
    expired_trials = sum(
        1 for c in coaches
        if getattr(c, "trial_end_date", None) and c.trial_end_date <= now
    )
    plan_breakdown = {}
    for c in coaches:
        plan = getattr(c, "plan", "free") or "free"
        plan_breakdown[plan] = plan_breakdown.get(plan, 0) + 1

    total_leads = db.query(models.Lead).count()

    return {
        "total_coaches": total,
        "active_trials": active_trials,
        "expired_trials": expired_trials,
        "plan_breakdown": plan_breakdown,
        "total_leads": total_leads,
    }


@router.get("/emails")
def admin_emails(db: Session = Depends(get_db), _=Depends(_require_admin)):
    coaches = db.query(models.Coach).order_by(models.Coach.created_at.desc()).all()
    now = datetime.utcnow()

    rows = []
    for c in coaches:
        trial_end = getattr(c, "trial_end_date", None)
        days_left = max(0, (trial_end - now).days) if trial_end else None
        trial_active = trial_end is not None and trial_end > now
        rows.append({
            "id": c.id,
            "name": c.name,
            "email": c.email,
            "plan": getattr(c, "plan", "free") or "free",
            "signup_date": c.created_at.isoformat() if c.created_at else None,
            "trial_end_date": trial_end.isoformat() if trial_end else None,
            "trial_active": trial_active,
            "trial_days_left": days_left,
            "onboarded": c.onboarded,
            "email_verified": getattr(c, "email_verified", False) or False,
        })

    return {"coaches": rows, "total": len(rows)}
