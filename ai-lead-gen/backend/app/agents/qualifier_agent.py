"""
Qualifier Agent — v4
Scores 0-100 + psychographic profile + response probability in ONE Claude call.

Pre-qualification signal boosts (deterministic, no API cost):
  • Buying intent (5 languages: FR/EN/ES/PT/AR) → +40
  • Life event trigger                           → +30
  • Ghost follower (follows coaches)             → +20
  • Hot prospect (repeated engagement)           → +15
  • Pain peak (maximum vulnerability)            → +25
  • Failed purchase (burned buyer)               → +35
  • Before/after seeker (transformation desire)  → +15
"""
import json
import logging
import os
import re

import anthropic
import httpx

logger = logging.getLogger(__name__)

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

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

_PAIN_PEAK_RE = re.compile(
    r'\b('
    # French — maximum vulnerability expressions
    r'je craque|je pète un câble|je suis à bout|j\'abandonne|j\'abandonne tout|'
    r'j\'en ai ras le bol|plus la force|plus envie de rien|j\'ai tout essayé|'
    r'je pleure|j\'ai pleuré|nuit blanche|2h du matin|3h du matin|4h du mat|'
    r'au secours|help me|s\'il vous plaît aidez|quelqu\'un peut m\'aider|'
    r'je ne sais plus quoi faire|je ne vois plus d\'issue|au fond du trou|'
    r'rock bottom|breaking point|can\'t do this anymore|i give up|'
    # English
    r'i\'m done|i\'m broken|i can\'t go on|hit rock bottom|enough is enough|'
    r'please someone help|i\'ve tried everything|nothing is working|'
    r'i\'m desperate|last resort|i don\'t know what to do'
    r')\b',
    re.IGNORECASE,
)

_FAILED_PURCHASE_RE = re.compile(
    r'('
    # French — bought coaching, got burned
    r'j\'ai (acheté|payé|investi).{0,50}(coach|formation|programme|cours|masterclass)|'
    r'(formation|programme|coaching|cours|masterclass).{0,40}(arnaque|marche pas|pas fonctionné|déçu|remboursement|nul|inutile)|'
    r'(arnaqué|escroquerie|fraude).{0,30}(coach|formation)|'
    r'perdu.{0,20}(€|euro|argent).{0,30}(coach|formation)|'
    r'demandé.{0,10}remboursement|se faire rembourser|'
    r'# English — failed buyer signals
    r'wasted.{0,20}(money|\$|€).{0,30}(coach|program|course)|'
    r'paid.{0,30}(coach|program|course).{0,30}(didn\'t|not|no result|waste|scam)|'
    r'got scammed.{0,20}(coach|program)|coaching.{0,30}(scam|fraud|waste)|'
    r'money back.{0,20}(coaching|program)|refund.{0,20}(coach|course)|'
    r'coach.{0,30}(lied|fake|fraud|useless|waste of)'
    r')',
    re.IGNORECASE,
)

_BEFORE_AFTER_RE = re.compile(
    r'\b('
    # Actively seeking transformation
    r'avant[/-]après|transformation|avant après|résultats comme|comme toi|comme ça|'
    r'je veux (ça|ça aussi|ce résultat|ces résultats|ce corps|cette vie)|'
    r'j\'aspire à|j\'aimerais (tellement|vraiment)|mon objectif|mes objectifs|'
    r'before.?after|body goals|life goals|goals!|goals 🙌|i want this|'
    r'this is my goal|i want results like|relationship goals|'
    r'saving this|bookmarking this|pinned|saved for inspo|'
    r'c\'est mon objectif|objectif atteint|objectif de vie'
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
        "pain_peak": bool(_PAIN_PEAK_RE.search(text)),
        "failed_purchase": bool(_FAILED_PURCHASE_RE.search(text)),
        "before_after_seeker": bool(_BEFORE_AFTER_RE.search(text)),
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
        if signals["pain_peak"]:
            detected.append("🚨 PAIN PEAK — at maximum emotional vulnerability right now")
        if signals["failed_purchase"]:
            detected.append("💔 FAILED BUYER — bought coaching before, got burned; still wants results")
        if signals["before_after_seeker"]:
            detected.append("🎯 TRANSFORMATION SEEKER — actively looking for before/after results")
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
  "response_probability": <0-100 likelihood they reply to a personalized DM>,
  "predicted_objection": "<their single most likely objection to buying, e.g. 'pas les moyens', 'pas le temps', 'déjà essayé', 'pas sûr que ça marche pour moi'>"
}}

Scoring guide: 85-100 actively venting/explicit pain · 65-84 clear signals · 40-64 indirect · 15-39 weak · 0-14 wrong audience/brand/competitor
response_probability: consider activity level, pain intensity, awareness stage, engagement patterns
predicted_objection: infer from their communication style, awareness stage, and content — be specific to THIS person"""

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
    result.setdefault("predicted_objection", "")
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
    if signals["pain_peak"]:
        score = min(98, score + 25)
        pain_points = result["pain_points"]
        if "Pic de douleur" not in pain_points:
            pain_points.insert(0, "Pic de douleur")
        result["pain_points"] = pain_points
    if signals["failed_purchase"]:
        score = min(98, score + 35)
        pain_points = result["pain_points"]
        if "Acheteur raté" not in pain_points:
            pain_points.insert(0, "Acheteur raté")
        result["pain_points"] = pain_points
    if signals["before_after_seeker"]:
        score = min(95, score + 15)
        pain_points = result["pain_points"]
        if "Cherche transformation" not in pain_points:
            pain_points.append("Cherche transformation")
        result["pain_points"] = pain_points

    result["score"] = score
    return result


# ---------------------------------------------------------------------------
# Cross-platform identity matching
# ---------------------------------------------------------------------------

_PLATFORM_URL_MAP = {
    "instagram": "instagram.com",
    "tiktok": "tiktok.com",
    "twitter": "twitter.com",
    "linkedin": "linkedin.com",
    "youtube": "youtube.com",
    "reddit": "reddit.com",
}


def enrich_cross_platform(handle: str, base_platform: str) -> str:
    """
    Search for the same handle on other platforms via DDG.
    Returns additional posts_summary context merged from other platforms.
    Called before qualification to give Claude richer data — no extra API cost.
    """
    other_platforms = [p for p in _PLATFORM_URL_MAP if p != base_platform]
    extra_snippets: list[str] = []

    for platform in other_platforms[:3]:  # check up to 3 other platforms
        site = _PLATFORM_URL_MAP[platform]
        query = f'site:{site} "{handle}"'
        try:
            resp = httpx.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers=BROWSER_HEADERS,
                timeout=8,
                follow_redirects=True,
            )
            # Extract first snippet that contains the exact handle
            snippets = re.findall(
                r'class="result__snippet">(.*?)</a>',
                resp.text,
                re.DOTALL,
            )
            for raw in snippets[:2]:
                text = re.sub(r'<[^>]+>', '', raw).strip()
                if handle.lower() in text.lower() and len(text) > 30:
                    extra_snippets.append(f"[{platform}] {text[:200]}")
                    break
        except Exception:
            pass

    return " | ".join(extra_snippets) if extra_snippets else ""
