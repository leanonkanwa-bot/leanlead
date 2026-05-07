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

Base.metadata.create_all(bind=engine)

# Lightweight additive migrations for columns added after initial deploy
_migrations = [
    "ALTER TABLE coaches ADD COLUMN offer_price REAL",
]
with engine.connect() as _conn:
    for _sql in _migrations:
        try:
            _conn.execute(text(_sql))
            _conn.commit()
        except Exception:
            pass  # column already exists

app = FastAPI(title="LeanLead AI", version="2.0.0")

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

# Serve built React frontend
_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
if _dist.exists():
    app.mount("/assets", StaticFiles(directory=str(_dist / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        return FileResponse(str(_dist / "index.html"))


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "2.0.0"}
