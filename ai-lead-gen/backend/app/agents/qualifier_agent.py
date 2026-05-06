"""
Qualifier Agent
Scores a social-media profile 1-10 for fit with a coach's niche/offer using Claude.
"""
import json
import os

import anthropic

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


def qualify_lead(lead_data: dict, coach_niche: str, coach_offer: str) -> dict:
    """
    Returns:
        {
          "score": int (1-10),
          "reason": str,
          "pain_points": list[str],
          "recommended_angle": str,
        }
    """
    prompt = f"""You are an expert lead qualifier for online coaches.

Coach niche: {coach_niche}
Coach offer: {coach_offer}

Analyze this social media profile and score it 1-10 for likelihood of being a great coaching client.

Profile:
- Name: {lead_data.get("name", "Unknown")}
- Handle: @{lead_data.get("handle", "")}
- Platform: {lead_data.get("platform", "instagram")}
- Bio: {lead_data.get("bio", "No bio available")}
- Followers: {lead_data.get("followers", 0):,}
- Posts summary: {lead_data.get("posts_summary", "N/A")}

Scoring guide:
8-10 → Strong fit: pain points visible, engaged audience, niche overlap
5-7  → Moderate fit: some signals, would benefit from nurturing
1-4  → Weak fit: wrong niche, no engagement, or likely bot

Respond ONLY with valid JSON (no markdown):
{{"score": <1-10>, "reason": "<2-3 sentence explanation>", "pain_points": ["<pain1>", "<pain2>"], "recommended_angle": "<what to lead with in outreach>"}}"""

    msg = _get_client().messages.create(
        model="claude-opus-4-7",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text
    start, end = text.find("{"), text.rfind("}") + 1
    return json.loads(text[start:end])
