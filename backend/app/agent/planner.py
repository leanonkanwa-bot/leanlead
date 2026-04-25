"""
The Brain. Calls Claude to turn a transcript + user instructions into an
EditPlan that the FFmpeg engine can execute.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

from anthropic import Anthropic

from app.agent.rules import system_prompt
from app.core.config import settings


FormatHint = Literal["short", "long", "auto"]


@dataclass
class EditPlan:
    raw: dict[str, Any]

    @property
    def format(self) -> str:
        return self.raw.get("format", "short")

    @property
    def keep_segments(self) -> list[dict[str, Any]]:
        return self.raw.get("keep_segments", [])

    @property
    def zoom_plan(self) -> list[dict[str, Any]]:
        return self.raw.get("zoom_plan", [])

    @property
    def caption_emphasis_words(self) -> list[str]:
        return [w.lower() for w in self.raw.get("caption_emphasis_words", [])]

    @property
    def broll_suggestions(self) -> list[dict[str, Any]]:
        return self.raw.get("broll_suggestions", [])

    @property
    def packaging(self) -> dict[str, Any]:
        return self.raw.get("packaging", {})


def _decide_format(duration_s: float, hint: FormatHint) -> str:
    if hint in ("short", "long"):
        return hint
    return "short" if duration_s <= 90 else "long"


def _client() -> Anthropic:
    return Anthropic(api_key=settings.anthropic_api_key)


def plan_edit(
    transcript: dict[str, Any],
    user_instructions: str,
    format_hint: FormatHint = "auto",
) -> EditPlan:
    """
    Ask Claude to produce an edit plan for the given transcript.
    Returns an EditPlan with the raw JSON the model emitted.
    """
    duration = float(transcript.get("duration", 0.0))
    fmt = _decide_format(duration, format_hint)

    user_msg = {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": (
                    f"FORMAT TARGET: {fmt}\n"
                    f"DURATION: {duration:.2f}s\n"
                    f"LANGUAGE: {transcript.get('language', 'en')}\n\n"
                    f"USER INSTRUCTIONS:\n{user_instructions or '(none — apply default high-retention edit)'}\n\n"
                    "TRANSCRIPT WITH WORD TIMESTAMPS (JSON):\n"
                    f"{json.dumps(transcript, ensure_ascii=False)}\n\n"
                    "Return the JSON edit plan now. No prose. Just the JSON."
                ),
            }
        ],
    }

    resp = _client().messages.create(
        model=settings.anthropic_model,
        max_tokens=8000,
        system=system_prompt(format_hint=fmt),
        messages=[user_msg],
    )

    text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    plan = _extract_json(text)
    plan.setdefault("format", fmt)
    return EditPlan(raw=plan)


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.rsplit("```", 1)[0]
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"Agent did not return JSON. Got:\n{text[:500]}")
    return json.loads(text[start : end + 1])
