"""End-to-end pipeline runner — transcribe → plan → render."""

from __future__ import annotations

import traceback
from pathlib import Path

from app.agent.planner import FormatHint, analyze_subject_position, plan_edit
from app.api.jobs import store
from app.core.config import settings
from app.engine.render import render
from app.engine.transcribe import transcribe, unload_model


def run_job(
    job_id: str,
    src: Path,
    instructions: str,
    format_hint: FormatHint,
    *,
    caption_font: str = "Poppins Bold",
    caption_color: str = "white",
    caption_position: str = "center",
    caption_style: str = "impact",
    brand_color: str | None = None,
    aesthetic: str = "dark-pro",
) -> None:
    try:
        store.update(job_id, status="transcribing", progress=10,
                     message="Transcribing audio with Whisper…")
        transcript = transcribe(src).to_dict()

        store.update(job_id, status="planning", progress=35,
                     message="Analysing subject position (vision)…")
        subject_pos = analyze_subject_position(src)

        store.update(job_id, status="planning", progress=40,
                     message="Asking the agent for an edit plan…")
        plan = plan_edit(
            transcript,
            instructions,
            format_hint=format_hint,
            brand_color=brand_color,
            caption_color=caption_color,
            caption_position=caption_position,
            caption_font=caption_font,
            subject_position=subject_pos,
            aesthetic=aesthetic,
        )

        # Reclaim ~250 MB of RAM before ffmpeg fires up — otherwise the
        # encoder gets OOM-killed on small dynos (no stderr, exit signal 9).
        unload_model()

        store.update(job_id, status="rendering", progress=70,
                     message="Rendering with FFmpeg…")
        out_path = settings.outputs_dir / f"{job_id}.mp4"
        work_dir = settings.work_dir / job_id
        result = render(
            src,
            transcript,
            plan,
            work_dir,
            out_path,
            caption_font=caption_font,
            caption_color=caption_color,
            caption_position=caption_position,
            caption_style=caption_style,
            brand_color=brand_color,
            aesthetic=aesthetic,
            subject_position=subject_pos,
        )

        store.update(
            job_id,
            status="done",
            progress=100,
            message="Done.",
            result={
                "video_url": f"/api/download/{job_id}",
                "packaging": result["packaging"],
                "format": result["format"],
                "duration": result["duration"],
                "plan": result["plan"],
            },
        )
    except Exception as e:
        store.update(
            job_id,
            status="error",
            error=f"{type(e).__name__}: {e}\n{traceback.format_exc()}",
            message="Job failed.",
        )
