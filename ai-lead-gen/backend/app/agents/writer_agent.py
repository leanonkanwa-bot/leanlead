"""
Writer Agent
Crafts an empathetic opening DM that acknowledges the lead's pain and ends
with a single discovery question. No pitch, no mention of services.
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
    """
    Returns a ready-to-send DM (under 80 words).

    The message must:
    - Acknowledge the specific pain the person expressed (not generic flattery)
    - Feel like it comes from a real human who noticed their content
    - End with ONE open-ended discovery question that qualifies the lead
    - Never mention coaching, services, offers, or a sales call
    """
    first_name = (lead_data.get("name") or "").split()[0] or "toi"
    pain_points = qualification.get("pain_points", [])
    angle = qualification.get("recommended_angle", "")
    bio = lead_data.get("bio", "")
    posts = lead_data.get("posts_summary", "")

    # Build the most specific context possible for Claude
    pain_context = angle or (pain_points[0] if pain_points else "")
    all_pains = ", ".join(pain_points) if pain_points else "inconnu"

    prompt = f"""You are {coach_name}. You just came across someone's profile and genuinely want to understand their situation better.

Their profile:
- First name: {first_name}
- Bio: {bio}
- Recent content: {posts}
- Pain they're expressing: {all_pains}
- Best angle to open with: {pain_context}

Write a DM that does EXACTLY this:
1. Open with one sentence that shows you genuinely noticed something SPECIFIC they expressed (not "I love your content")
2. Acknowledge their struggle with empathy — make them feel SEEN, not sold to
3. End with ONE open question that invites them to share more about their situation

Hard rules:
- Under 70 words total
- NEVER mention coaching, programs, offers, strategy calls, or any service
- NEVER say "I help people like you" or anything salesy
- No emojis
- Write as a real person, not a marketer
- Use their first name once at the very start

Return ONLY the DM text — nothing else, no quotes, no preamble."""

    msg = _get_client().messages.create(
        model="claude-opus-4-7",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()
