"""Apify-based scraper for TikTok, Instagram, and YouTube profiles."""

import asyncio
import httpx
from typing import Optional
from config import APIFY_API_KEY, RETRY_ATTEMPTS, RETRY_BASE_DELAY

APIFY_BASE = "https://api.apify.com/v2"

ACTOR_MAP = {
    "tiktok": "clockworks/free-tiktok-scraper",
    "instagram": "apify/instagram-scraper",
    "youtube": "streamers/youtube-scraper",
}


def _detect_platform(url: str) -> str:
    url_lower = url.lower()
    if "tiktok.com" in url_lower:
        return "tiktok"
    if "instagram.com" in url_lower:
        return "instagram"
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "youtube"
    raise ValueError(f"Unsupported platform for URL: {url}")


async def _run_actor(client: httpx.AsyncClient, actor_id: str, input_data: dict) -> dict:
    headers = {"Content-Type": "application/json"}
    params = {"token": APIFY_API_KEY}

    run_url = f"{APIFY_BASE}/acts/{actor_id}/runs"
    resp = await client.post(run_url, json=input_data, params=params, timeout=30)
    resp.raise_for_status()
    run_id = resp.json()["data"]["id"]

    # Poll until finished (max 120 s)
    for _ in range(24):
        await asyncio.sleep(5)
        status_resp = await client.get(
            f"{APIFY_BASE}/actor-runs/{run_id}", params=params, timeout=15
        )
        status_resp.raise_for_status()
        status = status_resp.json()["data"]["status"]
        if status == "SUCCEEDED":
            break
        if status in ("FAILED", "ABORTED", "TIMED-OUT"):
            raise RuntimeError(f"Apify actor run {run_id} ended with status: {status}")

    dataset_id = status_resp.json()["data"]["defaultDatasetId"]
    items_resp = await client.get(
        f"{APIFY_BASE}/datasets/{dataset_id}/items",
        params={**params, "limit": 6},
        timeout=15,
    )
    items_resp.raise_for_status()
    return items_resp.json()


async def _with_retry(coro_fn, *args, **kwargs):
    delay = RETRY_BASE_DELAY
    last_exc: Optional[Exception] = None
    for attempt in range(RETRY_ATTEMPTS):
        try:
            return await coro_fn(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            if attempt < RETRY_ATTEMPTS - 1:
                await asyncio.sleep(delay)
                delay *= 2
    raise last_exc


async def scrape_profile(url: str) -> dict:
    """Return { platform, bio, username, posts: [{ text, likes, comments }] }."""
    platform = _detect_platform(url)
    actor_id = ACTOR_MAP[platform]

    if platform == "tiktok":
        actor_input = {"profiles": [url], "resultsPerPage": 6, "shouldDownloadVideos": False}
    elif platform == "instagram":
        actor_input = {"directUrls": [url], "resultsType": "posts", "resultsLimit": 6}
    else:
        actor_input = {"startUrls": [{"url": url}], "maxResults": 6}

    async with httpx.AsyncClient() as client:
        items = await _with_retry(_run_actor, client, actor_id, actor_input)

    if not items:
        return {"platform": platform, "bio": "", "username": "", "posts": []}

    profile_item = items[0]
    bio = (
        profile_item.get("biography")
        or profile_item.get("bio")
        or profile_item.get("description")
        or ""
    )
    username = (
        profile_item.get("username")
        or profile_item.get("authorMeta", {}).get("name")
        or profile_item.get("channelName")
        or ""
    )

    posts = []
    for item in items[:5]:
        text = (
            item.get("text")
            or item.get("caption")
            or item.get("title")
            or item.get("description")
            or ""
        )
        posts.append(
            {
                "text": text[:500],
                "likes": item.get("likesCount") or item.get("likes") or 0,
                "comments": item.get("commentsCount") or item.get("comments") or 0,
            }
        )

    return {"platform": platform, "bio": bio[:800], "username": username, "posts": posts}
