"""Word-level transcription powered by faster-whisper.

We use faster-whisper (CTranslate2 backend) instead of openai-whisper
(PyTorch backend) because:

  - No torch dependency → ~700 MB less RAM, ~700 MB less image size.
  - int8 quantization keeps the same word-level quality at ~1/4 the
    memory of float32. This is what lets the app survive on a 1 GB dyno.
  - Faster on CPU (typically 3–4×).

Public surface stays identical: `transcribe(path) -> Transcript` with
`segments[i].words[j].{text,start,end}`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.core.config import settings


_model = None


def _load_model():
    """Lazy import + load. Keeps the heavy imports off the server's
    cold-start path so /healthz responds within the cloud platform's window."""
    global _model
    if _model is None:
        from faster_whisper import WhisperModel  # noqa: PLC0415 — intentional lazy import

        _model = WhisperModel(
            settings.whisper_model,
            device="cpu",
            compute_type="int8",
        )
    return _model


def unload_model() -> None:
    """Release the Whisper model and reclaim ~250 MB of RAM. Call this
    between transcription and rendering so ffmpeg has room to encode on
    a 1 GB dyno."""
    global _model
    _model = None
    import gc  # noqa: PLC0415
    gc.collect()


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
    seg_iter, info = model.transcribe(  # type: ignore[union-attr]
        str(video_path),
        word_timestamps=True,
        beam_size=1,        # save RAM + CPU vs the default beam_size=5
        vad_filter=True,    # cut leading/trailing silence
    )

    segments: list[Segment] = []
    last_end = 0.0
    for seg in seg_iter:
        words = [
            Word(
                text=(w.word or "").strip(),
                start=float(w.start),
                end=float(w.end),
            )
            for w in (seg.words or [])
            if w.start is not None and w.end is not None
        ]
        segments.append(
            Segment(
                start=float(seg.start),
                end=float(seg.end),
                text=(seg.text or "").strip(),
                words=words,
            )
        )
        last_end = max(last_end, float(seg.end))

    full_text = " ".join(s.text for s in segments).strip()

    return Transcript(
        language=getattr(info, "language", "en") or "en",
        duration=last_end,
        text=full_text,
        segments=segments,
    )
