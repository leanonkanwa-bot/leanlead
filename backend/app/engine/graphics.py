"""
Motion graphics renderer.

Each function renders ONE graphic to a PNG (RGBA, transparent background)
that the FFmpeg filter chain overlays onto the video. Animation (slide-in,
fade-in) is done by the FFmpeg overlay expressions, NOT here — that keeps
each graphic file small (one PNG) and keeps the renderer fast.

Today's library:
  - lower_third_title  — section title that slides in from the left
  - stat_circle        — donut chart with a big number in the middle
  - checklist          — stacked rounded pill buttons with X / ✓ icons

Style alignment is intentional: rounded corners, sans-serif Bold,
high-contrast accent colours pulled from the app's palette so the
graphics feel like one product. Match the polished references the user
shared (Hormozi/Codie/MrBeast tier).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from PIL import Image, ImageDraw, ImageFont


# Brand palette — kept in sync with the front-end picker.
PALETTE = {
    "blue":      (10, 132, 255, 255),    # Electric Blue  #0A84FF
    "red":       (255, 59, 48, 255),     # Clean Red      #FF3B30
    "yellow":    (255, 229, 0, 255),     # Electric Yellow #FFE500
    "green":     (52, 199, 89, 255),     # System Green
    "orange":    (255, 107, 0, 255),     # Orange Flash   #FF6B00
    "white":     (255, 255, 255, 255),
    "black":     (10, 10, 10, 255),
    "panel":     (26, 26, 26, 230),      # ~90% opaque dark grey
    "panel_2":   (16, 16, 16, 235),
}


def _load_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    """Resolve a font we baked into the Docker image. Falls back to default
    if a system box has none of these — prevents render hard-fails."""
    candidates = [
        f"/usr/local/share/fonts/leanlead/{name}.ttf",
        f"/usr/share/fonts/truetype/{name.lower()}/{name}.ttf",
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _hex_to_rgba(hex6: str | None, fallback: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    if not hex6:
        return fallback
    h = hex6.lstrip("#")
    if len(h) != 6:
        return fallback
    try:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)
    except ValueError:
        return fallback


def _rounded_rect(
    draw: ImageDraw.ImageDraw,
    bbox: tuple[int, int, int, int],
    radius: int,
    fill: tuple[int, int, int, int] | None = None,
    outline: tuple[int, int, int, int] | None = None,
    outline_width: int = 0,
) -> None:
    draw.rounded_rectangle(
        bbox, radius=radius, fill=fill,
        outline=outline, width=outline_width,
    )


def _text_size(font: ImageFont.FreeTypeFont, text: str) -> tuple[int, int]:
    bbox = font.getbbox(text)
    return (bbox[2] - bbox[0], bbox[3] - bbox[1])


# ---------------------------------------------------------------------------
# Graphic 1 — Lower Third Title
# ---------------------------------------------------------------------------

def render_lower_third(
    title: str,
    accent_word: str | None,
    out_path: Path,
    *,
    width: int = 900,
    accent_hex: str = "#0A84FF",
    font_title: str = "Poppins-Bold",
    font_subtitle: str = "Poppins-SemiBold",
) -> Path:
    """Title with optional accent (coloured) second line, plus a sparkle +
    subtitle. Matches the 'Building Your / Content Machine' reference.
    Slide-in is done by ffmpeg overlay; this PNG is the final state."""
    height = 360 if accent_word else 200
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    title_font = _load_font(font_title, 92)
    accent_color = _hex_to_rgba(accent_hex, PALETTE["blue"])

    y = 0
    draw.text((0, y), title, font=title_font, fill=PALETTE["white"])
    if accent_word:
        y += 110
        draw.text((0, y), accent_word, font=title_font, fill=accent_color)

    img.save(out_path, "PNG")
    return out_path


# ---------------------------------------------------------------------------
# Graphic 2 — Stat Circle (donut + big number)
# ---------------------------------------------------------------------------

def render_stat_circle(
    percent: int,
    label: str,
    sub_label: str | None,
    out_path: Path,
    *,
    accent_hex: str = "#0A84FF",
    size: int = 700,
    stroke: int = 60,
    font_number: str = "Poppins-ExtraBold",
    font_label: str = "Poppins-SemiBold",
) -> Path:
    """Donut chart filled to `percent`, big '<N>%' in the centre, smaller
    label underneath. Matches the '80% of your time' reference."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    accent = _hex_to_rgba(accent_hex, PALETTE["blue"])
    percent = max(0, min(100, int(percent)))

    bbox = (stroke // 2, stroke // 2, size - stroke // 2, size - stroke // 2)
    # Track + filled arc — start at top (-90°), draw clockwise.
    end_angle = -90 + (360 * percent / 100)
    draw.arc(bbox, start=-90, end=270, fill=(40, 40, 40, 255), width=stroke)
    draw.arc(bbox, start=-90, end=end_angle, fill=accent, width=stroke)

    # Centre text — number then sub-label.
    number_font = _load_font(font_number, int(size * 0.22))
    label_font = _load_font(font_label, int(size * 0.07))

    number_text = f"{percent}%"
    nw, nh = _text_size(number_font, number_text)
    draw.text(
        ((size - nw) / 2, (size - nh) / 2 - (size * 0.02)),
        number_text, font=number_font, fill=PALETTE["white"],
    )

    if label:
        lw, lh = _text_size(label_font, label)
        draw.text(
            ((size - lw) / 2, (size + nh) / 2 + 4),
            label, font=label_font, fill=PALETTE["white"],
        )

    img.save(out_path, "PNG")
    return out_path


# ---------------------------------------------------------------------------
# Graphic 3 — Checklist Reveal (X / ✓ rounded pill buttons)
# ---------------------------------------------------------------------------

@dataclass
class ChecklistItem:
    text: str
    ok: bool   # True = green ✓, False = red ✗


def render_checklist(
    items: Sequence[ChecklistItem],
    out_path: Path,
    *,
    width: int = 1200,
    pill_height: int = 160,
    gap: int = 28,
    font_name: str = "Poppins-Bold",
) -> Path:
    """Stacked rounded pill buttons with red X or green ✓ on the left.
    Matches the 'Not a Demo / Not Theory / Real Automations' reference."""
    n = len(items)
    if n == 0:
        # Render a 1×1 transparent pixel so callers always get a valid file.
        Image.new("RGBA", (1, 1), (0, 0, 0, 0)).save(out_path, "PNG")
        return out_path

    height = n * pill_height + (n - 1) * gap
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    text_font = _load_font(font_name, 84)

    radius = pill_height // 2
    icon_size = pill_height - 28

    for i, item in enumerate(items):
        y0 = i * (pill_height + gap)
        y1 = y0 + pill_height
        outline = PALETTE["green"] if item.ok else PALETTE["red"]

        _rounded_rect(
            draw,
            (0, y0, width, y1),
            radius=radius,
            fill=PALETTE["panel"],
            outline=outline,
            outline_width=4,
        )

        # Icon — filled circle in red/green with a white X or ✓.
        icon_x = 16
        icon_y = y0 + (pill_height - icon_size) // 2
        draw.ellipse(
            (icon_x, icon_y, icon_x + icon_size, icon_y + icon_size),
            fill=outline,
        )
        cx = icon_x + icon_size / 2
        cy = icon_y + icon_size / 2
        if item.ok:
            # Checkmark — three points, drawn as two thick lines.
            arm = icon_size * 0.25
            stem = icon_size * 0.4
            draw.line(
                [(cx - arm, cy + 0), (cx - arm * 0.2, cy + arm * 0.7), (cx + stem * 0.7, cy - stem * 0.5)],
                fill=PALETTE["white"], width=10, joint="curve",
            )
        else:
            arm = icon_size * 0.28
            draw.line([(cx - arm, cy - arm), (cx + arm, cy + arm)], fill=PALETTE["white"], width=10)
            draw.line([(cx + arm, cy - arm), (cx - arm, cy + arm)], fill=PALETTE["white"], width=10)

        # Label text — left-aligned with consistent padding after the icon.
        text_x = icon_x + icon_size + 36
        tw, th = _text_size(text_font, item.text)
        draw.text(
            (text_x, y0 + (pill_height - th) / 2 - 6),
            item.text, font=text_font, fill=PALETTE["white"],
        )

    img.save(out_path, "PNG")
    return out_path


# ---------------------------------------------------------------------------
# Dispatcher — turn one motion_graphic JSON into a rendered PNG + position.
# ---------------------------------------------------------------------------

@dataclass
class RenderedGraphic:
    """Result of rendering one motion_graphic: PNG path + frame placement +
    timing the renderer should overlay it on."""
    png: Path
    at: float
    duration: float
    x_expr: str        # ffmpeg overlay x expression
    y_expr: str        # ffmpeg overlay y expression
    fade_in_s: float = 0.3
    kind: str = ""


def render_motion_graphic(
    spec: dict,
    out_dir: Path,
    index: int,
    *,
    target_w: int,
    target_h: int,
    accent_hex: str = "#0A84FF",
) -> RenderedGraphic | None:
    """Render one motion_graphic spec to a PNG + return its placement.

    Returns None for kinds we don't yet execute (the agent still gets to
    plan them; the renderer just doesn't draw them today)."""
    kind = (spec.get("kind") or "").lower()
    try:
        at = float(spec.get("at", 0))
        duration = float(spec.get("duration", 2.0))
    except (TypeError, ValueError):
        return None
    out_dir.mkdir(parents=True, exist_ok=True)
    png = out_dir / f"mg_{index:03d}_{kind}.png"

    if kind == "lower_third" or kind == "fly_in":
        # fly_in degrades into a lower-third title — same visual, same intent.
        title = str(spec.get("title") or spec.get("text") or "").strip()
        accent_word = (spec.get("accent_word") or "").strip() or None
        if not title:
            return None
        render_lower_third(title, accent_word, png, accent_hex=accent_hex)
        # Slide-in from the left, anchored to lower-left third of the frame.
        margin_l = int(target_w * 0.06)
        anchor_y = int(target_h * 0.15)
        x_expr = (
            f"if(lt(t-{at:.3f},0.3),"
            f"-w + ({margin_l} - (-w))*((t-{at:.3f})/0.3)*((t-{at:.3f})/0.3)*(3-2*((t-{at:.3f})/0.3)),"
            f"{margin_l})"
        )
        y_expr = f"{anchor_y}"
        return RenderedGraphic(
            png=png, at=at, duration=duration,
            x_expr=x_expr, y_expr=y_expr, kind=kind,
        )

    if kind == "count_up" or kind == "stat_circle":
        try:
            value = int(round(float(spec.get("to") or spec.get("percent") or 50)))
        except (TypeError, ValueError):
            return None
        label = str(spec.get("label") or spec.get("text") or "").strip()
        render_stat_circle(value, label, None, png, accent_hex=accent_hex)
        # Centred horizontally, slightly above frame middle.
        x_expr = f"(W-w)/2"
        y_expr = f"(H-h)/2 - {int(target_h * 0.04)}"
        return RenderedGraphic(
            png=png, at=at, duration=duration,
            x_expr=x_expr, y_expr=y_expr, kind=kind,
        )

    if kind == "checklist":
        raw_items = spec.get("items") or []
        items: list[ChecklistItem] = []
        for raw in raw_items:
            if isinstance(raw, dict):
                items.append(ChecklistItem(
                    text=str(raw.get("text", "")).strip(),
                    ok=bool(raw.get("ok", raw.get("checked", False))),
                ))
            elif isinstance(raw, (list, tuple)) and len(raw) >= 2:
                items.append(ChecklistItem(text=str(raw[0]), ok=bool(raw[1])))
        items = [it for it in items if it.text]
        if not items:
            return None
        render_checklist(items, png)
        x_expr = "(W-w)/2"
        y_expr = "(H-h)/2"
        return RenderedGraphic(
            png=png, at=at, duration=duration,
            x_expr=x_expr, y_expr=y_expr, kind=kind,
        )

    # Unsupported kinds (split, quote, highlight, flow, arrow_callout) —
    # the agent still plans them, the renderer just doesn't draw them yet.
    return None
