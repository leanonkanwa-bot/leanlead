"""FastAPI entrypoint for the AI Video Editor Agent."""

from __future__ import annotations

import secrets
import shutil
from pathlib import Path
from typing import Literal

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app.api.jobs import store
from app.api.pipeline import run_job, run_render_phase
from app.api.upload import assembled_path, router as upload_router
from app.core.config import settings


app = FastAPI(title="AI Video Editor Agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)

AUTH_COOKIE = "lle_token"


def _auth_required() -> bool:
    return bool(settings.access_password)


def _check_auth(request: Request) -> None:
    if not _auth_required():
        return
    token = request.cookies.get(AUTH_COOKIE) or request.headers.get("x-access-token")
    if not token or not secrets.compare_digest(token, settings.access_password):
        raise HTTPException(status_code=401, detail="auth required")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/auth/status")
def auth_status(request: Request) -> dict:
    if not _auth_required():
        return {"required": False, "authed": True}
    cookie = request.cookies.get(AUTH_COOKIE)
    authed = bool(cookie) and secrets.compare_digest(cookie, settings.access_password)
    return {"required": True, "authed": authed}


@app.post("/api/auth/login")
def auth_login(password: str = Form(...)) -> Response:
    if not _auth_required():
        return JSONResponse({"ok": True})
    if not secrets.compare_digest(password, settings.access_password):
        raise HTTPException(401, "wrong password")
    resp = JSONResponse({"ok": True})
    resp.set_cookie(
        AUTH_COOKIE,
        settings.access_password,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
        secure=False,
    )
    return resp


@app.post("/api/auth/logout")
def auth_logout() -> Response:
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(AUTH_COOKIE)
    return resp


@app.post("/api/edit")
async def submit_edit(
    request: Request,
    background: BackgroundTasks,
    video: UploadFile = File(None, max_upload_size=500 * 1024 * 1024),  # optional — omitted when upload_id is used; 500 MB ceiling for direct uploads
    upload_id: str = Form(""),        # set by chunked-upload flow
    instructions: str = Form(""),
    format_hint: Literal["short", "long", "auto"] = Form("auto"),
    caption_font: str = Form("Poppins Bold"),
    caption_color: str = Form("white"),
    caption_position: Literal["center", "bottom", "side-left", "side-right"] = Form("center"),
    caption_style: Literal["impact", "kinetic"] = Form("impact"),
    brand_color: str = Form(""),
    theme: str = Form("dark-pro"),
    # Content brief fields (Feature 6)
    target_audience: str = Form(""),
    main_message: str = Form(""),
    desired_emotion: str = Form(""),
    platform: str = Form(""),
    content_type_hint: str = Form(""),
    _: None = Depends(_check_auth),
) -> JSONResponse:
    if not settings.anthropic_api_key:
        raise HTTPException(500, "ANTHROPIC_API_KEY not set in backend/.env")

    job = store.create()

    if upload_id:
        # Chunked-upload path: file was already assembled by /api/upload/assemble
        dest = assembled_path(upload_id)
        if dest is None:
            raise HTTPException(400, f"No assembled file found for upload_id={upload_id!r}. "
                                     "Call /api/upload/assemble first.")
    elif video and video.filename:
        # Direct upload path (files ≤ ~100 MB)
        suffix = Path(video.filename).suffix or ".mp4"
        dest = settings.uploads_dir / f"{job.id}{suffix}"
        with dest.open("wb") as f:
            shutil.copyfileobj(video.file, f)
    else:
        raise HTTPException(400, "Provide either a video file or an upload_id.")

    # Persist source path + run params so the job can be retried after a
    # server restart without the user having to re-upload the video.
    run_params = dict(
        instructions=instructions,
        format_hint=format_hint,
        caption_font=caption_font,
        caption_color=caption_color,
        caption_position=caption_position,
        caption_style=caption_style,
        brand_color=brand_color or None,
        aesthetic=theme,
        target_audience=target_audience,
        main_message=main_message,
        desired_emotion=desired_emotion,
        platform=platform,
        content_type_hint=content_type_hint,
    )
    store.update(job.id, source_path=str(dest), params=run_params)

    background.add_task(run_job, job.id, dest, **run_params)
    return JSONResponse({"job_id": job.id, "status": job.status})


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str, request: Request, _: None = Depends(_check_auth)) -> dict:
    job = store.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job.to_dict()


@app.post("/api/retry/{job_id}")
async def retry_job(
    job_id: str,
    background: BackgroundTasks,
    request: Request,
    _: None = Depends(_check_auth),
) -> JSONResponse:
    """Re-run a failed job using the source video that is still on disk.
    Returns a NEW job_id — the frontend polls that one."""
    original = store.get(job_id)
    if not original:
        raise HTTPException(404, "Original job not found")
    if not original.source_path:
        raise HTTPException(400, "No source file stored for this job — please re-upload")
    src = Path(original.source_path)
    if not src.exists():
        raise HTTPException(400, "Source video is no longer on disk — please re-upload")

    new_job = store.create()
    run_params = original.params or {}
    store.update(new_job.id, source_path=str(src), params=run_params)
    background.add_task(run_job, new_job.id, src, **run_params)
    return JSONResponse({"job_id": new_job.id})


@app.get("/api/jobs/{job_id}/plan")
def get_plan(job_id: str, request: Request, _: None = Depends(_check_auth)) -> dict:
    """Return the edit plan preview for a job that is in ready_for_review status."""
    job = store.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status != "ready_for_review":
        raise HTTPException(400, f"Job is not ready for review (status: {job.status})")
    return {"plan_preview": job.preview or {}, "plan_data": job.plan_data or {}}


@app.post("/api/jobs/{job_id}/approve")
async def approve_job(
    job_id: str,
    background: BackgroundTasks,
    request: Request,
    _: None = Depends(_check_auth),
) -> JSONResponse:
    """Approve an edit plan and trigger the render phase (Phase 2)."""
    job = store.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status != "ready_for_review":
        raise HTTPException(400, f"Job is not in ready_for_review state (status: {job.status})")
    if not job.source_path:
        raise HTTPException(400, "No source file stored for this job")
    src = Path(job.source_path)
    if not src.exists():
        raise HTTPException(400, "Source video is no longer on disk — please re-upload")

    store.update(job_id, status="rendering", progress=70,
                 message="Approved — starting render…")
    background.add_task(run_render_phase, job_id, src)
    return JSONResponse({"job_id": job_id, "status": "rendering"})


@app.get("/api/download/{job_id}")
def download(job_id: str, request: Request, _: None = Depends(_check_auth)):
    out = settings.outputs_dir / f"{job_id}.mp4"
    if not out.exists():
        raise HTTPException(404, "Output not ready")
    return FileResponse(out, media_type="video/mp4", filename=f"edited-{job_id}.mp4")


frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
