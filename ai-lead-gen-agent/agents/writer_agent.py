"""Agent 2 — Writer: craft a hyper-personalized DM opener + follow-up sequence."""

import asyncio
import json
import re
from typing import Optional

import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, RETRY_ATTEMPTS, RETRY_BASE_DELAY

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """Tu es un copywriter expert en DM (messages directs) sur les réseaux sociaux.
Tu écris des messages pour des coachs francophones qui prospectent d'autres coachs francophones.

Règles ABSOLUES :
1. Chaque message doit référencer un élément SPÉCIFIQUE du contenu de la personne (pas de généralités)
2. Ton : curieux, chaleureux, value-first — jamais vendeur ni insistant
3. Longueur : opener ≤ 3 phrases, follow-ups ≤ 4 phrases
4. Zéro jargon marketing, zéro emoji excessif (max 1 par message)
5. Les messages doivent sonner 100 % humain, pas bot

Réponds UNIQUEMENT avec un objet JSON valide, sans markdown ni texte autour.
Structure exacte :
{
  "opener": "<message d'ouverture>",
  "followup_d2": "<relance jour 2>",
  "followup_d4": "<relance jour 4>",
  "followup_d7": "<relance jour 7>"
}"""


def _build_user_prompt(lead: dict) -> str:
    posts_text = "\n".join(
        f"  - \"{p['text'][:250]}\""
        for p in lead.get("posts", [])[:3]
    )
    return f"""Écris une séquence de DM pour ce lead :

Prénom/pseudo : {lead.get('username', 'inconnu')}
Plateforme : {lead.get('platform', '')}
Niche : {lead.get('niche', '')}
Bio : {lead.get('bio', '')}

Posts récents :
{posts_text or '  (non disponible)'}

Le prospect n'a jamais interagi avec nous. Écris les 4 messages de la séquence."""


async def _call_claude_with_retry(prompt: str) -> str:
    delay = RETRY_BASE_DELAY
    last_exc: Optional[Exception] = None
    for attempt in range(RETRY_ATTEMPTS):
        try:
            response = await asyncio.to_thread(
                _client.messages.create,
                model=CLAUDE_MODEL,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip()
        except (anthropic.APIError, anthropic.APIConnectionError) as exc:
            last_exc = exc
            if attempt < RETRY_ATTEMPTS - 1:
                await asyncio.sleep(delay)
                delay *= 2
    raise last_exc


def _parse_json_output(raw: str) -> dict:
    raw = re.sub(r"```(?:json)?", "", raw).strip()
    return json.loads(raw)


async def write_dm_sequence(lead: dict) -> dict:
    """
    Generate a personalized DM opener + 3 follow-ups for a qualified lead.

    Args:
        lead: output dict from qualifier_agent.qualify_lead()

    Returns:
        { opener, followup_d2, followup_d4, followup_d7 }
    """
    prompt = _build_user_prompt(lead)
    raw_output = await _call_claude_with_retry(prompt)
    return _parse_json_output(raw_output)
