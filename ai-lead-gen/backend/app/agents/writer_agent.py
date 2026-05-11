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


def _build_social_proof_block(testimonials: list[dict] | None, pain_context: str) -> str:
    """Pick the most relevant testimonial and format it for injection."""
    if not testimonials:
        return ""
    # Use the first testimonial as a fallback; ideally Claude picks the best match
    t = testimonials[0]
    name = t.get("name", "un client")
    situation = t.get("situation", "")
    result = t.get("result", "")
    if not situation and not result:
        return ""
    return f'\nSocial proof (weave naturally if relevant — ONE brief mention max): "{name} était dans une situation similaire ({situation}) — {result}"'


def write_outreach_message(
    lead_data: dict,
    coach_name: str,
    coach_niche: str,
    coach_offer: str,
    qualification: dict,
    language: str = "fr",
    testimonials: list[dict] | None = None,
) -> str:
    """
    Returns a ready-to-send DM in the lead's language.
    Optionally weaves in a matching social proof testimonial.
    """
    first_name = (lead_data.get("name") or "").split()[0] or "toi"
    pain_context = qualification.get("recommended_angle", "") or \
                   (qualification.get("pain_points", [""])[0] if qualification.get("pain_points") else "")
    all_pains = ", ".join(qualification.get("pain_points", [])) or "unknown"
    objection = qualification.get("predicted_objection", "")
    bio = lead_data.get("bio", "")
    posts = lead_data.get("posts_summary", "")
    platform = lead_data.get("platform", "instagram")

    lang_name, lang_note = _LANGUAGE_INSTRUCTIONS.get(language, _LANGUAGE_INSTRUCTIONS["fr"])
    platform_style = _PLATFORM_STYLE.get(platform, _PLATFORM_STYLE["instagram"])
    proof_block = _build_social_proof_block(testimonials, pain_context)
    objection_block = f"\nPredicted objection to pre-empt subtly (don't name it directly): {objection}" if objection else ""

    prompt = f"""You are {coach_name}. Write a DM to {first_name} in {lang_name}. {lang_note}

Their profile:
- Bio: {bio}
- Recent content: {posts}
- Pain they express: {all_pains}
- Best angle: {pain_context}{proof_block}{objection_block}

Platform: {platform} — Style: {platform_style}

Rules:
1. Open with ONE sentence showing you noticed something SPECIFIC they expressed
2. Acknowledge their struggle with empathy — make them feel SEEN
3. If a social proof is provided, reference it naturally in ONE sentence ("J'ai aidé quelqu'un dans ta situation exacte…")
4. If a predicted objection is provided, subtly dissolve it without naming it
5. End with ONE open question inviting them to share more
6. NEVER mention coaching, programs, offers, calls, or services explicitly
7. NEVER say "I help people like you"
8. No emojis. Write as a real human, not a marketer.
9. Use their first name once at the start.

Return ONLY the DM text."""

    msg = _get_client().messages.create(
        model="claude-opus-4-7",
        max_tokens=300,
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
    testimonials: list[dict] | None = None,
) -> tuple[str, str]:
    """
    Returns (variant_a, variant_b):
    Variant A: empathy + social proof + objection pre-emption
    Variant B: curiosity angle (dream/goal)
    """
    first_name = (lead_data.get("name") or "").split()[0] or "toi"
    pain = qualification.get("recommended_angle", "") or \
           (qualification.get("pain_points", [""])[0] if qualification.get("pain_points") else "")
    objection = qualification.get("predicted_objection", "")
    bio = lead_data.get("bio", "")
    posts = lead_data.get("posts_summary", "")
    platform = lead_data.get("platform", "instagram")

    lang_name, lang_note = _LANGUAGE_INSTRUCTIONS.get(language, _LANGUAGE_INSTRUCTIONS["fr"])
    platform_style = _PLATFORM_STYLE.get(platform, _PLATFORM_STYLE["instagram"])
    proof_block = _build_social_proof_block(testimonials, pain)
    objection_block = f"\nPredicted objection to dissolve subtly in variant A: {objection}" if objection else ""

    prompt = f"""You are {coach_name}. Generate TWO different DMs to {first_name} in {lang_name}. {lang_note}

Profile:
- Bio: {bio}
- Content: {posts}
- Pain: {pain}{proof_block}{objection_block}

Platform: {platform} — Style: {platform_style}

VARIANT A — Empathy + proof: Acknowledge their struggle, reference the social proof naturally if available ("J'ai aidé quelqu'un dans ta situation exacte…"), subtly dissolve their predicted objection.
VARIANT B — Curiosity: Ask about their dream/goal, create intrigue about what's possible.

Both variants must:
- Be under 70 words
- NEVER mention coaching, programs, or services explicitly
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
