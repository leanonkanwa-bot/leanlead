"""
Prospector Agent
Uses Apify to scrape Instagram / TikTok profiles from hashtags or keywords,
then batches them for qualification.
"""
import json
import os
import time

import httpx

APIFY_BASE = "https://api.apify.com/v2"

# Apify actor IDs
ACTORS = {
    "instagram": "apify/instagram-scraper",
    "tiktok": "clockworks/tiktok-scraper",
}


def _api_key(override: str | None = None) -> str:
    key = override or os.getenv("APIFY_API_KEY", "")
    if not key:
        raise ValueError("No Apify API key configured. Add it in Settings.")
    return key


def _start_run(actor_id: str, input_data: dict, api_key: str) -> str:
    """Start an Apify actor run. Returns run_id."""
    resp = httpx.post(
        f"{APIFY_BASE}/acts/{actor_id}/runs",
        json={"input": input_data},
        params={"token": api_key},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["data"]["id"]


def _wait_for_run(run_id: str, api_key: str, timeout: int = 300) -> str:
    """Poll until run finishes. Returns dataset_id."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = httpx.get(
            f"{APIFY_BASE}/actor-runs/{run_id}",
            params={"token": api_key},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        status = data["status"]
        if status == "SUCCEEDED":
            return data["defaultDatasetId"]
        if status in ("FAILED", "ABORTED", "TIMED-OUT"):
            raise RuntimeError(f"Apify run {run_id} ended with status: {status}")
        time.sleep(8)
    raise TimeoutError(f"Apify run {run_id} did not complete within {timeout}s")


def _fetch_dataset(dataset_id: str, api_key: str, limit: int = 50) -> list[dict]:
    resp = httpx.get(
        f"{APIFY_BASE}/datasets/{dataset_id}/items",
        params={"token": api_key, "limit": limit, "clean": "true"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _normalize_instagram(item: dict) -> dict:
    return {
        "platform": "instagram",
        "name": item.get("fullName") or item.get("full_name") or "",
        "handle": item.get("username") or item.get("userName") or "",
        "profile_url": f"https://instagram.com/{item.get('username', '')}",
        "bio": item.get("biography") or item.get("bio") or "",
        "followers": item.get("followersCount") or item.get("followers") or 0,
        "posts_summary": _first_captions(item.get("latestPosts") or item.get("posts") or []),
    }


def _normalize_tiktok(item: dict) -> dict:
    return {
        "platform": "tiktok",
        "name": item.get("authorMeta", {}).get("name") or item.get("nickname") or "",
        "handle": item.get("authorMeta", {}).get("name") or item.get("uniqueId") or "",
        "profile_url": f"https://tiktok.com/@{item.get('uniqueId', '')}",
        "bio": item.get("authorMeta", {}).get("signature") or "",
        "followers": item.get("authorMeta", {}).get("fans") or 0,
        "posts_summary": item.get("text") or "",
    }


def _first_captions(posts: list, max_posts: int = 3) -> str:
    captions = []
    for p in posts[:max_posts]:
        cap = p.get("caption") or p.get("text") or ""
        if cap:
            captions.append(cap[:120])
    return " | ".join(captions)


def prospect(
    platform: str,
    hashtags: list[str],
    max_results: int,
    apify_api_key: str | None = None,
) -> list[dict]:
    """
    Scrape profiles from Instagram or TikTok matching the given hashtags.
    Returns normalized profile dicts ready to insert as leads.
    """
    key = _api_key(apify_api_key)
    actor = ACTORS.get(platform)
    if not actor:
        raise ValueError(f"Unsupported platform: {platform}")

    if platform == "instagram":
        input_data = {
            "hashtags": hashtags,
            "resultsLimit": max_results,
            "resultsType": "posts",
            "scrapePostsUntilDate": "",
        }
        normalize = _normalize_instagram
    else:
        input_data = {
            "hashtags": hashtags,
            "resultsPerPage": max_results,
        }
        normalize = _normalize_tiktok

    run_id = _start_run(actor, input_data, key)
    dataset_id = _wait_for_run(run_id, key)
    items = _fetch_dataset(dataset_id, key, limit=max_results)

    # Deduplicate by handle
    seen: set[str] = set()
    profiles: list[dict] = []
    for item in items:
        p = normalize(item)
        handle = p.get("handle", "").strip().lower()
        if handle and handle not in seen:
            seen.add(handle)
            profiles.append(p)

    return profiles


def prospect_by_url(profile_url: str, apify_api_key: str | None = None) -> dict:
    """
    Extract a normalized profile dict from a single TikTok or Instagram URL.
    Tries Apify first; falls back to URL-only parsing if no key or Apify fails.
    """
    url = profile_url.strip().rstrip("/")

    if "tiktok.com" in url:
        platform = "tiktok"
        handle = url.split("@")[-1].split("?")[0] if "@" in url else url.split("/")[-1]
    elif "instagram.com" in url:
        platform = "instagram"
        handle = url.split("instagram.com/")[-1].split("/")[0].split("?")[0]
    else:
        # Generic fallback
        platform = "unknown"
        handle = url.split("/")[-1].split("?")[0].lstrip("@")

    base_profile = {
        "platform": platform,
        "handle": handle.lower(),
        "name": handle,
        "profile_url": url,
        "bio": "",
        "followers": 0,
        "posts_summary": "",
    }

    if not apify_api_key:
        try:
            apify_api_key = _api_key()
        except ValueError:
            return base_profile

    try:
        if platform == "tiktok":
            input_data = {"profiles": [f"https://www.tiktok.com/@{handle}"], "resultsPerPage": 5}
            actor = "clockworks/tiktok-scraper"
            run_id = _start_run(actor, input_data, apify_api_key)
            dataset_id = _wait_for_run(run_id, apify_api_key, timeout=120)
            items = _fetch_dataset(dataset_id, apify_api_key, limit=5)
            if items:
                item = items[0]
                meta = item.get("authorMeta", {})
                base_profile.update({
                    "name": meta.get("name") or handle,
                    "bio": meta.get("signature") or "",
                    "followers": meta.get("fans") or 0,
                    "posts_summary": " | ".join(
                        i.get("text", "")[:120] for i in items[:3] if i.get("text")
                    ),
                })
        elif platform == "instagram":
            input_data = {"usernames": [handle], "resultsLimit": 1}
            actor = "apify/instagram-scraper"
            run_id = _start_run(actor, input_data, apify_api_key)
            dataset_id = _wait_for_run(run_id, apify_api_key, timeout=120)
            items = _fetch_dataset(dataset_id, apify_api_key, limit=1)
            if items:
                item = items[0]
                base_profile.update({
                    "name": item.get("fullName") or handle,
                    "bio": item.get("biography") or "",
                    "followers": item.get("followersCount") or 0,
                    "posts_summary": _first_captions(item.get("latestPosts") or []),
                })
    except Exception:
        pass  # return what we have

    return base_profile


def suggest_hashtags(niche: str, target_audience: str) -> list[str]:
    """Use Claude to generate relevant hashtags for prospecting."""
    import anthropic

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    msg = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=256,
        messages=[
            {
                "role": "user",
                "content": f"""Suggest 8 Instagram/TikTok hashtags for finding ideal coaching clients.

Coach niche: {niche}
Target audience: {target_audience}

Return ONLY a JSON array of hashtag strings (without the # symbol), no explanation:
["hashtag1", "hashtag2", ...]""",
            }
        ],
    )
    text = msg.content[0].text
    start, end = text.find("["), text.rfind("]") + 1
    return json.loads(text[start:end])
