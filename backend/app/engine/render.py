"""
FFmpeg renderer. Takes the EditPlan + transcript + raw video and produces the
final edited video.

Pipeline:
  1. For each keep_segment, produce a trimmed clip (lossless cut).
  2. Concat clips into a single mid file.
  3. Apply zoom plan via zoompan filter (drift, punch_in, pull_out).
  4. Burn ASS subtitles built from the transcript + emphasis words.
  5. Return final mp4 path + packaging metadata.
"""

from __future__ import annotations

import json
import shlex
import subprocess
from pathlib import Path
from typing import Any

from app.agent.planner import EditPlan
from app.engine.captions import WordTiming, build_ass


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed:\n  cmd: {shlex.join(cmd)}\n  stderr: {proc.stderr[-2000:]}"
        )


def _probe_duration(path: Path) -> float:
    out = subprocess.check_output(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        text=True,
    )
    return float(out.strip())


def _cut_segment(src: Path, start: float, end: float, dst: Path) -> None:
    duration = max(0.05, end - start)
    _run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-ss", f"{start:.3f}", "-i", str(src),
        "-t", f"{duration:.3f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        str(dst),
    ])


def _concat(parts: list[Path], dst: Path) -> None:
    list_path = dst.with_suffix(".txt")
    list_path.write_text("\n".join(f"file '{p.as_posix()}'" for p in parts))
    _run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(list_path),
        "-c", "copy",
        str(dst),
    ])
    list_path.unlink(missing_ok=True)


def _build_zoom_expression(
    zoom_plan: list[dict[str, Any]],
    total_duration: float,
    fps: int = 30,
) -> tuple[str, str]:
    """
    Convert the zoom plan into zoompan z/x/y expressions evaluated per output
    frame. zoompan uses 'on' = output frame number. We translate timestamps to
    frame ranges and build a chained if(...) expression.
    """
    if not zoom_plan:
        return "1", "iw/2-(iw/zoom/2)"

    sorted_plan = sorted(zoom_plan, key=lambda p: float(p.get("start", 0)))

    z_expr = "1"
    for step in reversed(sorted_plan):
        s = float(step.get("start", 0))
        e = float(step.get("end", s + 1))
        z_from = float(step.get("from", 1.0))
        z_to = float(step.get("to", z_from))
        f0 = int(s * fps)
        f1 = max(f0 + 1, int(e * fps))
        seg_dur = max(1, f1 - f0)
        seg_expr = (
            f"({z_from} + ({z_to}-{z_from}) * "
            f"min(1, max(0, (on-{f0}) / {seg_dur})))"
        )
        z_expr = f"if(between(on,{f0},{f1}),{seg_expr},{z_expr})"

    x_expr = "iw/2-(iw/zoom/2)"
    y_expr = "ih/2-(ih/zoom/2)"
    return z_expr, f"{x_expr};{y_expr}"


def render(
    src: Path,
    transcript: dict[str, Any],
    plan: EditPlan,
    work_dir: Path,
    output_path: Path,
) -> dict[str, Any]:
    work_dir.mkdir(parents=True, exist_ok=True)

    keep = plan.keep_segments or [
        {"start": 0.0, "end": float(transcript.get("duration", 0.0))}
    ]

    parts: list[Path] = []
    cum = 0.0
    remapped_zoom: list[dict[str, Any]] = []
    remapped_words: list[WordTiming] = []

    for i, seg in enumerate(keep):
        s = float(seg["start"])
        e = float(seg["end"])
        if e <= s:
            continue
        part = work_dir / f"part_{i:04d}.mp4"
        _cut_segment(src, s, e, part)
        parts.append(part)

        for zp in plan.zoom_plan:
            zs = float(zp.get("start", 0))
            ze = float(zp.get("end", zs))
            if zs >= s and ze <= e:
                remapped_zoom.append({
                    **zp,
                    "start": cum + (zs - s),
                    "end": cum + (ze - s),
                })

        for tseg in transcript.get("segments", []):
            for w in tseg.get("words", []):
                ws = float(w["start"])
                we = float(w["end"])
                if ws >= s and we <= e:
                    remapped_words.append(WordTiming(
                        text=w["text"].strip(),
                        start=cum + (ws - s),
                        end=cum + (we - s),
                    ))

        cum += (e - s)

    if not parts:
        raise RuntimeError("No keep_segments produced any clip.")

    concat_path = work_dir / "concat.mp4"
    _concat(parts, concat_path)
    total_duration = _probe_duration(concat_path)

    short_form = plan.format == "short"
    ass_path = work_dir / "captions.ass"
    build_ass(
        remapped_words,
        ass_path,
        short_form=short_form,
        emphasis_words=set(plan.caption_emphasis_words),
    )

    z_expr, xy_expr = _build_zoom_expression(remapped_zoom, total_duration)
    x_expr, y_expr = xy_expr.split(";")

    target_w, target_h = (1080, 1920) if short_form else (1920, 1080)
    fps = 30
    total_frames = max(1, int(total_duration * fps))

    vf = (
        f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase,"
        f"crop={target_w}:{target_h},"
        f"zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}':"
        f"d=1:s={target_w}x{target_h}:fps={fps},"
        f"ass={ass_path.as_posix()}"
    )

    _run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(concat_path),
        "-vf", vf,
        "-frames:v", str(total_frames),
        "-c:v", "libx264", "-preset", "medium", "-crf", "19",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        str(output_path),
    ])

    return {
        "output": str(output_path),
        "duration": total_duration,
        "format": plan.format,
        "packaging": plan.packaging,
        "plan": plan.raw,
    }
