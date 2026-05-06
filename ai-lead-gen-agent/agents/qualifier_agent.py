"""Agent 1 — Qualifier: scrape a social profile and score it as a francophone coach lead."""

import asyncio
import json
import re
from typing import Optional

import anthropic
import httpx

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, QUALIFIER_SCORE_THRESHOLD, RETRY_ATTEMPTS, RETRY_BASE_DELAY
from integrations.scraper import scrape_profile

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """Tu es un expert en qualification de leads pour des coachs francophones.
Tu analyses des profils de réseaux sociaux et tu évalues si la personne est un coach francophone
actif dans l'un de ces créneaux : business/entrepreneuriat, fitness/santé, mindset/développement
personnel, spirituel/bien-être.

Réponds UNIQUEMENT avec un objet JSON valide, sans markdown ni texte autour.
Structure exacte :
{
  "score": <entier 0-100>,
  "niche": "<niche détectée ou 'inconnue'>",
  "icp_match": <true|false>,
  "reason": "<explication concise en français, max 150 mots>"
}

Critères de scoring :
- 90-100 : Coach francophone actif, audience engagée, contenu clair sur l'offre
- 70-89  : Probable coach, signes forts mais quelques doutes
- 40-69  : Créateur de contenu dans la niche mais pas clairement coach
- 0-39   : Hors cible (anglophone dominant, autre activité, compte inactif)

icp_match = true uniquement si score >= 70."""


def _build_user_prompt(profile: dict) -> str:
    posts_text = "\n".join(
        f"  - Post {i+1}: {p['text'][:300]} (❤️ {p['likes']}, 💬 {p['comments']})"
        for i, p in enumerate(profile.get("posts", []))
    )
    return f"""Profil à analyser :
Plateforme : {profile['platform']}
Nom d'utilisateur : {profile['username']}
Bio : {profile['bio']}

Derniers posts :
{posts_text or '  (aucun post récupéré)'}

Qualifie ce lead."""


async def _call_claude_with_retry(prompt: str) -> str:
    delay = RETRY_BASE_DELAY
    last_exc: Optional[Exception] = None
    for attempt in range(RETRY_ATTEMPTS):
        try:
            response = await asyncio.to_thread(
                _client.messages.create,
                model=CLAUDE_MODEL,
                max_tokens=512,
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
    # Strip any accidental markdown fences
    raw = re.sub(r"```(?:json)?", "", raw).strip()
    return json.loads(raw)


async def qualify_lead(profile_url: str) -> dict:
    """
    Scrape + qualify a social profile.

    Returns:
        {
            profile_url, platform, username, bio, posts,
            score, niche, icp_match, reason, passed_threshold
        }
    """
    profile = await scrape_profile(profile_url)
    prompt = _build_user_prompt(profile)
    raw_output = await _call_claude_with_retry(prompt)
    qualification = _parse_json_output(raw_output)

    score = qualification.get("score", 0)
    return {
        "profile_url": profile_url,
        "platform": profile["platform"],
        "username": profile["username"],
        "bio": profile["bio"],
        "posts": profile["posts"],
        "score": score,
        "niche": qualification.get("niche", "inconnue"),
        "icp_match": qualification.get("icp_match", False),
        "reason": qualification.get("reason", ""),
        "passed_threshold": score >= QUALIFIER_SCORE_THRESHOLD,
    }
