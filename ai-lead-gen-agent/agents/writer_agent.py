import json
import re
import time
from typing import Optional

import anthropic

from config import ANTHROPIC_API_KEY, CALENDLY_LINK, CLAUDE_MODEL, RETRY_ATTEMPTS, RETRY_BASE_DELAY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def write_dm_sequence(lead: dict) -> dict:
    posts_text = "\n".join(
        f'  - "{p["text"][:200]}"'
        for p in lead.get("posts", [])[:3]
    )

    prompt = f"""
Tu es un expert en copywriting de DMs pour coachs francophones.
Style : Alex Hormozi + Dan Martell. Humain, jamais commercial.

Profil du lead :
- Pseudo : {lead.get('username', 'inconnu')}
- Plateforme : {lead.get('platform', '')}
- Niche : {lead.get('niche')}
- Bio : {lead.get('bio', '')}
- Raison qualification : {lead.get('reason')}
- URL : {lead.get('url')}

Posts récents :
{posts_text or '  (non disponible)'}

Génère UNIQUEMENT ce JSON valide, sans markdown :
{{
  "opener": "<message d'ouverture personnalisé, 2-3 phrases max, curiosité + valeur, JAMAIS de pitch>",
  "followup_d2": "<relance J+2, apporte une insight utile lié à leur niche>",
  "followup_d4": "<relance J+4, pose une question sur leur plus grand défi>",
  "followup_d7": "<relance J+7, dernière tentative, offre une valeur concrète>"
}}

Règles :
- Chaque message sonne 100% humain, référence un élément SPÉCIFIQUE de leur contenu
- Jamais : "Je voulais juste...", "Est-ce que tu serais intéressé...", emojis excessifs
- Toujours spécifique à leur niche et à ce qu'ils postent réellement
- Maximum 3 phrases par message
"""

    last_exc: Optional[Exception] = None
    delay = RETRY_BASE_DELAY

    for attempt in range(RETRY_ATTEMPTS):
        try:
            response = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = re.sub(r"```(?:json)?", "", response.content[0].text).strip()
            result = json.loads(raw)
            result["lead_url"] = lead.get("url")
            result["calendly"] = CALENDLY_LINK
            return result
        except (anthropic.APIError, anthropic.APIConnectionError, json.JSONDecodeError) as exc:
            last_exc = exc
            if attempt < RETRY_ATTEMPTS - 1:
                time.sleep(delay)
                delay *= 2

    raise last_exc
