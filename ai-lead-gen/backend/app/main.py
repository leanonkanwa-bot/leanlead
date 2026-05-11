import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from sqlalchemy import text
from .database import Base, engine
from .routers import auth, leads, pipeline, prospecting, followups, analytics
from .routers import agent as agent_router
from .routers import icp as icp_router

Base.metadata.create_all(bind=engine)

# Lightweight additive migrations for columns added after initial deploy
_migrations = [
    "ALTER TABLE coaches ADD COLUMN offer_price REAL",
    "ALTER TABLE coaches ADD COLUMN icp_pain_points TEXT",
    "UPDATE leads SET qualification_score = qualification_score * 10 WHERE qualification_score > 0 AND qualification_score <= 10",
    # Autonomous agent fields
    "ALTER TABLE coaches ADD COLUMN agent_enabled INTEGER DEFAULT 0",
    "ALTER TABLE coaches ADD COLUMN agent_frequency_hours INTEGER DEFAULT 6",
    "ALTER TABLE coaches ADD COLUMN agent_platforms TEXT",
    "ALTER TABLE coaches ADD COLUMN agent_max_results_per_platform INTEGER DEFAULT 20",
    "ALTER TABLE coaches ADD COLUMN agent_dm_threshold INTEGER DEFAULT 70",
    "ALTER TABLE coaches ADD COLUMN agent_last_run_at DATETIME",
    "ALTER TABLE coaches ADD COLUMN webhook_url TEXT",
    "ALTER TABLE coaches ADD COLUMN competitor_accounts TEXT",
    # Intelligence fields v3
    "ALTER TABLE leads ADD COLUMN language TEXT",
    "ALTER TABLE leads ADD COLUMN psychographic_profile TEXT",
    "ALTER TABLE leads ADD COLUMN response_probability REAL",
    "ALTER TABLE leads ADD COLUMN dm_variant_b TEXT",
    "ALTER TABLE leads ADD COLUMN dm_variant_sent TEXT",
    "ALTER TABLE leads ADD COLUMN warming_status TEXT DEFAULT 'none'",
    "ALTER TABLE leads ADD COLUMN warming_comment TEXT",
    "ALTER TABLE leads ADD COLUMN source_tag TEXT",
    # Intelligence fields v4 — objection pre-emption, pain escalation, social proof
    "ALTER TABLE leads ADD COLUMN predicted_objection TEXT",
    "ALTER TABLE leads ADD COLUMN score_delta REAL",
    "ALTER TABLE leads ADD COLUMN escalation_alert INTEGER DEFAULT 0",
    "ALTER TABLE coaches ADD COLUMN testimonials TEXT",
    # Intelligence fields v5 — aspiration gap detector
    "ALTER TABLE leads ADD COLUMN aspiration_gap_score REAL DEFAULT 0",
    # Intelligence fields v5 — price tier, trust velocity, voice tone
    "ALTER TABLE leads ADD COLUMN price_tier TEXT DEFAULT 'mid'",
    "ALTER TABLE leads ADD COLUMN trust_velocity TEXT DEFAULT 'unknown'",
    "ALTER TABLE leads ADD COLUMN voice_tone_intensity REAL DEFAULT 0",
    # Intelligence fields v6 — churn prevention, emotional trajectory
    "ALTER TABLE leads ADD COLUMN churn_risk REAL DEFAULT 0",
    "ALTER TABLE leads ADD COLUMN emotion_history TEXT",
    "ALTER TABLE leads ADD COLUMN reengagement_message TEXT",
    # Intelligence fields v7 — CRM enrichment, sales scripts, nurture, attribution
    "ALTER TABLE leads ADD COLUMN enriched_data TEXT",
    "ALTER TABLE leads ADD COLUMN enriched_at DATETIME",
    "ALTER TABLE leads ADD COLUMN sales_script TEXT",
    "ALTER TABLE leads ADD COLUMN nurture_sequence TEXT",
    "ALTER TABLE leads ADD COLUMN nurture_step INTEGER DEFAULT 0",
    "ALTER TABLE leads ADD COLUMN converting_angle TEXT",
    "ALTER TABLE leads ADD COLUMN predicted_close_date DATETIME",
    # ICP and competitive intelligence tables (created via Base.metadata.create_all)
]
with engine.connect() as _conn:
    for _sql in _migrations:
        try:
            _conn.execute(text(_sql))
            _conn.commit()
        except Exception:
            pass  # column already exists or migration already applied

app = FastAPI(title="LeanLead AI", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(leads.router)
app.include_router(pipeline.router)
app.include_router(prospecting.router)
app.include_router(followups.router)
app.include_router(analytics.router)
app.include_router(agent_router.router)
app.include_router(icp_router.router)


@app.on_event("startup")
def startup_scheduler():
    """Start APScheduler and resume jobs for all coaches with agent_enabled."""
    from .scheduler import start_scheduler, schedule_coach
    from .database import SessionLocal
    from . import models

    start_scheduler()

    db = SessionLocal()
    try:
        enabled_coaches = (
            db.query(models.Coach)
            .filter(models.Coach.agent_enabled == True, models.Coach.onboarded == True)
            .all()
        )
        for coach in enabled_coaches:
            schedule_coach(coach.id, coach.agent_frequency_hours or 6)
    except Exception:
        pass
    finally:
        db.close()


@app.on_event("shutdown")
def shutdown_scheduler():
    from .scheduler import stop_scheduler
    stop_scheduler()


# Serve built React frontend
_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
if _dist.exists():
    app.mount("/assets", StaticFiles(directory=str(_dist / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        return FileResponse(str(_dist / "index.html"))


@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "3.0.0"}
