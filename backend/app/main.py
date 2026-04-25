"""FastAPI entrypoint for the AI Video Editor Agent."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Literal

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.jobs import store
from app.api.pipeline import run_job
from app.core.config import settings


app = FastAPI(title="AI Video Editor Agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/edit")
async def submit_edit(
    background: BackgroundTasks,
    video: UploadFile = File(...),
    instructions: str = Form(""),
    format_hint: Literal["short", "long", "auto"] = Form("auto"),
) -> JSONResponse:
    if not settings.anthropic_api_key:
        raise HTTPException(500, "ANTHROPIC_API_KEY not set in backend/.env")

    job = store.create()

    suffix = Path(video.filename or "input.mp4").suffix or ".mp4"
    dest = settings.uploads_dir / f"{job.id}{suffix}"
    with dest.open("wb") as f:
        shutil.copyfileobj(video.file, f)

    background.add_task(run_job, job.id, dest, instructions, format_hint)
    return JSONResponse({"job_id": job.id, "status": job.status})


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    job = store.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job.to_dict()


@app.get("/api/download/{job_id}")
def download(job_id: str):
    out = settings.outputs_dir / f"{job_id}.mp4"
    if not out.exists():
        raise HTTPException(404, "Output not ready")
    return FileResponse(out, media_type="video/mp4", filename=f"edited-{job_id}.mp4")


frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
