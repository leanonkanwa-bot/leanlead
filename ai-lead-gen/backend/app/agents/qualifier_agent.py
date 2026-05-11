"""
Qualifier Agent — v3
Scores 0-100 + psychographic profile + response probability in ONE Claude call.

Pre-qualification signal boosts (deterministic, no API cost):
  • Buying intent (5 languages: FR/EN/ES/PT/AR) → +40
  • Life event trigger                           → +30
  • Ghost follower (follows coaches)             → +20
"""
import json
import os
import re

import anthropic

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


# ---------------------------------------------------------------------------
# Signal detectors — 5 languages, no API call
# ---------------------------------------------------------------------------

_BUYING_INTENT_RE = re.compile(
    r'\b('
    # French
    r'combien [çca]a co[uû]te|c\'est combien|quel (est le )?tarif|comment vous contacter|'
    r'o[uù] (vous )?trouver|j\'ai besoin d\'aide|quelqu\'un peut m\'aider|'
    r'cherche un coach|besoin d\'un coach|qui peut m\'aider|'
    r'comment commencer|par o[uù] commencer|comment (tu|vous) (fais|faites)|'
    r'vous recommandez|des recommandations|c\'est possible pour moi|'
    r'je veux (changer|m\'améliorer|progresser)|prêt(e)? à investir|'
    # English
    r'how much (does it cost|is it)|how do i (start|get started)|where do i start|'
    r'looking for a coach|need a coach|any recommendations|how do i|'
    r'someone help|advice please|ready to invest|is it possible for me|'
    r'do you recommend (someone|anyone)|how did you do it|'
    # Spanish
    r'cu[aá]nto cuesta|c[oó]mo empezar|necesito (un coach|ayuda)|'
    r'recomiendas (a )?alguien|es posible para m[ií]|c[oó]mo lo hiciste|'
    r'busco un coach|necesito apoyo|por d[oó]nde empiezo|'
    # Portuguese
    r'quanto custa|como come[çc]ar|preciso de (ajuda|um coach)|'
    r'voc[êe] recomenda|[eé] poss[íi]vel para mim|como voc[êe] fez|'
    r'procuro um coach|preciso de apoio|por onde come[çc]ar|'
    # Arabic (transliterated + common patterns)
    r'كم يكلف|كيف أبدأ|أحتاج مساعدة|هل ممكن|كيف فعلت|أبحث عن مدرب'
    r')\b',
    re.IGNORECASE,
)

_LIFE_EVENT_RE = re.compile(
    r'\b('
    # French
    r'nouvelle ann[ée]e?|nouvel an|nouveau d[ée]part|tout recommencer|repartir de z[ée]ro|'
    r'nouvelle vie|changer de vie|licenci[ée]e?|au ch[ôo]mage|d[ée]mission|'
    r'j\'ai quitt[ée]|reconversion|j\'en peux plus|j\'en ai marre|ras le bol|'
    r'divorc[ée]e?|s[ée]paration|rupture|b[ée]b[ée]|enceinte|accouchement|'
    r'mariage|fianc[ée]|j\'ai d[ée]cid[ée]|cette fois c\'est la bonne|maintenant ou jamais|'
    r'je me lance|j\'ose enfin|'
    # English
    r'new year|fresh start|starting over|just lost my job|quit my job|left my job|'
    r'just divorced|just had a baby|new chapter|rock bottom|enough is enough|'
    r'turning point|wake up call|life change|career change|'
    r'turned 3\d|turning 3\d|turned 4\d|turning 4\d|just graduated|just moved|'
    # Spanish/Portuguese
    r'nuevo comienzo|empezar de cero|acabo de perder|nueva vida|'
    r'novo come[çc]o|come[çc]ar do zero|'
    r')\b',
    re.IGNORECASE,
)

_FOLLOWS_COACHES_RE = re.compile(
    r'\b('
    # French
    r'suivi?s? par|abonné(e)? (à|de)|fan de|inspiré(e)? par|merci.{0,20}coach|'
    r'coach de ma vie|ma coach|mon coach|j\'adore.{0,15}coach|'
    r'j\'ai suivi|j\'ai regardé|j\'ai fait (le |la |son |sa )?programme|'
    r'la méthode de|le podcast de|sa chaîne|formation (de|avec)|masterclass|'
    # English
    r'following.{0,15}coach|fan of.{0,15}coach|love.{0,15}coach|inspired by|'
    r'watched.{0,10}course|enrolled in|coaching program|my coach|'
    r'coach changed my life|coach helped me'
    r')\b',
    re.IGNORECASE,
)

_HOT_PROSPECT_RE = re.compile(
    r'\b('
    # Repeatedly engaging with solution content
    r'je regarde (toutes?|chaque)|j\'ai regardé (tous?|chaque)|je suis (tous?|chaque)|'
    r'tes (vidéos?|contenus?|lives?|stories?)|vos (vidéos?|contenus?)|'
    r'i watch (all|every)|i follow (all|every)|i\'ve watched|been following|'
    r'siempre (veo|sigo)|sempre (assisto|sigo)'
    r')\b',
    re.IGNORECASE,
)


def _detect_signals(lead_data: dict) -> dict:
    text = f"{lead_data.get('bio', '')} {lead_data.get('posts_summary', '')}".strip()
    return {
        "buying_intent": bool(_BUYING_INTENT_RE.search(text)),
        "life_event": bool(_LIFE_EVENT_RE.search(text)),
        "follows_coaches": bool(_FOLLOWS_COACHES_RE.search(text)),
        "hot_prospect": bool(_HOT_PROSPECT_RE.search(text)),
    }


# ---------------------------------------------------------------------------
# Main qualifier
# ---------------------------------------------------------------------------

def qualify_lead(
    lead_data: dict,
    coach_niche: str,
    coach_offer: str,
    icp_pain_points: list[str] | None = None,
) -> dict:
    """
    Scores lead 0-100, builds psychographic profile, predicts response probability.
    All in one Claude call. Deterministic signal boosts applied after.

    Returns:
        score, reason, pain_points, recommended_angle,
        psychographic {dominant_emotion, awareness_stage, communication_style,
                        best_contact_time, language},
        response_probability
    """
    signals = _detect_signals(lead_data)

    pains_block = ""
    if icp_pain_points:
        pains_block = "\nPains the coach's ICP typically expresses:\n" + \
                      "\n".join(f"  - {p}" for p in icp_pain_points) + "\n"

    signal_context = ""
    if any(signals.values()):
        detected = []
        if signals["buying_intent"]:
            detected.append("💳 BUYING INTENT — actively asking about solutions or costs")
        if signals["life_event"]:
            detected.append("⚡ LIFE EVENT — major personal transition detected")
        if signals["follows_coaches"]:
            detected.append("👁 FOLLOWS COACHES — references coaches/programs they watch")
        if signals["hot_prospect"]:
            detected.append("🔥 HOT PROSPECT — repeatedly engages with solution content")
        signal_context = "\n\nPRE-DETECTED SIGNALS:\n" + "\n".join(detected) + "\n"

    prompt = f"""You are an expert at identifying people who are actively struggling with a problem and are likely to buy a coaching solution.

Coach niche: {coach_niche}
Coach offer: {coach_offer}{pains_block}{signal_context}
Profile:
- Name: {lead_data.get("name", "Unknown")}
- Handle: @{lead_data.get("handle", "")}
- Platform: {lead_data.get("platform", "instagram")}
- Bio: {lead_data.get("bio", "No bio")}
- Followers: {lead_data.get("followers", 0):,}
- Content summary: {lead_data.get("posts_summary", "N/A")}

Respond ONLY with valid JSON (no markdown):
{{
  "score": <0-100 pain/fit score>,
  "reason": "<2-3 sentences explaining specific signals>",
  "pain_points": ["<exact pain from their content>", ...],
  "recommended_angle": "<single most resonant pain to open DM with>",
  "psychographic": {{
    "dominant_emotion": "<frustration|fear|hope|excitement|shame|anxiety>",
    "awareness_stage": "<unaware|problem_aware|solution_aware|product_aware>",
    "communication_style": "<casual|formal>",
    "best_contact_time": "<morning|evening|weekend|anytime>",
    "language": "<fr|en|es|pt|ar|other>"
  }},
  "response_probability": <0-100 likelihood they reply to a personalized DM>
}}

Scoring guide: 85-100 actively venting/explicit pain · 65-84 clear signals · 40-64 indirect · 15-39 weak · 0-14 wrong audience/brand/competitor
response_probability: consider activity level, pain intensity, awareness stage, engagement patterns"""

    msg = _get_client().messages.create(
        model="claude-opus-4-7",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text
    start, end = text.find("{"), text.rfind("}") + 1
    result = json.loads(text[start:end])

    # Normalise types
    score = max(0, min(100, int(result.get("score", 0))))
    result.setdefault("reason", "")
    result.setdefault("pain_points", [])
    result.setdefault("recommended_angle", "")
    result.setdefault("psychographic", {})
    result.setdefault("response_probability", 50)
    result["response_probability"] = max(0, min(100, int(result["response_probability"])))

    # Deterministic signal boosts (applied after Claude scoring)
    if signals["buying_intent"]:
        score = min(95, score + 40)
    if signals["life_event"]:
        score = min(95, score + 30)
    if signals["follows_coaches"]:
        score = min(95, score + 20)
        pain_points = result["pain_points"]
        if "Suiveur de coaches" not in pain_points:
            pain_points.insert(0, "Suiveur de coaches")
        result["pain_points"] = pain_points
    if signals["hot_prospect"]:
        score = min(95, score + 15)
        result["pain_points"] = ["Prospect chaud"] + [p for p in result["pain_points"] if p != "Prospect chaud"]

    result["score"] = score
    return result
