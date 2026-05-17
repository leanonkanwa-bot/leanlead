"""
Follow-up Agent
Generates D+2, D+4, and D+7 follow-up messages for leads that haven't replied.
Each touch has a different tone to avoid feeling spammy.
"""
import os

import anthropic

_client: anthropic.Anthropic | None = None

FOLLOWUP_TONES = {
    2: "light, casual bump — under 40 words. Reference one specific thing from their profile or bio. No pressure.",
    4: "value-add — share a short, sharp insight or ask a curious question directly relevant to their situation. Under 50 words.",
    7: "closing the loop — honest, human, final message. Make it easy for them to say no. Under 40 words. No guilt.",
}


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


def generate_followup(
    lead_data: dict,
    original_dm: str,
    coach_name: str,
    coach_niche: str,
    coach_offer: str,
    day: int,
) -> str:
    """
    Generate a follow-up DM. day: 2 = D+2, 4 = D+4, 7 = D+7.
    Returns the message text.
    """
    tone = FOLLOWUP_TONES.get(day, FOLLOWUP_TONES[7])
    first_name = (lead_data.get("name") or "").split()[0] or "toi"

    prompt = f"""Tu es {coach_name}, coach en {coach_niche}. Tu fais un suivi sur un DM Instagram sans réponse.

DM original envoyé :
"{original_dm}"

Profil du lead :
- Prénom : {first_name}
- Bio : {lead_data.get("bio", "")}
- Plateforme : {lead_data.get("platform", "instagram")}

C'est le suivi J+{day}. Ton : {tone}

Règles STRICTES :
- N'utilise PAS "juste un suivi" ou "je reviens vers toi"
- Ne répète PAS le DM original
- Sonne comme une vraie personne, pas une séquence automatique
- Écris EN FRANÇAIS
- Retourne UNIQUEMENT le texte du message — rien d'autre"""

    msg = _get_client().messages.create(
        model="claude-opus-4-7",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()
