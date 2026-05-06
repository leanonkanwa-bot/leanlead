"""
Writer Agent
Crafts a short, personalized DM for a qualified lead using Claude.
"""
import os

import anthropic

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


def write_outreach_message(
    lead_data: dict,
    coach_name: str,
    coach_niche: str,
    coach_offer: str,
    qualification: dict,
) -> str:
    """Returns a ready-to-send DM string (under 100 words)."""
    pain_points = ", ".join(qualification.get("pain_points", []))
    angle = qualification.get("recommended_angle", "")

    prompt = f"""You are an expert at writing Instagram DMs that book coaching calls without sounding salesy.

Coach: {coach_name}
Coach niche: {coach_niche}
Coach offer: {coach_offer}

Lead:
- First name: {lead_data.get("name", "").split()[0] if lead_data.get("name") else "there"}
- Bio: {lead_data.get("bio", "")}
- Pain points: {pain_points}
- Best opening angle: {angle}

Write a DM that:
1. Opens with a genuine, specific observation about their content or bio (NOT "I love your content!")
2. Names one pain point naturally (never use the word "pain point")
3. Hints at a solution without pitching
4. Ends with one low-commitment question

Rules:
- Under 80 words
- Conversational, no emojis
- Use their first name once at the start
- No hard sell, no "I help people like you"

Return ONLY the DM text — nothing else."""

    msg = _get_client().messages.create(
        model="claude-opus-4-7",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()
