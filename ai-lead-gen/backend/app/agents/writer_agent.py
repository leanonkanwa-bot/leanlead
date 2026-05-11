"""
Writer Agent — v3
- Multi-language DM (writes in lead's detected language)
- A/B variant generation (two angles per lead)
- Warming comment generation (genuine, non-generic)
- Content mirroring (matches lead's exact writing style)
- Social proof injection (matching testimonial)
- Objection pre-emption
- AI Coach Persona Builder (DMs sound like the coach)
- Price-tier adaptive messaging (premium vs standard)
- Trust-velocity adaptive approach (direct offer vs nurture sequence)
"""
import os
import re

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


_coach_persona_cache: dict[int, str] = {}


def build_coach_persona(coach_id: int, coach_name: str, coach_niche: str, coach_offer: str,
                        testimonials: list[dict] | None = None) -> str:
    """
    Feature 7: AI Coach Persona Builder.
    Builds a reusable voice/style guide so every DM sounds like the coach wrote it personally.
    Cached per coach_id to avoid repeated API calls.
    """
    if coach_id in _coach_persona_cache:
        return _coach_persona_cache[coach_id]

    testimonial_examples = ""
    if testimonials:
        examples = []
        for t in testimonials[:3]:
            examples.append(f"- Client: {t.get('name','')}, Situation: {t.get('situation','')}, Result: {t.get('result','')}")
        testimonial_examples = "\nReal transformations this coach achieves:\n" + "\n".join(examples)

    prompt = f"""Analyze this coach's profile and write a concise VOICE & STYLE GUIDE (under 80 words) that captures how they communicate in DMs.

Coach name: {coach_name}
Niche: {coach_niche}
Offer: {coach_offer}{testimonial_examples}

Based on their niche and offer, describe:
1. Vocabulary they likely use (3-4 specific words/phrases)
2. Tone (warm/direct/inspirational/no-nonsense?)
3. One sentence they would NEVER say
4. Their unique coaching promise in 10 words

Return ONLY the style guide text, no headers."""

    try:
        msg = _get_client().messages.create(
            model="claude-opus-4-7",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )
        persona = msg.content[0].text.strip()
    except Exception:
        persona = f"Write as {coach_name}: warm, direct, focused on {coach_niche}. Genuine and human."

    _coach_persona_cache[coach_id] = persona
    return persona


def _get_price_strategy(price_tier: str) -> str:
    """Feature 9: Price-adaptive DM strategy."""
    if price_tier == "premium":
        return "This prospect shows premium spending signals. Position transformation as an exclusive investment, not a cost. Match their level of ambition."
    if price_tier == "budget":
        return "This prospect may have affordability concerns. Focus entirely on the transformation, never hint at price. Build desire first, discuss investment much later."
    return ""


def _get_trust_strategy(trust_velocity: str) -> str:
    """Feature 10: Trust-velocity adaptive approach."""
    if trust_velocity == "fast":
        return "This is a FAST TRUSTER — decisive, action-oriented. End with a clear but soft invitation. They respond to directness. Do NOT over-explain."
    if trust_velocity == "slow":
        return "This is a SLOW TRUSTER — analytical, needs time. Ask a thoughtful open question only. Do NOT suggest any action or meeting. Just start a conversation."
    return ""


def _detect_writing_style(bio: str, posts: str) -> str:
    """
    Analyze lead's writing style to mirror in the DM.
    Returns a one-line instruction for the writer prompt.
    """
    text = f"{bio} {posts}"
    if not text.strip():
        return ""

    emoji_count = len(re.findall(r'[\U00010000-\U0010ffff]|[\U00002600-\U000027BF]', text))
    word_count = max(len(text.split()), 1)
    emoji_density = emoji_count / word_count

    # Slang/informal markers (FR + EN)
    slang = bool(re.search(r'\b(wsh|frr|ouf|bg|tkt|mdr|lol|omg|ngl|tbh|fr fr|imo|bruh|fam)\b', text, re.IGNORECASE))
    formal = bool(re.search(r'\b(bonjour|cordialement|veuillez|je vous|madame|monsieur|dear|sincerely|regards)\b', text, re.IGNORECASE))
    caps = bool(re.search(r'[A-Z]{4,}', text))  # ALL CAPS emphasis
    ellipsis = text.count('...') + text.count('…') > 1
    exclamation = text.count('!') > 2

    if formal:
        return "Mirror their formal style: use 'vous', full sentences, no contractions, professional tone."
    if slang:
        return "Mirror their slang: use informal speech, match their exact vocabulary and abbreviations, be casual."
    style_notes = []
    if emoji_density > 0.1:
        style_notes.append("use 1-2 relevant emojis")
    if caps:
        style_notes.append("occasional CAPS for emphasis")
    if ellipsis:
        style_notes.append("trailing ellipsis for effect…")
    if exclamation:
        style_notes.append("enthusiastic punctuation!")
    if style_notes:
        return f"Mirror their style: {', '.join(style_notes)}."
    return "Casual, natural tone — no emojis, no formality."


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
    coach_id: int | None = None,
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

    price_tier = qualification.get("price_tier", "mid")
    trust_velocity = qualification.get("trust_velocity", "unknown")
    lang_name, lang_note = _LANGUAGE_INSTRUCTIONS.get(language, _LANGUAGE_INSTRUCTIONS["fr"])
    platform_style = _PLATFORM_STYLE.get(platform, _PLATFORM_STYLE["instagram"])
    proof_block = _build_social_proof_block(testimonials, pain_context)
    objection_block = f"\nPredicted objection to pre-empt subtly (don't name it directly): {objection}" if objection else ""
    style_note = _detect_writing_style(bio, posts)
    style_block = f"\nContent mirroring: {style_note}" if style_note else ""
    price_block = f"\nPricing strategy: {_get_price_strategy(price_tier)}" if price_tier != "mid" else ""
    trust_block = f"\nTrust strategy: {_get_trust_strategy(trust_velocity)}" if trust_velocity != "unknown" else ""
    persona_block = ""
    if coach_id:
        persona = build_coach_persona(coach_id, coach_name, coach_niche, coach_offer, testimonials)
        persona_block = f"\nYour voice & style: {persona}"

    prompt = f"""You are {coach_name}. Write a DM to {first_name} in {lang_name}. {lang_note}

Their profile:
- Bio: {bio}
- Recent content: {posts}
- Pain they express: {all_pains}
- Best angle: {pain_context}{proof_block}{objection_block}{style_block}{persona_block}{price_block}{trust_block}

Platform: {platform} — Style: {platform_style}

Rules:
1. Open with ONE sentence showing you noticed something SPECIFIC they expressed
2. Acknowledge their struggle with empathy — make them feel SEEN
3. If a social proof is provided, reference it naturally in ONE sentence ("J'ai aidé quelqu'un dans ta situation exacte…")
4. If a predicted objection is provided, subtly dissolve it without naming it
5. MIRROR their writing style exactly as instructed — match their vocabulary, tone, emoji usage
6. Apply trust strategy for the ending (fast truster: soft CTA, slow truster: open question only)
7. NEVER mention coaching, programs, offers, calls, or services explicitly
8. NEVER say "I help people like you"
9. Use their first name once at the start. Sound exactly like the voice guide.

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
    coach_id: int | None = None,
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
    price_tier = qualification.get("price_tier", "mid")
    trust_velocity = qualification.get("trust_velocity", "unknown")
    bio = lead_data.get("bio", "")
    posts = lead_data.get("posts_summary", "")
    platform = lead_data.get("platform", "instagram")

    lang_name, lang_note = _LANGUAGE_INSTRUCTIONS.get(language, _LANGUAGE_INSTRUCTIONS["fr"])
    platform_style = _PLATFORM_STYLE.get(platform, _PLATFORM_STYLE["instagram"])
    proof_block = _build_social_proof_block(testimonials, pain)
    objection_block = f"\nPredicted objection to dissolve subtly in variant A: {objection}" if objection else ""
    style_note = _detect_writing_style(bio, posts)
    style_block = f"\nContent mirroring: {style_note}" if style_note else ""
    price_block = f"\nPricing strategy: {_get_price_strategy(price_tier)}" if price_tier != "mid" else ""
    trust_block = f"\nTrust strategy: {_get_trust_strategy(trust_velocity)}" if trust_velocity != "unknown" else ""
    persona_block = ""
    if coach_id:
        persona = build_coach_persona(coach_id, coach_name, coach_niche, coach_offer, testimonials)
        persona_block = f"\nYour voice & style: {persona}"

    prompt = f"""You are {coach_name}. Generate TWO different DMs to {first_name} in {lang_name}. {lang_note}

Profile:
- Bio: {bio}
- Content: {posts}
- Pain: {pain}{proof_block}{objection_block}{style_block}{persona_block}{price_block}{trust_block}

Platform: {platform} — Style: {platform_style}

VARIANT A — Empathy + proof: Acknowledge their struggle, reference the social proof if available, subtly dissolve their predicted objection. Apply trust strategy for closing.
VARIANT B — Curiosity: Ask about their dream/goal, create intrigue about what's possible. Adapt for their price tier.

Both variants must:
- Be under 70 words
- MIRROR their writing style exactly as instructed
- Sound exactly like the coach's voice guide
- NEVER mention coaching, programs, or services explicitly
- Feel human and genuine

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


def write_reengagement_message(
    lead_data: dict,
    coach_name: str,
    coach_niche: str,
    days_silent: int,
    language: str = "fr",
    coach_id: int | None = None,
) -> str:
    """
    Feature 6: Predictive Churn Prevention.
    Generates a re-engagement DM for a lead going cold.
    Designed to reignite the conversation without being pushy.
    """
    first_name = (lead_data.get("name") or "").split()[0] or "toi"
    pain = lead_data.get("recommended_angle") or lead_data.get("notes") or ""
    bio = lead_data.get("bio", "")
    lang_name, lang_note = _LANGUAGE_INSTRUCTIONS.get(language, _LANGUAGE_INSTRUCTIONS["fr"])

    persona_block = ""
    if coach_id:
        persona = build_coach_persona(coach_id, coach_name, coach_niche, "", None)
        persona_block = f"\nYour voice: {persona}"

    prompt = f"""You are {coach_name}. You sent a DM to {first_name} about {days_silent} days ago but got no reply.
Write a SHORT re-engagement message in {lang_name}. {lang_note}

Their context: {bio or pain}{persona_block}

Rules:
- Under 40 words
- Do NOT reference the previous message
- Show you're thinking of them because of something specific (not generic "just checking in")
- No pressure, no selling, no urgency
- One question that's easy to answer (yes/no or one word)
- Sound like a human who genuinely cares, not a salesperson

Return ONLY the message text."""

    msg = _get_client().messages.create(
        model="claude-opus-4-7",
        max_tokens=120,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


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


def write_sales_script(
    lead_data: dict,
    coach_name: str,
    coach_niche: str,
    coach_offer: str,
    coach_price: float | None,
    qualification: dict,
    language: str = "fr",
    coach_id: int | None = None,
) -> dict:
    """
    Feature 4: Sales Script Generation.
    Generates a complete personalized call script for this lead.
    Agencies charge €500 for a generic script. This is personalized to each lead.
    Returns: {opener, objections: [{objection, response}], closing, followup_sequence}
    """
    first_name = (lead_data.get("name") or "").split()[0] or "votre prospect"
    pain = qualification.get("recommended_angle", "") or \
           (qualification.get("pain_points", [""])[0] if qualification.get("pain_points") else "")
    objection = qualification.get("predicted_objection", "")
    all_pains = ", ".join(qualification.get("pain_points", [])[:5]) or "unknown"
    trust_velocity = qualification.get("trust_velocity", "unknown")
    price_tier = qualification.get("price_tier", "mid")
    comm_style = (qualification.get("psychographic") or {}).get("communication_style", "casual")

    lang_name, lang_note = _LANGUAGE_INSTRUCTIONS.get(language, _LANGUAGE_INSTRUCTIONS["fr"])

    persona_block = ""
    if coach_id:
        persona = build_coach_persona(coach_id, coach_name, coach_niche, coach_offer)
        persona_block = f"\nYour voice: {persona}"

    price_block = f" Their budget tier: {price_tier}." if price_tier else ""
    trust_block = (
        " They're a FAST TRUSTER — be direct and decisive."
        if trust_velocity == "fast"
        else " They're a SLOW TRUSTER — be patient, ask questions, don't rush."
        if trust_velocity == "slow"
        else ""
    )

    prompt = f"""You are {coach_name}. Generate a complete personalized sales call script for {first_name} in {lang_name}.{persona_block}

Lead profile:
- Their main pain: {pain}
- All pain points: {all_pains}
- Predicted objection: {objection}
- Communication style: {comm_style}{price_block}{trust_block}
- Coach offer: {coach_offer}
{f'- Price: €{int(coach_price)}' if coach_price else ''}

Return ONLY valid JSON:
{{
  "opener": "<personalized call opener — reference something specific from their pain, under 30 words>",
  "discovery_questions": [
    "<3 deep questions to open them up — each specific to their pain, not generic>"
  ],
  "objections": [
    {{"objection": "<exact objection text — use predicted objection first>", "response": "<perfect empathetic 1-2 sentence response>"}},
    {{"objection": "<second common objection for this niche>", "response": "<response>"}},
    {{"objection": "<price objection>", "response": "<response that reframes investment>"}}
  ],
  "closing": "<closing language that matches their style — direct for fast trustors, inviting for slow>",
  "post_call_followup": "<what to send within 2 hours of the call — personalized to their situation>"
}}"""

    msg = _get_client().messages.create(
        model="claude-opus-4-7",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text
    start, end = text.find("{"), text.rfind("}") + 1
    import json as _json
    try:
        return _json.loads(text[start:end])
    except Exception:
        return {"opener": "", "discovery_questions": [], "objections": [], "closing": "", "post_call_followup": ""}


def write_nurture_sequence(
    lead_data: dict,
    coach_name: str,
    coach_niche: str,
    coach_offer: str,
    qualification: dict,
    language: str = "fr",
    num_messages: int = 5,
    coach_id: int | None = None,
) -> list[dict]:
    """
    Feature 8: Automated Nurture Sequences.
    Generates a complete personalized multi-touch sequence — never the same message twice.
    Each message references their specific situation. Adapts escalation based on stage.
    Returns list of {day, trigger, message, angle}
    """
    first_name = (lead_data.get("name") or "").split()[0] or "toi"
    pain = qualification.get("recommended_angle", "") or \
           (qualification.get("pain_points", [""])[0] if qualification.get("pain_points") else "")
    all_pains = ", ".join(qualification.get("pain_points", [])[:5]) or pain
    trust_velocity = qualification.get("trust_velocity", "unknown")
    lang_name, lang_note = _LANGUAGE_INSTRUCTIONS.get(language, _LANGUAGE_INSTRUCTIONS["fr"])
    platform = lead_data.get("platform", "instagram")
    platform_style = _PLATFORM_STYLE.get(platform, _PLATFORM_STYLE["instagram"])

    persona_block = ""
    if coach_id:
        persona = build_coach_persona(coach_id, coach_name, coach_niche, coach_offer)
        persona_block = f"\nYour voice: {persona}"

    trust_note = (
        "Fast truster: escalate toward call invitation by message 3."
        if trust_velocity == "fast"
        else "Slow truster: stay conversational through message 5, never push toward a call."
        if trust_velocity == "slow"
        else "Unknown trust speed: escalate gently, read their engagement."
    )

    prompt = f"""You are {coach_name}. Generate {num_messages} nurture messages for {first_name} in {lang_name}. {lang_note}
{persona_block}

Their situation:
- Main pain: {pain}
- All pain points: {all_pains}
- Platform: {platform} — Style: {platform_style}
- Trust pattern: {trust_note}

Rules:
- Each message uses a DIFFERENT angle (don't repeat the same pain twice)
- Each references something SPECIFIC about their situation
- Messages escalate naturally: conversation → insight → proof → invitation
- NEVER mention coaching/programs/services until message 4-5
- Each message is under 60 words
- Each must feel like a human follow-up, not an automated sequence
- Messages must NEVER sound like the previous one

Return ONLY valid JSON array:
[
  {{
    "day": <days after first contact>,
    "trigger": "<what should prompt sending this — e.g. 'no reply after 2 days', 'engaged with story'>",
    "angle": "<what this message focuses on>",
    "message": "<the DM text>"
  }}
]"""

    msg = _get_client().messages.create(
        model="claude-opus-4-7",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text
    start, end = text.find("["), text.rfind("]") + 1
    import json as _json
    try:
        return _json.loads(text[start:end])
    except Exception:
        return []
