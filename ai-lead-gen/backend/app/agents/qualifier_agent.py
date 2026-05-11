"""
Qualifier Agent
Scores a social-media profile 0-100 based on how intensely the person
expresses a pain that the coach's ICP (ideal client profile) experiences.

Pre-qualification signal detectors run BEFORE the Claude API call to:
  - Detect ghost followers (follows coaches but hasn't bought) → +20, tag "Suiveur de coaches"
  - Detect life event triggers (FR+EN) → +30
  - Detect buying intent signals (FR+EN) → +15
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
# Pre-qualification signal detection (fast regex, no API call)
# ---------------------------------------------------------------------------

_FOLLOWS_COACHES_RE = re.compile(
    r'\b('
    # French
    r'suivi?s? par|abonné(e)? (à|de)|fan de|inspiré(e)? par|merci.{0,20}coach|'
    r'coach de ma vie|ma coach|mon coach|ma coachin|j\'adore.{0,15}coach|'
    r'j\'ai suivi|j\'ai regardé|j\'ai fait (le |la |son |sa )?programme|'
    r'la méthode de|le podcast de|sa chaîne|formation (de|avec)|masterclass|'
    # English
    r'following.{0,15}coach|fan of.{0,15}coach|love.{0,15}coach|inspired by|'
    r'watched.{0,10}course|enrolled in|coaching program|my coach|best coach|'
    r'coach changed my life|coach helped me'
    r')\b',
    re.IGNORECASE,
)

_LIFE_EVENT_RE = re.compile(
    r'\b('
    # French — new year / restart
    r'nouvelle ann[ée]e?|nouvel an|nouveau d[ée]part|tout recommencer|repartir de z[ée]ro|'
    r'nouvelle vie|changer de vie|changement de vie|'
    # French — work / career
    r'licenci[ée](e)?|au ch[ôo]mage|d[ée]mission|j\'ai quitt[ée]|reconversion|'
    r'plus jamais|ras le bol|j\'en peux plus|j\'en ai marre|marre de|'
    # French — relationships
    r'divorc[ée](e)?|s[ée]paration|rupture|c[ée]libataire (depuis|à nouveau)|'
    r'b[ée]b[ée]|enceinte|accouchement|mariage|fianç|'
    # French — decision
    r'j\'ai d[ée]cid[ée]|cette fois c\'est la bonne|maintenant ou jamais|'
    r'j\'ai enfin|je me lance|j\'ose|'
    # English
    r'new year|fresh start|starting over|just lost my job|quit my job|left my job|'
    r'just divorced|just had a baby|new chapter|rock bottom|enough is enough|'
    r'turning point|wake up call|life change|big decision|career change|'
    r'turned 3\d|turning 3\d|turned 4\d|turning 4\d|just graduated|just moved'
    r')\b',
    re.IGNORECASE,
)

_BUYING_INTENT_RE = re.compile(
    r'\b('
    # French
    r'combien [çca]a co[uû]te|c\'est combien|quel tarif|comment vous contacter|'
    r'o[uù] trouver|comment faire pour|j\'ai besoin d\'aide|quelqu\'un peut m\'aider|'
    r'des conseils|vous recommandez|comment commencer|par o[uù] commencer|'
    r'cherche un coach|besoin d\'un coach|qui peut m\'aider|des recommandations|'
    r'comment (tu|vous) (fais|faites)|'
    # English
    r'how much|how do i start|where do i start|looking for a coach|'
    r'need a coach|any recommendations|how do i|someone help|advice please|'
    r'ready to invest|ready to change|need guidance'
    r')\b',
    re.IGNORECASE,
)


def _detect_signals(lead_data: dict) -> dict:
    """Fast pre-qualifier that detects high-value signals before hitting Claude API."""
    text = f"{lead_data.get('bio', '')} {lead_data.get('posts_summary', '')}".strip()
    return {
        "follows_coaches": bool(_FOLLOWS_COACHES_RE.search(text)),
        "life_event": bool(_LIFE_EVENT_RE.search(text)),
        "buying_intent": bool(_BUYING_INTENT_RE.search(text)),
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
    Scores how strongly this person is expressing a pain the coach solves.

    Returns:
        {
          "score": int (0-100),
          "reason": str,
          "pain_points": list[str],
          "recommended_angle": str,
        }
    """
    # Run fast signal detection first
    signals = _detect_signals(lead_data)

    pains_block = ""
    if icp_pain_points:
        formatted = "\n".join(f"  - {p}" for p in icp_pain_points)
        pains_block = f"\nPains the coach's ideal client typically expresses:\n{formatted}\n"

    signal_context = ""
    if any(signals.values()):
        detected = []
        if signals["life_event"]:
            detected.append("⚡ LIFE EVENT DETECTED (major personal transition in their content)")
        if signals["follows_coaches"]:
            detected.append("👁 FOLLOWS COACHES (references coaches/programs they follow)")
        if signals["buying_intent"]:
            detected.append("💳 BUYING INTENT (actively asking about solutions/costs)")
        signal_context = "\n\nPRE-DETECTED SIGNALS:\n" + "\n".join(detected) + "\n"

    prompt = f"""You are an expert at identifying people who are actively struggling with a specific problem.

Coach niche: {coach_niche}
Coach offer: {coach_offer}{pains_block}{signal_context}
Profile to analyze:
- Name: {lead_data.get("name", "Unknown")}
- Handle: @{lead_data.get("handle", "")}
- Platform: {lead_data.get("platform", "instagram")}
- Bio: {lead_data.get("bio", "No bio")}
- Followers: {lead_data.get("followers", 0):,}
- Recent posts / content summary: {lead_data.get("posts_summary", "N/A")}

Your task: score 0-100 how strongly this person is EXPRESSING or LIVING one of the coach's target pains RIGHT NOW.

Scoring guide:
85-100 → Actively venting or posting about the struggle, explicit pain language, high emotional charge
65-84  → Clear signals of the problem in bio or posts, not explicitly venting but clearly affected
40-64  → Indirect signals — lifestyle or content suggests the pain but not stated
15-39  → Weak alignment, possible fit but little evidence
0-14   → Wrong audience, no alignment, influencer/brand account, or competitor

IMPORTANT DISQUALIFIERS (score ≤ 10):
- They ARE a coach/consultant in the same niche (they sell solutions, not buy them)
- They are a brand, business, or media account
- No content signals at all

Respond ONLY with valid JSON (no markdown, no extra text):
{{"score": <0-100>, "reason": "<2-3 sentences: what specific signals justify the score>", "pain_points": ["<exact pain detected in their content>", ...], "recommended_angle": "<the single most resonant pain to open the conversation with>"}}"""

    msg = _get_client().messages.create(
        model="claude-opus-4-7",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text
    start, end = text.find("{"), text.rfind("}") + 1
    result = json.loads(text[start:end])

    # Normalise score
    score = max(0, min(100, int(result.get("score", 0))))

    # Apply deterministic signal boosts (applied AFTER Claude scoring)
    if signals["life_event"]:
        score = min(95, score + 30)
    if signals["follows_coaches"]:
        score = min(95, score + 20)
        pain_points = result.get("pain_points", [])
        if "Suiveur de coaches" not in pain_points:
            pain_points.insert(0, "Suiveur de coaches")
        result["pain_points"] = pain_points
    if signals["buying_intent"]:
        score = min(95, score + 15)

    result["score"] = score
    result.setdefault("reason", "")
    result.setdefault("pain_points", [])
    result.setdefault("recommended_angle", "")
    return result
