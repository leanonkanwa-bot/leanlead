import json
import re
import time
from typing import Optional

import anthropic
import httpx

from config import (
    ANTHROPIC_API_KEY,
    APIFY_API_KEY,
    CLAUDE_MODEL,
    QUALIFIER_SCORE_THRESHOLD,
    RETRY_ATTEMPTS,
    RETRY_BASE_DELAY,
)

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

APIFY_BASE = "https://api.apify.com/v2"

ACTOR_MAP = {
    "instagram": "apify/instagram-scraper",
    "tiktok":    "clockworks/free-tiktok-scraper",
    "youtube":   "streamers/youtube-scraper",
}


def _detect_platform(url: str) -> str:
    u = url.lower()
    if "instagram.com" in u:
        return "instagram"
    if "tiktok.com" in u:
        return "tiktok"
    if "youtube.com" in u or "youtu.be" in u:
        return "youtube"
    raise ValueError(f"Plateforme non supportée : {url}")


def _actor_input(platform: str, url: str) -> dict:
    if platform == "instagram":
        return {"directUrls": [url], "resultsType": "posts", "resultsLimit": 5}
    if platform == "tiktok":
        return {"profiles": [url], "resultsPerPage": 5, "shouldDownloadVideos": False}
    # youtube
    return {"startUrls": [{"url": url}], "maxResults": 5}


def _extract_fields(platform: str, items: list) -> tuple[str, str, list]:
    """Return (username, bio, posts) from raw Apify items."""
    if not items:
        return "", "", []

    first = items[0]

    if platform == "instagram":
        username = first.get("ownerUsername") or first.get("username") or ""
        bio = first.get("biography") or first.get("bio") or ""
    elif platform == "tiktok":
        username = first.get("authorMeta", {}).get("name") or first.get("author") or ""
        bio = first.get("authorMeta", {}).get("signature") or ""
    else:
        username = first.get("channelName") or first.get("author") or ""
        bio = first.get("description") or ""

    posts = []
    for item in items[:5]:
        text = (
            item.get("caption")
            or item.get("text")
            or item.get("title")
            or item.get("description")
            or ""
        )
        posts.append({
            "text": text[:400],
            "likes": item.get("likesCount") or item.get("likes") or 0,
            "comments": item.get("commentsCount") or item.get("comments") or 0,
        })

    return username, bio[:700], posts


def scrape_profile(url: str) -> dict:
    """Call Apify run-sync endpoint and return normalized profile dict."""
    platform = _detect_platform(url)
    actor_id = ACTOR_MAP[platform]
    actor_input = _actor_input(platform, url)

    last_exc: Optional[Exception] = None
    delay = RETRY_BASE_DELAY

    for attempt in range(RETRY_ATTEMPTS):
        try:
            response = httpx.post(
                f"{APIFY_BASE}/acts/{actor_id}/run-sync-get-dataset-items",
                params={"token": APIFY_API_KEY},
                json=actor_input,
                timeout=90,
            )
            response.raise_for_status()
            items = response.json()
            username, bio, posts = _extract_fields(platform, items)
            return {
                "platform": platform,
                "username": username,
                "bio": bio,
                "posts": posts,
            }
        except (httpx.HTTPError, Exception) as exc:
            last_exc = exc
            if attempt < RETRY_ATTEMPTS - 1:
                time.sleep(delay)
                delay *= 2

    raise last_exc


def qualify_lead(url: str) -> dict:
    """Scrape + qualify a social profile. Returns full result dict."""
    raw_data = scrape_profile(url)

    posts_text = "\n".join(
        f"  - Post {i+1}: {p['text'][:300]} (❤️ {p['likes']}, 💬 {p['comments']})"
        for i, p in enumerate(raw_data["posts"])
    )

    prompt = f"""
Tu es un expert en qualification de leads pour coachs francophones.

Analyse ce profil social :
Plateforme : {raw_data['platform']}
Utilisateur : {raw_data['username']}
Bio : {raw_data['bio']}

Derniers posts :
{posts_text or '  (aucun post récupéré)'}

Réponds UNIQUEMENT en JSON valide, sans markdown :
{{
  "score": <int 0-100>,
  "niche": "<business|fitness|mindset|spirituel|autre>",
  "icp_match": <true|false>,
  "reason": "<explication courte>"
}}

Critères de scoring :
- Coach francophone actif : +40pts
- Audience engagée visible : +20pts
- Contenu orienté transformation : +20pts
- Offre ou service mentionné : +20pts

icp_match = true uniquement si score >= 70.
"""

    last_exc: Optional[Exception] = None
    delay = RETRY_BASE_DELAY

    for attempt in range(RETRY_ATTEMPTS):
        try:
            response = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = re.sub(r"```(?:json)?", "", response.content[0].text).strip()
            result = json.loads(raw)
            score = result.get("score", 0)
            return {
                "url": url,
                "platform": raw_data["platform"],
                "username": raw_data["username"],
                "bio": raw_data["bio"],
                "posts": raw_data["posts"],
                "score": score,
                "niche": result.get("niche", "autre"),
                "icp_match": result.get("icp_match", False),
                "reason": result.get("reason", ""),
                "passed_threshold": score >= QUALIFIER_SCORE_THRESHOLD,
            }
        except (anthropic.APIError, anthropic.APIConnectionError, json.JSONDecodeError) as exc:
            last_exc = exc
            if attempt < RETRY_ATTEMPTS - 1:
                time.sleep(delay)
                delay *= 2

    raise last_exc
