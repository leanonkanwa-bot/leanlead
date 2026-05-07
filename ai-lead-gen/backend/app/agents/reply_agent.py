"""
Reply Agent
Classifies a lead's reply and generates the perfect contextual response.
Returns structured JSON with classification, reasoning, reply text, and Calendly flag.
"""
import json
import os

import anthropic

_client: anthropic.Anthropic | None = None

CLASSIFICATIONS = {
    "POSITIF":      "Intéressé·e, engage positivement, pose des questions",
    "NEUTRE":       "Poli·e mais sans engagement clair",
    "NEGATIF":      "Refuse ou demande à arrêter",
    "SIGNAL_ACHAT": "Intention claire de réserver / acheter",
}


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


def generate_reply(
    lead_reply: str,
    conversation_history: str,
    coach_name: str,
    coach_niche: str,
    coach_offer: str,
    calendly_link: str,
) -> dict:
    """
    Analyse la réponse du lead et génère la réponse parfaite.
    Returns: {classification, reasoning, reply, inject_calendly}
    """
    history_block = f"\nHistorique :\n{conversation_history}\n" if conversation_history.strip() else ""
    calendly_block = f"\nLien de réservation : {calendly_link}" if calendly_link else ""

    prompt = f"""Tu es {coach_name}, coach en {coach_niche}.
Ton offre : {coach_offer}{calendly_block}
{history_block}
Message reçu du lead :
"{lead_reply}"

Analyse ce message et génère la réponse idéale.

Classifications disponibles :
- POSITIF      : Intéressé·e, engage positivement, pose des questions
- NEUTRE       : Poli·e mais sans engagement clair
- NEGATIF      : Refuse ou demande à arrêter
- SIGNAL_ACHAT : Intention claire de réserver / acheter (demande prix, dispo, étapes)

Règles pour la réponse :
- EN FRANÇAIS, comme une vraie personne — pas un script de vente
- Sous 80 mots
- SIGNAL_ACHAT + Calendly fourni → intègre le lien naturellement dans le texte
- NEGATIF → remercie poliment, n'insiste pas
- NEUTRE → pose UNE question ciblée pour débloquer la situation
- POSITIF → approfondis ou propose naturellement la prochaine étape

Retourne UNIQUEMENT ce JSON valide (zéro texte autour) :
{{
  "classification": "POSITIF" | "NEUTRE" | "NEGATIF" | "SIGNAL_ACHAT",
  "reasoning": "une phrase expliquant la classification",
  "reply": "le message exact à envoyer",
  "inject_calendly": true | false
}}"""

    msg = _get_client().messages.create(
        model="claude-opus-4-7",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text.strip()
    start, end = text.find("{"), text.rfind("}") + 1
    data = json.loads(text[start:end])

    if data.get("classification") not in CLASSIFICATIONS:
        data["classification"] = "NEUTRE"
    data.setdefault("reasoning", "")
    data.setdefault("reply", "")
    data.setdefault("inject_calendly", False)
    return data
