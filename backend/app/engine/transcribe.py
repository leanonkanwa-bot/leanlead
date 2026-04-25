"""Whisper-based transcription with word-level timestamps."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import whisper

from app.core.config import settings


_model = None


def _load_model():
    global _model
    if _model is None:
        _model = whisper.load_model(settings.whisper_model)
    return _model


@dataclass
class Word:
    text: str
    start: float
    end: float


@dataclass
class Segment:
    start: float
    end: float
    text: str
    words: list[Word]


@dataclass
class Transcript:
    language: str
    duration: float
    text: str
    segments: list[Segment]

    def to_dict(self) -> dict[str, Any]:
        return {
            "language": self.language,
            "duration": self.duration,
            "text": self.text,
            "segments": [
                {
                    "start": s.start,
                    "end": s.end,
                    "text": s.text,
                    "words": [asdict(w) for w in s.words],
                }
                for s in self.segments
            ],
        }


def transcribe(video_path: Path) -> Transcript:
    model = _load_model()
    result = model.transcribe(
        str(video_path),
        word_timestamps=True,
        verbose=False,
    )

    segments: list[Segment] = []
    last_end = 0.0
    for seg in result.get("segments", []):
        words = [
            Word(text=w["word"].strip(), start=float(w["start"]), end=float(w["end"]))
            for w in seg.get("words", [])
            if "start" in w and "end" in w
        ]
        segments.append(
            Segment(
                start=float(seg["start"]),
                end=float(seg["end"]),
                text=seg["text"].strip(),
                words=words,
            )
        )
        last_end = max(last_end, float(seg["end"]))

    return Transcript(
        language=result.get("language", "en"),
        duration=last_end,
        text=result.get("text", "").strip(),
        segments=segments,
    )
