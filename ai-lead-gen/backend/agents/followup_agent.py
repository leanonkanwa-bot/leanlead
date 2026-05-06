"""
Follow-up Agent
Generates D+2, D+4, and D+7 follow-up messages for leads that haven't replied.
Each touch has a different tone to avoid feeling spammy.
"""
import os

import anthropic

_client: anthropic.Anthropic | None = None

FOLLOWUP_TONES = {
    2: "light bump — short, casual, no pressure. Reference one specific thing from their profile.",
    4: "value-add — share a quick insight or question that's directly relevant to their situation.",
    7: "closing the loop — honest, human, final message. No guilt-tripping. Just close it gently.",
}


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


def generate_followup(
    lead_data: dict,
    original_dm: str,
    coach_name: str,
    coach_offer: str,
    day: int,  # 2, 4, or 7
) -> str:
    """
    Generate a follow-up DM for a lead that hasn't replied.
    day: 2 = D+2, 4 = D+4, 7 = D+7
    """
    tone = FOLLOWUP_TONES.get(day, FOLLOWUP_TONES[7])
    first_name = (lead_data.get("name") or "there").split()[0]

    prompt = f"""You are {coach_name}, following up on an unanswered Instagram DM.

Original message you sent:
"{original_dm}"

Lead profile:
- Name: {first_name}
- Bio: {lead_data.get("bio", "")}
- Platform: {lead_data.get("platform", "instagram")}

This is follow-up #{day // 2} (Day +{day}). Tone: {tone}

Rules:
- Under 60 words
- Do NOT repeat the original DM
- No "Just following up" opener
- No emojis unless it's very natural
- Sound like a real person, not a sequence

Return ONLY the follow-up message text — nothing else."""

    msg = _get_client().messages.create(
        model="claude-opus-4-7",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()
