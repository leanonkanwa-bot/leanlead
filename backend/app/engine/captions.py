"""Build .ass subtitle files.

Hard rules (Hormozi/Sanchez/MrBeast caption system):
  - ONE word per card. Always. No exceptions.
  - One single color (no shadow / outline / gradient / stroke).
  - Font is Poppins Bold by default. User can pick from a small allowlist.
  - Emphasis word: 20% larger, same color, same font.
  - No punctuation in captions.
  - Words appear ONLY when they are spoken — start..end of each word.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


# Allowed fonts — must be installed in the Docker image (see Dockerfile).
ALLOWED_FONTS = {
    "Poppins Bold",
    "Poppins ExtraBold",
    "Inter Bold",
    "Montserrat Bold",
    "Roboto Bold",
}

ALLOWED_COLORS = {
    "white": "FFFFFF",
    "yellow": "FFE500",
    "red": "FF3B30",
}

ALLOWED_POSITIONS = {"center", "bottom", "side-left", "side-right"}

PUNCT_RE = re.compile(r"[.,!?;:\"'()\[\]…–—]")


@dataclass
class WordTiming:
    text: str
    start: float
    end: float


def _ts(t: float) -> str:
    if t < 0:
        t = 0.0
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t - (h * 3600 + m * 60)
    return f"{h}:{m:02d}:{s:05.2f}"


def _strip_punct(word: str) -> str:
    return PUNCT_RE.sub("", word).strip()


def _hex_to_ass_bgr(hex6: str) -> str:
    """ASS uses &H00BBGGRR primary colour notation."""
    hex6 = hex6.lstrip("#").upper()
    if len(hex6) != 6:
        hex6 = "FFFFFF"
    r, g, b = hex6[0:2], hex6[2:4], hex6[4:6]
    return f"&H00{b}{g}{r}"


def _alignment_for(position: str) -> tuple[int, int, int, int]:
    """Return (Alignment, MarginL, MarginR, MarginV) for ASS Default style.

    Alignment numbers:
       1 = bottom-left, 2 = bottom-center, 3 = bottom-right,
       4 = mid-left,    5 = mid-center,    6 = mid-right,
       7 = top-left,    8 = top-center,    9 = top-right.
    """
    if position == "bottom":
        return (2, 60, 60, 320)
    if position == "side-left":
        return (4, 80, 60, 0)
    if position == "side-right":
        return (6, 60, 80, 0)
    return (5, 60, 60, 0)  # center default


def _ass_header(
    short_form: bool,
    font_name: str,
    color_hex: str,
    position: str,
) -> str:
    primary = _hex_to_ass_bgr(color_hex)
    align, ml, mr, mv = _alignment_for(position)

    base_size = 96 if short_form else 56
    emph_size = int(round(base_size * 1.20))

    # The user spec says: ONE color, no shadow / outline / gradient / stroke.
    # We honor that — Outline=0, Shadow=0, BackColour transparent.
    style = (
        f"Style: Default,{font_name},{base_size},{primary},{primary},{primary},"
        f"&H00000000,1,0,0,0,100,100,0,0,1,0,0,{align},{ml},{mr},{mv},1"
    )
    emphasis = (
        f"Style: Emphasis,{font_name},{emph_size},{primary},{primary},{primary},"
        f"&H00000000,1,0,0,0,100,100,0,0,1,0,0,{align},{ml},{mr},{mv},1"
    )

    return (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "PlayResX: 1080\n"
        "PlayResY: 1920\n"
        "ScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"{style}\n"
        f"{emphasis}\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, "
        "Effect, Text\n"
    )


def _in_window(t: float, windows: Iterable[tuple[float, float]]) -> bool:
    return any(s <= t <= e for s, e in windows)


def build_ass(
    words: Iterable[WordTiming],
    out_path: Path,
    short_form: bool,
    emphasis_words: set[str] | None = None,
    font: str = "Poppins Bold",
    color: str = "white",
    position: str = "center",
    broll_windows: Iterable[tuple[float, float]] = (),
) -> Path:
    """Render captions, one ASS Dialogue per spoken word."""
    if font not in ALLOWED_FONTS:
        font = "Poppins Bold"
    color_hex = ALLOWED_COLORS.get(color.lower(), color if color.startswith("#") else "FFFFFF")
    if position not in ALLOWED_POSITIONS:
        position = "center"

    emphasis_words = {_strip_punct(w).lower() for w in (emphasis_words or set())}
    broll_list = list(broll_windows)

    lines = [_ass_header(short_form, font, color_hex, position)]

    for w in words:
        clean = _strip_punct(w.text).upper()
        if not clean:
            continue
        # Hard rule: no captions during B-roll windows.
        if _in_window((w.start + w.end) / 2, broll_list):
            continue
        style = "Emphasis" if clean.lower() in emphasis_words else "Default"
        lines.append(
            f"Dialogue: 0,{_ts(w.start)},{_ts(w.end)},{style},,0,0,0,,{clean}"
        )

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path
