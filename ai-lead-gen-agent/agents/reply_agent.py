import json
import re
import time
from typing import Optional

import anthropic

from config import (
    ANTHROPIC_API_KEY,
    CALENDLY_LINK,
    CLAUDE_MODEL,
    BUYING_SIGNAL_MIN_EXCHANGES,
    RETRY_ATTEMPTS,
    RETRY_BASE_DELAY,
)

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def handle_reply(
    incoming_message: str,
    conversation_history: list,
    exchange_count: int,
) -> dict:
    prompt = f"""
Tu es un agent de conversation pour coach francophone.
Historique : {json.dumps(conversation_history[-8:], ensure_ascii=False)}
Nouveau message reçu : "{incoming_message}"
Nombre d'échanges : {exchange_count}
Lien Calendly : {CALENDLY_LINK}

Réponds UNIQUEMENT en JSON valide, sans markdown :
{{
  "classification": "<POSITIVE|NEUTRAL|NEGATIVE|BUYING_SIGNAL>",
  "reply": "<ta réponse, max 3 phrases, 100% humaine>",
  "inject_calendly": <true si BUYING_SIGNAL et échanges >= {BUYING_SIGNAL_MIN_EXCHANGES}, sinon false>,
  "flag_human": <true si lead très chaud ou situation ambiguë, sinon false>
}}

Règles :
- Si inject_calendly est true : intègre naturellement "{CALENDLY_LINK}" dans la réponse
- BUYING_SIGNAL = demande de prix, de détails sur l'offre, "comment ça marche", proposition de call
- Jamais de langage robot, toujours continuer la conversation naturellement
- Si NEGATIVE : réponse courte, respectueuse, sans insistance
- Pose UNE seule question ouverte maximum par message
"""

    last_exc: Optional[Exception] = None
    delay = RETRY_BASE_DELAY

    for attempt in range(RETRY_ATTEMPTS):
        try:
            response = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = re.sub(r"```(?:json)?", "", response.content[0].text).strip()
            result = json.loads(raw)

            # Enforce Calendly only after minimum exchanges
            is_buying = result.get("classification") == "BUYING_SIGNAL"
            result["inject_calendly"] = is_buying and exchange_count >= BUYING_SIGNAL_MIN_EXCHANGES

            # Append Calendly link if needed and not already present
            if result["inject_calendly"] and CALENDLY_LINK not in result.get("reply", ""):
                result["reply"] = (
                    result["reply"].rstrip()
                    + f"\n\nVoici mon lien pour qu'on se parle : {CALENDLY_LINK} 🗓️"
                )

            return result
        except (anthropic.APIError, anthropic.APIConnectionError, json.JSONDecodeError) as exc:
            last_exc = exc
            if attempt < RETRY_ATTEMPTS - 1:
                time.sleep(delay)
                delay *= 2

    raise last_exc
