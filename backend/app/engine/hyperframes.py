"""
Hyperframes-style HTML motion graphics — generates HTML animations and renders
them to video via headless Chromium + FFmpeg.

Rendering strategy: one Chromium screenshot with --virtual-time-budget to
advance virtual time so CSS animations reach their settled state, then FFmpeg
loops that single frame into a video clip of the requested duration.  This
avoids launching Chromium once per frame (which would add minutes of overhead
per graphic at 30fps) while still producing visually complete animated frames.

Falls back gracefully:
  1. Chromium screenshot → FFmpeg video (primary path)
  2. FFmpeg lavfi drawtext/drawbox overlay (if Chromium unavailable)
  3. Transparent black clip (if all else fails — no overlay shown)
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from app.engine.transcribe import FFMPEG_PATH, FFPROBE_PATH

# Chromium binary search order
_CHROMIUM_CANDIDATES = [
    os.environ.get("CHROMIUM_PATH", ""),
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
]


def _find_chromium() -> str | None:
    for p in _CHROMIUM_CANDIDATES:
        if p and os.path.exists(p):
            return p
    return None


# ── HTML generation ────────────────────────────────────────────────────────────


def generate_motion_graphic_html(
    graphic_type: str,
    content: dict,
    duration: float,
    width: int,
    height: int,
    brand_color: str = "#FF7751",
    font: str = "Inter",
) -> str:
    """Generate HTML for a motion graphic overlay.

    graphic_type: "title_card" | "stat" | "checklist" | "key_phrase" | "lower_third"
    content: type-specific dict (text, number, label, items, phrase, context, …)
    Returns an HTML string ready for headless-Chrome screenshot.
    """
    accent = brand_color

    if graphic_type == "title_card":
        text = content.get("text", "").upper()
        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    width: {width}px; height: {height}px;
    background: #2B080C;
    display: flex; align-items: center; justify-content: center;
    font-family: '{font}', Inter, sans-serif;
    overflow: hidden;
}}
.card {{
    text-align: center;
    animation: scaleIn {duration:.2f}s linear forwards;
}}
.title {{
    font-size: {int(height * 0.12)}px;
    font-weight: 900;
    color: #FDFBF7;
    letter-spacing: 0.05em;
    line-height: 1.1;
}}
@keyframes scaleIn {{
    0%   {{ transform: scale(1.00); }}
    100% {{ transform: scale(1.05); }}
}}
</style>
</head>
<body><div class="card"><div class="title">{_esc(text)}</div></div></body>
</html>"""

    if graphic_type == "stat":
        number  = _esc(str(content.get("number", "")))
        label   = _esc(str(content.get("label", "")))
        context = _esc(str(content.get("context", "")))
        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    width: {width}px; height: {height}px;
    background: transparent;
    display: flex; align-items: center; justify-content: center;
    font-family: '{font}', Inter, sans-serif;
}}
.stat-card {{
    background: rgba(0,0,0,0.85);
    border-radius: 24px;
    padding: 48px 64px;
    text-align: center;
    animation: popIn 0.3s cubic-bezier(0.34,1.56,0.64,1) forwards;
    border: 1px solid rgba(255,255,255,0.1);
}}
.number {{
    font-size: {int(height * 0.15)}px;
    font-weight: 900;
    color: {accent};
    line-height: 1;
}}
.label {{
    font-size: {int(height * 0.04)}px;
    color: #FFFFFF;
    font-weight: 700;
    margin-top: 16px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}}
.context {{
    font-size: {int(height * 0.025)}px;
    color: rgba(255,255,255,0.6);
    margin-top: 8px;
}}
@keyframes popIn {{
    0%   {{ transform: scale(0.8); opacity: 0; }}
    100% {{ transform: scale(1);   opacity: 1; }}
}}
</style>
</head>
<body>
<div class="stat-card">
    <div class="number">{number}</div>
    <div class="label">{label}</div>
    <div class="context">{context}</div>
</div>
</body>
</html>"""

    if graphic_type == "checklist":
        title = _esc(str(content.get("title", "")))
        items = [_esc(str(it)) for it in (content.get("items") or [])[:5]]
        items_html = "".join(
            f'<div class="item" style="animation-delay:{i * 0.3:.1f}s">'
            f'<span class="bullet" style="color:{accent}">▸</span>'
            f'<span class="text">{it}</span></div>'
            for i, it in enumerate(items)
        )
        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    width: {width}px; height: {height}px;
    background: transparent;
    display: flex; align-items: center; justify-content: flex-start;
    padding-left: {int(width * 0.06)}px;
    font-family: '{font}', Inter, sans-serif;
}}
.list {{
    background: rgba(0,0,0,0.80);
    border-radius: 20px;
    padding: 32px 40px;
    border-left: 4px solid {accent};
    max-width: {int(width * 0.45)}px;
}}
.list-title {{
    font-size: {int(height * 0.035)}px;
    color: {accent};
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 20px;
}}
.item {{
    display: flex; align-items: center; gap: 12px;
    margin: 12px 0;
    animation: slideIn 0.4s cubic-bezier(0.16,1,0.3,1) both;
    opacity: 0;
}}
.bullet {{ font-size: {int(height * 0.03)}px; }}
.text  {{
    font-size: {int(height * 0.028)}px;
    color: #FFFFFF;
    font-weight: 500;
}}
@keyframes slideIn {{
    from {{ transform: translateX(-30px); opacity: 0; }}
    to   {{ transform: translateX(0);    opacity: 1; }}
}}
</style>
</head>
<body>
<div class="list">
    <div class="list-title">{title}</div>
    {items_html}
</div>
</body>
</html>"""

    if graphic_type == "key_phrase":
        small = _esc(str(content.get("context", "")))
        large = _esc(str(content.get("phrase", "")))
        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    width: {width}px; height: {height}px;
    background: transparent;
    display: flex; flex-direction: column;
    align-items: center; justify-content: flex-end;
    padding-bottom: {int(height * 0.12)}px;
    font-family: '{font}', Inter, sans-serif;
}}
.small {{
    font-size: {int(height * 0.028)}px;
    color: rgba(255,255,255,0.7);
    font-weight: 400;
    margin-bottom: 8px;
    animation: fadeIn 0.3s ease forwards;
}}
.large {{
    font-size: {int(height * 0.065)}px;
    color: {accent};
    font-weight: 800;
    text-align: center;
    line-height: 1.15;
    animation: popIn 0.4s cubic-bezier(0.34,1.56,0.64,1) forwards;
    text-shadow: 0 4px 20px rgba(0,0,0,0.5);
}}
@keyframes fadeIn {{
    from {{ opacity: 0; transform: translateY(10px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
}}
@keyframes popIn {{
    from {{ transform: scale(0.85); opacity: 0; }}
    to   {{ transform: scale(1);    opacity: 1; }}
}}
</style>
</head>
<body>
    <div class="small">{small}</div>
    <div class="large">{large}</div>
</body>
</html>"""

    if graphic_type == "lower_third":
        name    = _esc(str(content.get("name", "")))
        role    = _esc(str(content.get("role", "")))
        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    width: {width}px; height: {height}px;
    background: transparent;
    display: flex; align-items: flex-end;
    padding: 0 {int(width * 0.05)}px {int(height * 0.10)}px;
    font-family: '{font}', Inter, sans-serif;
}}
.lower {{
    background: rgba(0,0,0,0.80);
    border-left: 4px solid {accent};
    padding: 12px 20px;
    border-radius: 4px 8px 8px 4px;
    animation: slideUp 0.35s cubic-bezier(0.16,1,0.3,1) forwards;
    opacity: 0;
}}
.name {{
    font-size: {int(height * 0.04)}px;
    font-weight: 700;
    color: #FFFFFF;
}}
.role {{
    font-size: {int(height * 0.025)}px;
    color: {accent};
    margin-top: 4px;
}}
@keyframes slideUp {{
    from {{ transform: translateY(20px); opacity: 0; }}
    to   {{ transform: translateY(0);    opacity: 1; }}
}}
</style>
</head>
<body>
<div class="lower">
    <div class="name">{name}</div>
    <div class="role">{role}</div>
</div>
</body>
</html>"""

    # Transparent fallback
    return (
        f'<!DOCTYPE html><html>'
        f'<body style="background:transparent;width:{width}px;height:{height}px;">'
        f'</body></html>'
    )


def _esc(t: str) -> str:
    """Minimal HTML escaping for content injected into templates."""
    return (
        t.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace('"', "&quot;")
    )


# ── Video rendering ────────────────────────────────────────────────────────────


def render_html_to_video(
    html_content: str,
    output_path: Path,
    duration: float,
    width: int,
    height: int,
    fps: int = 30,
) -> bool:
    """Render an HTML animation to a silent MP4 clip.

    Strategy:
      1. Write HTML to disk.
      2. Launch Chromium headless with --virtual-time-budget=<ms> so CSS
         animations reach their fully-animated state in one screenshot pass.
      3. Convert the PNG to a looped video of `duration` seconds.

    Returns True on success; False if Chromium is unavailable (caller skips).
    Logs all failures via print() so Railway logs show the exact failure point.
    """
    output_path = Path(output_path)
    work_dir = output_path.parent
    work_dir.mkdir(parents=True, exist_ok=True)

    chromium = _find_chromium()
    if not chromium:
        print("[HYPERFRAMES] Chromium not found — motion graphic skipped")
        return False

    html_path = work_dir / f"{output_path.stem}_hf.html"
    png_path  = work_dir / f"{output_path.stem}_hf.png"
    try:
        html_path.write_text(html_content, encoding="utf-8")

        # --virtual-time-budget advances the page clock so animations that take
        # 300–600ms finish before the screenshot is taken — we get the settled
        # state rather than the very first frame.
        vt_budget_ms = max(1000, int(duration * 1000))
        result = subprocess.run(
            [
                chromium,
                "--headless=new",
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--disable-software-rasterizer",
                f"--window-size={width},{height}",
                f"--virtual-time-budget={vt_budget_ms}",
                f"--screenshot={png_path}",
                f"file://{html_path}",
            ],
            capture_output=True,
            timeout=30,
        )
        if result.returncode != 0 or not png_path.exists():
            print(
                f"[HYPERFRAMES] Chromium failed (rc={result.returncode}): "
                f"{result.stderr[-300:]}"
            )
            return False

        # Convert single PNG → video of exact duration (loop=1 + -t flag)
        subprocess.run(
            [
                FFMPEG_PATH, "-y", "-loglevel", "error",
                "-loop", "1",
                "-i", str(png_path),
                "-t", f"{duration:.3f}",
                "-vf", f"scale={width}:{height},setsar=1:1,fps={fps},format=yuva420p",
                "-c:v", "libvpx-vp9",   # VP9 supports alpha (YUVA420)
                "-b:v", "0", "-crf", "20",
                "-an",
                str(output_path.with_suffix(".webm")),
            ],
            check=True,
            timeout=60,
        )
        # Remux to MP4 (no alpha, black background) for ffmpeg overlay compatibility
        subprocess.run(
            [
                FFMPEG_PATH, "-y", "-loglevel", "error",
                "-i", str(output_path.with_suffix(".webm")),
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "0",
                "-pix_fmt", "yuv420p",
                "-an",
                str(output_path),
            ],
            check=True,
            timeout=60,
        )
        output_path.with_suffix(".webm").unlink(missing_ok=True)
        print(f"[HYPERFRAMES] Rendered: {output_path.name}  ({duration:.2f}s)")
        return True

    except subprocess.TimeoutExpired:
        print(f"[HYPERFRAMES] Timeout rendering {output_path.name}")
        return False
    except Exception as exc:
        import traceback as _tb
        print(f"[HYPERFRAMES] Exception: {exc}\n{_tb.format_exc()[:600]}")
        return False
    finally:
        html_path.unlink(missing_ok=True)
        png_path.unlink(missing_ok=True)
