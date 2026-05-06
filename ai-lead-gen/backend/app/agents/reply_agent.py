"""
Reply Agent
Generates a contextual follow-up reply that moves the conversation toward a booked call.
"""
import os

import anthropic

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


def generate_reply(
    lead_reply: str,
    conversation_history: str,
    coach_name: str,
    coach_offer: str,
    calendly_link: str,
) -> str:
    """Returns the next reply the coach should send."""
    prompt = f"""You are {coach_name}, an online coach having a DM conversation with a potential client.

Your offer: {coach_offer}
Your booking link: {calendly_link}

Conversation so far:
{conversation_history}

Their latest message:
"{lead_reply}"

Write a reply that:
1. Responds genuinely to what they said (no copy-paste vibes)
2. Deepens rapport or addresses their objection
3. If they show buying intent → share the Calendly link naturally
4. If they're unsure → ask one targeted discovery question to surface the real pain

Rules:
- Under 80 words
- Sound like a real human, not a sales script
- Only share the Calendly link when there's clear interest
- No emojis, no "Great question!"

Return ONLY the reply text — nothing else."""

    msg = _get_client().messages.create(
        model="claude-opus-4-7",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()
