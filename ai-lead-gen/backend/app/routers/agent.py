"""Agent router — control the autonomous lead generation engine."""
import json
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_coach
from ..database import get_db
from .. import models
from ..scheduler import schedule_coach, unschedule_coach, get_next_run, trigger_now

router = APIRouter(prefix="/api/agent", tags=["agent"])


class AgentSettingsRequest(BaseModel):
    enabled: bool | None = None
    frequency_hours: int | None = None
    platforms: list[str] | None = None
    max_results_per_platform: int | None = None
    dm_threshold: int | None = None
    webhook_url: str | None = None


def _serialize_run(r: models.AgentRun) -> dict:
    return {
        "id": r.id,
        "status": r.status,
        "platforms_searched": json.loads(r.platforms_searched or "[]"),
        "leads_found": r.leads_found or 0,
        "leads_qualified": r.leads_qualified or 0,
        "dms_generated": r.dms_generated or 0,
        "high_score_leads": r.high_score_leads or 0,
        "error_message": r.error_message,
        "started_at": r.started_at.isoformat() if r.started_at else None,
        "finished_at": r.finished_at.isoformat() if r.finished_at else None,
    }


@router.get("/status")
def agent_status(
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    last_run = (
        db.query(models.AgentRun)
        .filter(models.AgentRun.coach_id == coach.id)
        .order_by(models.AgentRun.started_at.desc())
        .first()
    )
    next_run = get_next_run(coach.id)
    platforms = json.loads(
        getattr(coach, "agent_platforms", None) or
        '["instagram","tiktok","linkedin","twitter","reddit"]'
    )
    competitors = json.loads(getattr(coach, "competitor_accounts", None) or "[]")
    return {
        "enabled": getattr(coach, "agent_enabled", False) or False,
        "frequency_hours": getattr(coach, "agent_frequency_hours", 6) or 6,
        "platforms": platforms,
        "max_results_per_platform": getattr(coach, "agent_max_results_per_platform", 20) or 20,
        "dm_threshold": getattr(coach, "agent_dm_threshold", 70) or 70,
        "webhook_url": getattr(coach, "webhook_url", None),
        "last_run_at": coach.agent_last_run_at.isoformat() if getattr(coach, "agent_last_run_at", None) else None,
        "next_run_at": next_run.isoformat() if next_run else None,
        "last_run": _serialize_run(last_run) if last_run else None,
        "competitor_accounts": competitors,
    }


@router.patch("/settings")
def update_settings(
    req: AgentSettingsRequest,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    if req.enabled is not None:
        coach.agent_enabled = req.enabled
    if req.frequency_hours is not None:
        if not (1 <= req.frequency_hours <= 168):
            raise HTTPException(400, "frequency_hours must be 1–168")
        coach.agent_frequency_hours = req.frequency_hours
    if req.platforms is not None:
        valid = {"instagram", "tiktok", "linkedin", "twitter", "reddit"}
        for p in req.platforms:
            if p not in valid:
                raise HTTPException(400, f"Invalid platform: {p}")
        coach.agent_platforms = json.dumps(req.platforms)
    if req.max_results_per_platform is not None:
        if not (5 <= req.max_results_per_platform <= 50):
            raise HTTPException(400, "max_results_per_platform must be 5–50")
        coach.agent_max_results_per_platform = req.max_results_per_platform
    if req.dm_threshold is not None:
        if not (0 <= req.dm_threshold <= 100):
            raise HTTPException(400, "dm_threshold must be 0–100")
        coach.agent_dm_threshold = req.dm_threshold
    if req.webhook_url is not None:
        coach.webhook_url = req.webhook_url or None

    db.commit()

    if coach.agent_enabled:
        schedule_coach(coach.id, coach.agent_frequency_hours or 6)
    else:
        unschedule_coach(coach.id)

    return {"ok": True}


@router.post("/trigger")
def trigger_agent(
    coach: models.Coach = Depends(get_current_coach),
):
    if not coach.onboarded or not coach.niche or not coach.offer_description:
        raise HTTPException(400, "Complete onboarding first (niche + offer required)")

    # Check not already running
    from .agent import _get_running_run
    if _get_running_run(coach.id):
        raise HTTPException(409, "An autonomous run is already in progress")

    trigger_now(coach.id)
    return {"ok": True, "message": "Autonomous run started"}


def _get_running_run(coach_id: int):
    from ..database import SessionLocal
    db = SessionLocal()
    try:
        return (
            db.query(models.AgentRun)
            .filter(
                models.AgentRun.coach_id == coach_id,
                models.AgentRun.status == "running",
            )
            .first()
        )
    finally:
        db.close()


@router.get("/runs")
def list_runs(
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    runs = (
        db.query(models.AgentRun)
        .filter(models.AgentRun.coach_id == coach.id)
        .order_by(models.AgentRun.started_at.desc())
        .limit(10)
        .all()
    )
    return [_serialize_run(r) for r in runs]


# ---------------------------------------------------------------------------
# Competitor account management
# ---------------------------------------------------------------------------

class CompetitorRequest(BaseModel):
    url: str
    platform: str = "instagram"


def _extract_handle(url: str) -> str:
    h = url.strip().rstrip("/").split("@")[-1].split("?")[0]
    if "/" in h:
        h = h.split("/")[-1]
    return h.lstrip("@").lower()


@router.get("/competitors")
def list_competitors(
    coach: models.Coach = Depends(get_current_coach),
):
    accounts = json.loads(getattr(coach, "competitor_accounts", None) or "[]")
    return accounts


@router.post("/competitors", status_code=201)
def add_competitor(
    req: CompetitorRequest,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    valid_platforms = {"instagram", "tiktok", "twitter", "linkedin"}
    if req.platform not in valid_platforms:
        raise HTTPException(400, f"Platform must be one of: {', '.join(valid_platforms)}")

    handle = _extract_handle(req.url)
    if not handle:
        raise HTTPException(400, "Could not extract handle from URL")

    accounts: list[dict] = json.loads(getattr(coach, "competitor_accounts", None) or "[]")

    if any(a["handle"] == handle for a in accounts):
        raise HTTPException(409, f"Competitor @{handle} already added")

    if len(accounts) >= 10:
        raise HTTPException(400, "Maximum 10 competitor accounts")

    accounts.append({"url": req.url, "platform": req.platform, "handle": handle})
    coach.competitor_accounts = json.dumps(accounts)
    db.commit()
    return {"ok": True, "handle": handle, "competitors": accounts}


@router.delete("/competitors/{handle}")
def remove_competitor(
    handle: str,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    accounts: list[dict] = json.loads(getattr(coach, "competitor_accounts", None) or "[]")
    updated = [a for a in accounts if a["handle"] != handle.lower()]
    if len(updated) == len(accounts):
        raise HTTPException(404, f"Competitor @{handle} not found")
    coach.competitor_accounts = json.dumps(updated)
    db.commit()
    return {"ok": True, "competitors": updated}
