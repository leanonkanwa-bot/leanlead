"""
Build .ass subtitle files from word-level timestamps.
Short form  -> big centered captions, 1–4 words per card, emphasis colored.
Long form   -> smaller, lower-third, 5–9 words, soft.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


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


def _ass_header(short_form: bool) -> str:
    if short_form:
        style = (
            "Style: Default,Inter,72,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,"
            "1,0,0,0,100,100,0,0,1,4,2,2,40,40,150,1"
        )
        emphasis = (
            "Style: Emphasis,Inter,80,&H0000F2FF,&H000000FF,&H00000000,&H64000000,"
            "1,0,0,0,100,100,0,0,1,5,2,2,40,40,150,1"
        )
    else:
        style = (
            "Style: Default,Inter,42,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,"
            "0,0,0,0,100,100,0,0,1,2,1,2,80,80,90,1"
        )
        emphasis = (
            "Style: Emphasis,Inter,46,&H0000F2FF,&H000000FF,&H00000000,&H80000000,"
            "1,0,0,0,100,100,0,0,1,3,1,2,80,80,90,1"
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


def _group_words(words: list[WordTiming], max_words: int) -> list[list[WordTiming]]:
    cards: list[list[WordTiming]] = []
    cur: list[WordTiming] = []
    for w in words:
        if not cur:
            cur.append(w)
            continue
        gap = w.start - cur[-1].end
        if len(cur) >= max_words or gap > 0.6:
            cards.append(cur)
            cur = [w]
        else:
            cur.append(w)
    if cur:
        cards.append(cur)
    return cards


def build_ass(
    words: Iterable[WordTiming],
    out_path: Path,
    short_form: bool,
    emphasis_words: set[str] | None = None,
) -> Path:
    emphasis_words = {w.lower().strip(".,!?;:") for w in (emphasis_words or set())}
    word_list = [w for w in words if w.text.strip()]
    cards = _group_words(word_list, max_words=3 if short_form else 8)

    lines = [_ass_header(short_form)]
    for card in cards:
        if not card:
            continue
        start = card[0].start
        end = card[-1].end
        is_emphasis = any(
            w.text.lower().strip(".,!?;:") in emphasis_words for w in card
        )
        style = "Emphasis" if is_emphasis else "Default"
        text = " ".join(w.text for w in card).upper() if short_form else " ".join(
            w.text for w in card
        )
        text = text.replace("\n", " ").strip()
        lines.append(
            f"Dialogue: 0,{_ts(start)},{_ts(end)},{style},,0,0,0,,{text}"
        )

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path
