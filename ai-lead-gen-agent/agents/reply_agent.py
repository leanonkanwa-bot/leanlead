"""Agent 3 — Reply: classify an incoming DM and generate a contextual response."""

import asyncio
import json
import re
from typing import Optional

import anthropic

from config import (
    ANTHROPIC_API_KEY,
    CLAUDE_MODEL,
    BUYING_SIGNAL_MIN_EXCHANGES,
    RETRY_ATTEMPTS,
    RETRY_BASE_DELAY,
)
from integrations.calendly import get_booking_link

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

CLASSIFICATIONS = ("POSITIVE", "NEUTRAL", "NEGATIVE", "BUYING_SIGNAL")

SYSTEM_PROMPT = """Tu es un assistant expert en gestion de conversations DM pour des coachs francophones.
Ta mission : analyser une réponse entrante, la classifier, et rédiger une réplique naturelle.

Classifications disponibles :
- POSITIVE : intérêt manifeste, curiosité, ouverture
- NEUTRAL : réponse polie sans intention claire
- NEGATIVE : désintérêt, refus, irritation
- BUYING_SIGNAL : demande de prix, de détails sur l'offre, proposition de call, "comment ça marche ?"

Règles de réponse :
1. Réponse conversationnelle, jamais commerciale
2. Poser UNE seule question ouverte max par message
3. Si classification NEGATIVE : réponse courte, respectueuse, sans insistance
4. Si inject_calendly = true : intègre le lien de façon ultra-naturelle dans la réplique
5. Longueur : 2-4 phrases max

Réponds UNIQUEMENT avec un objet JSON valide, sans markdown ni texte autour.
Structure exacte :
{
  "reply": "<texte du message de réponse>",
  "classification": "<POSITIVE|NEUTRAL|NEGATIVE|BUYING_SIGNAL>",
  "inject_calendly": <true|false>,
  "flag_human": <true|false>
}

flag_human = true si : lead très chaud + historique ≥ 5 échanges, ou si la situation est ambiguë/sensible."""


def _build_user_prompt(
    incoming_message: str,
    conversation_history: list[dict],
    exchange_count: int,
    calendly_link: str,
) -> str:
    history_text = "\n".join(
        f"  [{m['role'].upper()}] {m['content'][:300]}"
        for m in conversation_history[-8:]
    )
    return f"""Conversation jusqu'ici ({exchange_count} échanges) :
{history_text or '  (premier message reçu)'}

Nouveau message reçu :
"{incoming_message}"

Lien Calendly disponible : {calendly_link}
Nombre d'échanges total : {exchange_count}

Analyse ce message et génère la réponse appropriée."""


async def _call_claude_with_retry(prompt: str) -> str:
    delay = RETRY_BASE_DELAY
    last_exc: Optional[Exception] = None
    for attempt in range(RETRY_ATTEMPTS):
        try:
            response = await asyncio.to_thread(
                _client.messages.create,
                model=CLAUDE_MODEL,
                max_tokens=768,
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


async def handle_reply(
    incoming_message: str,
    conversation_history: Optional[list[dict]] = None,
    exchange_count: int = 1,
) -> dict:
    """
    Classify an incoming DM and produce a contextual response.

    Args:
        incoming_message: raw text of the prospect's latest message
        conversation_history: list of { role: "agent"|"lead", content: str }
        exchange_count: total number of exchanges so far (used for Calendly injection logic)

    Returns:
        { reply, classification, inject_calendly, flag_human }
    """
    conversation_history = conversation_history or []
    calendly_link = get_booking_link()

    prompt = _build_user_prompt(
        incoming_message, conversation_history, exchange_count, calendly_link
    )
    raw_output = await _call_claude_with_retry(prompt)
    result = _parse_json_output(raw_output)

    # Enforce Calendly injection only after minimum exchanges
    classification = result.get("classification", "NEUTRAL")
    should_inject = (
        classification == "BUYING_SIGNAL"
        and exchange_count >= BUYING_SIGNAL_MIN_EXCHANGES
    )
    result["inject_calendly"] = should_inject

    # Append Calendly link to reply if needed
    if should_inject and calendly_link not in result.get("reply", ""):
        result["reply"] = result["reply"].rstrip() + f"\n\nVoici mon lien pour qu'on se parle : {calendly_link} 🗓️"

    result["classification"] = classification if classification in CLASSIFICATIONS else "NEUTRAL"
    return result
