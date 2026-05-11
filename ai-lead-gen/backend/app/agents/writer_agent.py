"""
Writer Agent — v2
- Multi-language DM (writes in lead's detected language)
- A/B variant generation (two angles per lead)
- Warming comment generation (genuine, non-generic)
"""
import os

import anthropic

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


_LANGUAGE_INSTRUCTIONS = {
    "fr": ("français", "Tutoie-le(la) naturellement."),
    "en": ("English", "Use natural first-name basis."),
    "es": ("español", "Tutéale naturalmente."),
    "pt": ("português", "Use 'você' naturalmente."),
    "ar": ("العربية", "اكتب بشكل طبيعي وودي."),
    "other": ("English", "Use natural first-name basis."),
}

_PLATFORM_STYLE = {
    "instagram": "Casual, warm, under 70 words.",
    "tiktok": "Very casual, Gen-Z friendly, under 60 words.",
    "linkedin": "Professional but human, under 60 words. No slang.",
    "twitter": "Punchy, direct, under 50 words.",
    "reddit": "Low-key, genuine, under 70 words. No sales energy.",
}


def write_outreach_message(
    lead_data: dict,
    coach_name: str,
    coach_niche: str,
    coach_offer: str,
    qualification: dict,
    language: str = "fr",
) -> str:
    """
    Returns a ready-to-send DM in the lead's language.
    Never mentions coaching, services, or a sales call.
    """
    first_name = (lead_data.get("name") or "").split()[0] or "toi"
    pain_context = qualification.get("recommended_angle", "") or \
                   (qualification.get("pain_points", [""])[0] if qualification.get("pain_points") else "")
    all_pains = ", ".join(qualification.get("pain_points", [])) or "unknown"
    bio = lead_data.get("bio", "")
    posts = lead_data.get("posts_summary", "")
    platform = lead_data.get("platform", "instagram")

    lang_name, lang_note = _LANGUAGE_INSTRUCTIONS.get(language, _LANGUAGE_INSTRUCTIONS["fr"])
    platform_style = _PLATFORM_STYLE.get(platform, _PLATFORM_STYLE["instagram"])

    prompt = f"""You are {coach_name}. Write a DM to {first_name} in {lang_name}. {lang_note}

Their profile:
- Bio: {bio}
- Recent content: {posts}
- Pain they express: {all_pains}
- Best angle: {pain_context}

Platform: {platform} — Style: {platform_style}

Rules:
1. Open with ONE sentence showing you noticed something SPECIFIC they expressed
2. Acknowledge their struggle with empathy — make them feel SEEN
3. End with ONE open question inviting them to share more
4. NEVER mention coaching, programs, offers, calls, or services
5. NEVER say "I help people like you"
6. No emojis. Write as a real human, not a marketer.
7. Use their first name once at the start.

Return ONLY the DM text."""

    msg = _get_client().messages.create(
        model="claude-opus-4-7",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


def write_ab_variants(
    lead_data: dict,
    coach_name: str,
    coach_niche: str,
    coach_offer: str,
    qualification: dict,
    language: str = "fr",
) -> tuple[str, str]:
    """
    Returns (variant_a, variant_b) — two different DM angles for A/B testing.
    Variant A: empathy angle (acknowledge the pain)
    Variant B: curiosity angle (ask about their goal/vision)
    """
    first_name = (lead_data.get("name") or "").split()[0] or "toi"
    pain = qualification.get("recommended_angle", "") or \
           (qualification.get("pain_points", [""])[0] if qualification.get("pain_points") else "")
    bio = lead_data.get("bio", "")
    posts = lead_data.get("posts_summary", "")
    platform = lead_data.get("platform", "instagram")

    lang_name, lang_note = _LANGUAGE_INSTRUCTIONS.get(language, _LANGUAGE_INSTRUCTIONS["fr"])
    platform_style = _PLATFORM_STYLE.get(platform, _PLATFORM_STYLE["instagram"])

    prompt = f"""You are {coach_name}. Generate TWO different DM openings to {first_name} in {lang_name}. {lang_note}

Profile:
- Bio: {bio}
- Content: {posts}
- Pain: {pain}

Platform: {platform} — Style: {platform_style}

VARIANT A — Empathy angle: Acknowledge their struggle, make them feel understood.
VARIANT B — Curiosity angle: Ask about their dream/goal, create intrigue about possibility.

Both variants must:
- Be under 70 words
- NEVER mention coaching, programs, or services
- Feel human and genuine
- End with ONE open question

Return ONLY valid JSON (no markdown):
{{"variant_a": "<DM text>", "variant_b": "<DM text>"}}"""

    msg = _get_client().messages.create(
        model="claude-opus-4-7",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text
    start, end = text.find("{"), text.rfind("}") + 1
    data = {"variant_a": "", "variant_b": ""}
    try:
        data = {**data, **__import__("json").loads(text[start:end])}
    except Exception:
        pass
    return data["variant_a"].strip(), data["variant_b"].strip()


def write_warming_comment(
    lead_data: dict,
    coach_name: str,
    qualification: dict,
    language: str = "fr",
) -> str:
    """
    Generates a genuine, non-generic comment on one of the lead's recent posts.
    To be posted BEFORE sending the DM to warm up the relationship.
    Under 20 words — sounds like a real person, not a bot.
    """
    first_name = (lead_data.get("name") or "").split()[0] or ""
    bio = lead_data.get("bio", "")
    posts = lead_data.get("posts_summary", "")
    pain = qualification.get("recommended_angle", "") or \
           (qualification.get("pain_points", [""])[0] if qualification.get("pain_points") else "")

    lang_name, lang_note = _LANGUAGE_INSTRUCTIONS.get(language, _LANGUAGE_INSTRUCTIONS["fr"])

    prompt = f"""Write ONE short comment in {lang_name} to leave on {first_name}'s recent post. {lang_note}

What they post about: {posts or bio}
Their main struggle: {pain}

Rules:
- Under 20 words
- Genuine, not generic ("super post!" is forbidden)
- Reference something specific from their content
- Sounds like a real person who resonated with what they shared
- NO emojis, no marketing language, no questions
- This comment is to build recognition BEFORE a DM — keep it human

Return ONLY the comment text."""

    msg = _get_client().messages.create(
        model="claude-opus-4-7",
        max_tokens=80,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()
