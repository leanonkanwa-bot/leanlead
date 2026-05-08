"""
Prospector Agent
Uses free httpx scraping to find Instagram / TikTok profiles from hashtags,
then batches them for qualification.
"""
import json
import os
import re

import httpx

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Referer": "https://www.google.com/",
}

_RESERVED = {"explore", "accounts", "reels", "p", "stories", "reel", "tv", "tags"}


# ---------------------------------------------------------------------------
# Platform scrapers
# ---------------------------------------------------------------------------

def scrape_tiktok_profile(handle: str) -> dict:
    """Scrape a TikTok profile page and return a normalized dict."""
    url = f"https://www.tiktok.com/@{handle}"
    fallback = {
        "platform": "tiktok",
        "handle": handle,
        "name": handle,
        "profile_url": url,
        "bio": "",
        "followers": 0,
        "posts_summary": "",
    }
    try:
        resp = httpx.get(url, headers=BROWSER_HEADERS, timeout=15, follow_redirects=True)
        resp.raise_for_status()
        m = re.search(
            r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>',
            resp.text,
            re.DOTALL,
        )
        if not m:
            return fallback
        data = json.loads(m.group(1))
        user_info = data["__DEFAULT_SCOPE__"]["webapp.user-detail"]["userInfo"]
        user = user_info["user"]
        stats = user_info["stats"]
        return {
            "platform": "tiktok",
            "handle": handle,
            "name": user.get("nickname", handle),
            "profile_url": url,
            "bio": user.get("signature", ""),
            "followers": stats.get("followerCount", 0),
            "posts_summary": "",
        }
    except Exception:
        return fallback


def scrape_instagram_profile(handle: str) -> dict:
    """Scrape an Instagram profile and return a normalized dict."""
    url = f"https://www.instagram.com/{handle}/"
    fallback = {
        "platform": "instagram",
        "handle": handle,
        "name": handle,
        "profile_url": url,
        "bio": "",
        "followers": 0,
        "posts_summary": "",
    }
    # Primary: private API endpoint
    try:
        api_headers = {
            **BROWSER_HEADERS,
            "x-ig-app-id": "936619743392459",
            "Accept": "application/json",
        }
        resp = httpx.get(
            "https://i.instagram.com/api/v1/users/web_profile_info/",
            params={"username": handle},
            headers=api_headers,
            timeout=15,
            follow_redirects=True,
        )
        if resp.status_code == 200:
            data = resp.json()
            user = data["data"]["user"]
            return {
                "platform": "instagram",
                "handle": handle,
                "name": user.get("full_name", handle),
                "profile_url": url,
                "bio": user.get("biography", ""),
                "followers": (user.get("edge_followed_by") or {}).get("count", 0),
                "posts_summary": "",
            }
    except Exception:
        pass

    # Fallback: plain HTML scrape
    try:
        resp = httpx.get(url, headers=BROWSER_HEADERS, timeout=15, follow_redirects=True)
        resp.raise_for_status()
        # Try to extract JSON from page source
        m = re.search(r'"biography":"(.*?)"', resp.text)
        bio = m.group(1) if m else ""
        m2 = re.search(r'"full_name":"(.*?)"', resp.text)
        name = m2.group(1) if m2 else handle
        m3 = re.search(r'"edge_followed_by":\{"count":(\d+)\}', resp.text)
        followers = int(m3.group(1)) if m3 else 0
        return {
            "platform": "instagram",
            "handle": handle,
            "name": name,
            "profile_url": url,
            "bio": bio,
            "followers": followers,
            "posts_summary": "",
        }
    except Exception:
        return fallback


# ---------------------------------------------------------------------------
# DDG handle search
# ---------------------------------------------------------------------------

def _search_ddg_handles(platform: str, hashtag: str, max_results: int) -> list[str]:
    """Search DuckDuckGo HTML for social media handles mentioning a hashtag."""
    if platform == "tiktok":
        q = f'site:tiktok.com "@{hashtag}"'
        pattern = r'tiktok\.com/@([A-Za-z0-9_.]{2,30})'
    else:
        q = f'site:instagram.com "{hashtag}"'
        pattern = r'instagram\.com/([A-Za-z0-9_.]{2,30})(?:/|\?|")'

    try:
        resp = httpx.get(
            "https://html.duckduckgo.com/html/",
            params={"q": q},
            headers=BROWSER_HEADERS,
            timeout=15,
            follow_redirects=True,
        )
        resp.raise_for_status()
        raw_handles = re.findall(pattern, resp.text)
    except Exception:
        return []

    seen: set[str] = set()
    handles: list[str] = []
    for h in raw_handles:
        hl = h.lower()
        if hl not in _RESERVED and hl not in seen:
            seen.add(hl)
            handles.append(h)
        if len(handles) >= max_results:
            break
    return handles


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def prospect(
    platform: str,
    hashtags: list[str],
    max_results: int,
    **kwargs,
) -> list[dict]:
    """
    Scrape profiles from Instagram or TikTok matching the given hashtags.
    Returns normalized profile dicts ready to insert as leads.
    """
    if platform not in ("instagram", "tiktok"):
        raise ValueError(f"Unsupported platform: {platform}")

    scrape_fn = scrape_tiktok_profile if platform == "tiktok" else scrape_instagram_profile

    seen: set[str] = set()
    profiles: list[dict] = []

    for hashtag in hashtags[:3]:
        per_tag = max_results // 3 + 2
        handles = _search_ddg_handles(platform, hashtag, per_tag)
        for handle in handles:
            hl = handle.lower()
            if hl in seen:
                continue
            seen.add(hl)
            profile = scrape_fn(handle)
            profiles.append(profile)
            if len(profiles) >= max_results:
                return profiles

    return profiles


def prospect_by_url(profile_url: str, **kwargs) -> dict:
    """
    Extract a normalized profile dict from a single TikTok or Instagram URL.
    """
    url = profile_url.strip().rstrip("/")

    if "tiktok.com" in url:
        platform = "tiktok"
        handle = url.split("@")[-1].split("?")[0] if "@" in url else url.split("/")[-1]
    elif "instagram.com" in url:
        platform = "instagram"
        handle = url.split("instagram.com/")[-1].split("/")[0].split("?")[0]
    else:
        platform = "unknown"
        handle = url.split("/")[-1].split("?")[0].lstrip("@")

    if platform == "tiktok":
        return scrape_tiktok_profile(handle)
    elif platform == "instagram":
        return scrape_instagram_profile(handle)
    else:
        return {
            "platform": platform,
            "handle": handle.lower(),
            "name": handle,
            "profile_url": url,
            "bio": "",
            "followers": 0,
            "posts_summary": "",
        }


def suggest_hashtags(
    niche: str,
    target_audience: str,
    icp_pain_points: list[str] | None = None,
) -> list[str]:
    """Use Claude to generate pain-expression hashtags — people living the problem, not the solution."""
    import anthropic

    pain_block = ""
    if icp_pain_points:
        formatted = "\n".join(f"  - {p}" for p in icp_pain_points)
        pain_block = f"\nPains the coach's ideal client typically expresses:\n{formatted}\n"

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    msg = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=256,
        messages=[
            {
                "role": "user",
                "content": f"""Suggest 8 Instagram/TikTok hashtags that people use when they are VENTING, STRUGGLING, or EXPRESSING the problem that the coach below helps solve.

Coach niche: {niche}
Target audience: {target_audience}{pain_block}

IMPORTANT: These hashtags should be used by POTENTIAL CLIENTS who are LIVING the problem — NOT by coaches, consultants, or solution-providers. Think about what someone in pain would post, not what a coach would post.

Return ONLY a JSON array of hashtag strings (without the # symbol), no explanation:
["hashtag1", "hashtag2", ...]""",
            }
        ],
    )
    text = msg.content[0].text
    start, end = text.find("["), text.rfind("]") + 1
    return json.loads(text[start:end])
