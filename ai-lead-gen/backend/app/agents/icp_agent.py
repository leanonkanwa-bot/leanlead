"""
ICP Agent — Ideal Client Profile generation and iterative learning.

Agencies spend 2 weeks manually building ICP documents.
LeanLead does it in 60 seconds — and it gets smarter every week as leads respond.
"""
import json
import logging
import os

import anthropic

logger = logging.getLogger(__name__)

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


def get_onboarding_questions() -> list[str]:
    """5 smart questions that interview the coach to build their ICP."""
    return [
        "Décrivez en détail votre client idéal : qui est-il ? Quel âge, quelle situation pro, quelle vie quotidienne ?",
        "Quel est le problème numéro 1 qu'il essaie de résoudre quand il vous trouve ? En ses propres mots.",
        "Qu'est-ce qui l'a empêché de résoudre ce problème jusqu'à maintenant ? (temps, argent, croyances, peur ?)",
        "Racontez l'histoire de votre meilleur client — comment il vous a trouvé, pourquoi il a acheté, quel résultat il a eu.",
        "Quand un prospect hésite à travailler avec vous, quelle est sa vraie objection (pas ce qu'il dit, ce qu'il pense) ?",
    ]


def generate_icp(
    coach_name: str,
    coach_niche: str,
    coach_offer: str,
    target_audience: str,
    coach_answers: dict | None = None,
    sample_leads: list[dict] | None = None,
    reply_data: list[dict] | None = None,
) -> dict:
    """
    Generate a complete ICP from coach data.
    Optionally enriched with coach interview answers + top qualified leads + what actually got replies.
    """
    context_blocks: list[str] = []

    if coach_answers:
        answers_text = "\n".join(f"Q: {q}\nA: {a}" for q, a in coach_answers.items())
        context_blocks.append(f"Coach interview answers:\n{answers_text}")

    if sample_leads:
        top = sorted(sample_leads, key=lambda l: l.get("qualification_score", 0), reverse=True)[:10]
        leads_txt = "\n".join(
            f"- @{l.get('handle','?')} ({l.get('platform','?')}): score {l.get('qualification_score',0)}, "
            f"pain: {', '.join((json.loads(l['pain_points']) if isinstance(l.get('pain_points'), str) else l.get('pain_points', []))[:3])}"
            for l in top
        )
        context_blocks.append(f"Top qualified leads found so far:\n{leads_txt}")

    if reply_data:
        replied_txt = "\n".join(
            f"- {r.get('name','?')}: replied after {r.get('angle','?')} angle on {r.get('platform','?')}"
            for r in reply_data[:10]
        )
        context_blocks.append(f"Leads who actually replied (ground truth on what works):\n{replied_txt}")

    extra = "\n\n".join(context_blocks)

    prompt = f"""You are an elite marketing strategist. Build a detailed Ideal Client Profile (ICP) for this coach.

Coach: {coach_name}
Niche: {coach_niche}
Offer: {coach_offer}
Target audience description: {target_audience}

{extra}

Return ONLY valid JSON (no markdown):
{{
  "summary": "<2-3 sentence portrait of the ideal client — specific enough to recognize them on the street>",
  "demographics": {{
    "age_range": "<e.g. 28-42>",
    "gender": "<male|female|mixed — based on niche>",
    "location": "<primary markets>",
    "situation": "<job/life stage/family situation>",
    "income_range": "<estimated annual income>"
  }},
  "psychographics": {{
    "values": ["<top 3 core values — specific, not generic>"],
    "identity": "<how they see themselves in one sentence>",
    "dream_life": "<their dream outcome in 15 words>",
    "fears": ["<top 3 fears — use their own language>"],
    "awareness_stage": "<unaware|problem_aware|solution_aware|product_aware>"
  }},
  "pain_points": ["<top 5 pains — use the exact words they would type in Google>"],
  "buying_triggers": ["<top 3 events that make them ready to buy TODAY>"],
  "objections": [
    {{"objection": "<what they say>", "real_reason": "<what they actually mean>", "response": "<best 1-sentence response>"}}
  ],
  "best_dm_angles": ["<top 3 DM opening angles that resonate — very specific>"],
  "content_consumed": ["<platforms + content types they consume — very specific>"],
  "search_terms": ["<5 exact phrases they type into Google when looking for help>"],
  "platforms_ranked": ["<platforms in order of where they spend most time>"],
  "not_icp": "<1 sentence describing who is NOT a good fit>"
}}"""

    msg = _get_client().messages.create(
        model="claude-opus-4-7",
        max_tokens=1800,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text
    start, end = text.find("{"), text.rfind("}") + 1
    return json.loads(text[start:end])


def update_icp_from_conversions(
    current_icp: dict,
    successful_angles: list[str],
    successful_pain_points: list[str],
    failed_angles: list[str],
    coach_niche: str,
) -> dict:
    """
    Feature 1b: ICP self-learning.
    Updates ICP based on actual conversion data — what angles got replies, what pain points resonated.
    Called weekly by scheduler. ICP gets smarter every week.
    """
    if not successful_angles and not successful_pain_points:
        return current_icp

    prompt = f"""Update this ICP based on real conversion data from actual leads who responded.

Current ICP:
{json.dumps(current_icp, ensure_ascii=False)[:2000]}

What WORKED (got replies):
- Angles: {successful_angles}
- Pain points mentioned: {successful_pain_points}

What did NOT work (no reply):
- Angles: {failed_angles}

Niche: {coach_niche}

Return an UPDATED version of the same JSON structure with:
1. best_dm_angles reordered/updated to reflect what actually works
2. pain_points reordered by resonance (most successful first)
3. summary tweaked if patterns reveal something new about the ICP
All other fields stay the same unless there's strong evidence to update them.
Return ONLY valid JSON."""

    try:
        msg = _get_client().messages.create(
            model="claude-opus-4-7",
            max_tokens=1800,
            messages=[{"role": "user", "content": prompt}],
        )
        text = msg.content[0].text
        start, end = text.find("{"), text.rfind("}") + 1
        return json.loads(text[start:end])
    except Exception as e:
        logger.warning("ICP update failed: %s", e)
        return current_icp
