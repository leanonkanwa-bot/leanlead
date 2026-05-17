"""
Writer Agent
Crafts a short, personalized first-touch message for a qualified lead using Claude.
Platform-aware: DM style for Instagram/TikTok, connection note for LinkedIn,
Twitter DM for Twitter/X, Reddit DM for Reddit.
"""
import os

import anthropic

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


_PLATFORM_INSTRUCTIONS = {
    "instagram": (
        "Instagram DM",
        "Under 80 words. Conversational, no emojis. Opens with a genuine observation about their content. "
        "Hints at a solution without pitching. Ends with one low-commitment question.",
    ),
    "tiktok": (
        "TikTok DM",
        "Under 80 words. Casual and direct, reference their TikTok content or vibe. "
        "No emojis. One soft question at the end.",
    ),
    "linkedin": (
        "LinkedIn connection request note",
        "Under 60 words. Professional but warm. Reference something specific about their profile or role. "
        "No pitch — just genuine curiosity. Ends with a question or reason to connect.",
    ),
    "twitter": (
        "Twitter/X DM",
        "Under 60 words. Conversational, reference a specific tweet or topic they post about. "
        "No emojis. One low-commitment question.",
    ),
    "reddit": (
        "Reddit DM",
        "Under 80 words. Friendly and community-focused. Reference their posts/comments in the subreddit. "
        "No hard pitch. Ends with an open question.",
    ),
}


def write_outreach_message(
    lead_data: dict,
    coach_name: str,
    coach_niche: str,
    coach_offer: str,
    qualification: dict,
) -> str:
    """Returns a ready-to-send message string."""
    platform = (lead_data.get("platform") or "instagram").lower()
    message_type, style_rules = _PLATFORM_INSTRUCTIONS.get(platform, _PLATFORM_INSTRUCTIONS["instagram"])

    pain_points = ", ".join(qualification.get("pain_points", []))
    angle = qualification.get("recommended_angle", "")
    first_name = (lead_data.get("name") or "there").split()[0]

    prompt = f"""You are an expert at writing {message_type}s that book coaching calls without sounding salesy.

Coach: {coach_name}
Coach niche: {coach_niche}
Coach offer: {coach_offer}

Lead:
- First name: {first_name}
- Platform: {platform}
- Bio: {lead_data.get("bio", "")}
- Posts/activity: {lead_data.get("posts_summary", "")}
- Pain points detected: {pain_points}
- Best opening angle: {angle}

Write a {message_type} that:
1. Opens with a genuine, specific observation about their content, bio, or activity (NOT "I love your content!")
2. Names one pain point naturally (never use the word "pain point")
3. Hints at a solution without pitching
4. Ends with one low-commitment question

Style rules: {style_rules}
- Use their first name once at the start
- No hard sell, no "I help people like you"
- No fake urgency

Return ONLY the message text — nothing else."""

    msg = _get_client().messages.create(
        model="claude-opus-4-7",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()
