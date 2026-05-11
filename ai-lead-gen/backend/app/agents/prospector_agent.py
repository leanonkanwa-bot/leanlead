"""
Prospector Agent
Finds potential coaching clients across Instagram, TikTok, LinkedIn, Twitter/X, and Reddit
using DuckDuckGo HTML search for free, then enriches profiles with snippet-as-posts-summary.
"""
import json
import os
import re
import time

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

SUPPORTED_PLATFORMS = ("instagram", "tiktok", "linkedin", "twitter", "reddit")

_RESERVED = {"explore", "accounts", "reels", "p", "stories", "reel", "tv", "tags", "search", "trending"}


# ---------------------------------------------------------------------------
# DuckDuckGo search (snippet extraction)
# ---------------------------------------------------------------------------

def _search_ddg(query: str, max_results: int = 20) -> list[dict]:
    """
    Query DuckDuckGo HTML and return list of {url, title, snippet}.
    Snippets often contain actual post/bio text — used as posts_summary.
    """
    try:
        resp = httpx.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers=BROWSER_HEADERS,
            timeout=20,
            follow_redirects=True,
        )
        resp.raise_for_status()
    except Exception:
        return []

    results = []
    # Extract result blocks
    for block in re.findall(
        r'<div class="result__body">(.*?)</div>\s*</div>',
        resp.text,
        re.DOTALL,
    )[:max_results * 2]:
        url_m = re.search(r'href="([^"]+)"', block)
        title_m = re.search(r'class="result__title"[^>]*>.*?<a[^>]*>(.*?)</a>', block, re.DOTALL)
        snip_m = re.search(r'class="result__snippet"[^>]*>(.*?)</span>', block, re.DOTALL)
        if url_m:
            results.append({
                "url": url_m.group(1),
                "title": re.sub(r"<[^>]+>", "", title_m.group(1)).strip() if title_m else "",
                "snippet": re.sub(r"<[^>]+>", "", snip_m.group(1)).strip() if snip_m else "",
            })
        if len(results) >= max_results:
            break
    return results


# ---------------------------------------------------------------------------
# Platform-specific profile fetchers
# ---------------------------------------------------------------------------

def _fetch_instagram(handle: str) -> dict:
    url = f"https://www.instagram.com/{handle}/"
    fallback = {"platform": "instagram", "handle": handle, "name": handle,
                "profile_url": url, "bio": "", "followers": 0, "posts_summary": ""}
    try:
        api_headers = {**BROWSER_HEADERS, "x-ig-app-id": "936619743392459", "Accept": "application/json"}
        resp = httpx.get(
            "https://i.instagram.com/api/v1/users/web_profile_info/",
            params={"username": handle}, headers=api_headers, timeout=15, follow_redirects=True,
        )
        if resp.status_code == 200:
            user = resp.json()["data"]["user"]
            return {
                "platform": "instagram", "handle": handle,
                "name": user.get("full_name", handle), "profile_url": url,
                "bio": user.get("biography", ""),
                "followers": (user.get("edge_followed_by") or {}).get("count", 0),
                "posts_summary": "",
            }
    except Exception:
        pass
    # HTML fallback
    try:
        resp = httpx.get(url, headers=BROWSER_HEADERS, timeout=15, follow_redirects=True)
        resp.raise_for_status()
        bio = (re.search(r'"biography":"(.*?)"', resp.text) or type("", (), {"group": lambda *a: ""})()).group(1)
        name = (re.search(r'"full_name":"(.*?)"', resp.text) or type("", (), {"group": lambda *a: handle})()).group(1)
        fc = re.search(r'"edge_followed_by":\{"count":(\d+)\}', resp.text)
        return {"platform": "instagram", "handle": handle, "name": name, "profile_url": url,
                "bio": bio, "followers": int(fc.group(1)) if fc else 0, "posts_summary": ""}
    except Exception:
        return fallback


def _fetch_tiktok(handle: str) -> dict:
    url = f"https://www.tiktok.com/@{handle}"
    fallback = {"platform": "tiktok", "handle": handle, "name": handle,
                "profile_url": url, "bio": "", "followers": 0, "posts_summary": ""}
    try:
        resp = httpx.get(url, headers=BROWSER_HEADERS, timeout=15, follow_redirects=True)
        resp.raise_for_status()
        m = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', resp.text, re.DOTALL)
        if not m:
            return fallback
        data = json.loads(m.group(1))
        user_info = data["__DEFAULT_SCOPE__"]["webapp.user-detail"]["userInfo"]
        user, stats = user_info["user"], user_info["stats"]
        return {
            "platform": "tiktok", "handle": handle,
            "name": user.get("nickname", handle), "profile_url": url,
            "bio": user.get("signature", ""),
            "followers": stats.get("followerCount", 0), "posts_summary": "",
        }
    except Exception:
        return fallback


def _fetch_linkedin_from_snippet(handle: str, title: str, snippet: str) -> dict:
    url = f"https://www.linkedin.com/in/{handle}/"
    return {
        "platform": "linkedin", "handle": handle,
        "name": title.replace(" | LinkedIn", "").split(" - ")[0].strip() or handle,
        "profile_url": url,
        "bio": snippet[:400],
        "followers": 0,
        "posts_summary": snippet,
    }


def _fetch_twitter_from_snippet(handle: str, title: str, snippet: str) -> dict:
    url = f"https://twitter.com/{handle}"
    name = re.sub(r'\(@[^)]+\)', '', title).replace("on Twitter", "").replace("on X", "").strip()
    return {
        "platform": "twitter", "handle": handle,
        "name": name or handle, "profile_url": url,
        "bio": snippet[:400], "followers": 0,
        "posts_summary": snippet,
    }


def _fetch_reddit_from_snippet(handle: str, title: str, snippet: str) -> dict:
    url = f"https://www.reddit.com/user/{handle}"
    return {
        "platform": "reddit", "handle": handle,
        "name": handle, "profile_url": url,
        "bio": "",
        "followers": 0,
        "posts_summary": snippet,
    }


# ---------------------------------------------------------------------------
# Platform-specific DDG searches
# ---------------------------------------------------------------------------

def _search_instagram(hashtag: str, max_results: int) -> list[dict]:
    results = _search_ddg(f'site:instagram.com "{hashtag}"', max_results * 3)
    seen: set[str] = set()
    profiles: list[dict] = []
    for r in results:
        m = re.search(r'instagram\.com/([A-Za-z0-9_.]{2,30})(?:/|\?|")', r["url"] + '"')
        if not m:
            continue
        handle = m.group(1).lower()
        if handle in _RESERVED or handle in seen:
            continue
        seen.add(handle)
        profile = _fetch_instagram(handle)
        if r["snippet"]:
            profile["posts_summary"] = r["snippet"]
        profiles.append(profile)
        if len(profiles) >= max_results:
            break
    return profiles


def _search_tiktok(hashtag: str, max_results: int) -> list[dict]:
    results = _search_ddg(f'site:tiktok.com "@{hashtag}"', max_results * 3)
    seen: set[str] = set()
    profiles: list[dict] = []
    for r in results:
        m = re.search(r'tiktok\.com/@([A-Za-z0-9_.]{2,30})', r["url"])
        if not m:
            continue
        handle = m.group(1).lower()
        if handle in seen:
            continue
        seen.add(handle)
        profile = _fetch_tiktok(handle)
        if r["snippet"]:
            profile["posts_summary"] = r["snippet"]
        profiles.append(profile)
        if len(profiles) >= max_results:
            break
    return profiles


def _search_linkedin(keyword: str, max_results: int) -> list[dict]:
    results = _search_ddg(f'site:linkedin.com/in "{keyword}"', max_results * 3)
    seen: set[str] = set()
    profiles: list[dict] = []
    for r in results:
        m = re.search(r'linkedin\.com/in/([A-Za-z0-9_-]{2,60})(?:/|\?|$)', r["url"])
        if not m:
            continue
        handle = m.group(1).lower()
        if handle in seen:
            continue
        seen.add(handle)
        profiles.append(_fetch_linkedin_from_snippet(handle, r["title"], r["snippet"]))
        if len(profiles) >= max_results:
            break
    return profiles


def _search_twitter(keyword: str, max_results: int) -> list[dict]:
    results = _search_ddg(
        f'(site:twitter.com OR site:x.com) "{keyword}" -filter:links',
        max_results * 3,
    )
    seen: set[str] = set()
    profiles: list[dict] = []
    for r in results:
        m = re.search(r'(?:twitter|x)\.com/([A-Za-z0-9_]{1,15})(?:/|\?|$)', r["url"])
        if not m:
            continue
        handle = m.group(1).lower()
        if handle in seen or handle in {"search", "home", "explore", "i", "intent"}:
            continue
        seen.add(handle)
        profiles.append(_fetch_twitter_from_snippet(handle, r["title"], r["snippet"]))
        if len(profiles) >= max_results:
            break
    return profiles


def _search_reddit(subreddit: str, max_results: int) -> list[dict]:
    sub = subreddit.lstrip("r/")
    results = _search_ddg(f'site:reddit.com/r/{sub}', max_results * 3)
    seen: set[str] = set()
    profiles: list[dict] = []
    for r in results:
        # Extract u/username from URL or snippet
        m = re.search(r'reddit\.com/u(?:ser)?/([A-Za-z0-9_-]{3,30})', r["url"] + " " + r["snippet"])
        if not m:
            # Try to extract from title "Posted by u/username"
            m2 = re.search(r'u/([A-Za-z0-9_-]{3,30})', r["snippet"])
            if not m2:
                continue
            handle = m2.group(1).lower()
        else:
            handle = m.group(1).lower()
        if handle in seen or handle in {"automoderator", "deleted", "removed"}:
            continue
        seen.add(handle)
        profiles.append(_fetch_reddit_from_snippet(handle, r["title"], r["snippet"]))
        if len(profiles) >= max_results:
            break
    return profiles


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
    Search for profiles across any supported platform.
    hashtags = hashtags (IG/TT), keywords (LI/TW), or subreddits (Reddit).
    """
    if platform not in SUPPORTED_PLATFORMS:
        raise ValueError(f"Unsupported platform: {platform}. Use: {SUPPORTED_PLATFORMS}")

    search_fn = {
        "instagram": _search_instagram,
        "tiktok": _search_tiktok,
        "linkedin": _search_linkedin,
        "twitter": _search_twitter,
        "reddit": _search_reddit,
    }[platform]

    seen: set[str] = set()
    profiles: list[dict] = []

    for term in hashtags[:5]:
        per_term = max_results // len(hashtags[:5]) + 3
        found = search_fn(term, per_term)
        for p in found:
            handle = (p.get("handle") or "").lower()
            if not handle or handle in seen:
                continue
            seen.add(handle)
            profiles.append(p)
            if len(profiles) >= max_results:
                return profiles
        time.sleep(0.5)  # rate-limit DDG

    return profiles


def prospect_by_url(profile_url: str, **kwargs) -> dict:
    """Scrape a single profile URL."""
    url = profile_url.strip().rstrip("/")

    if "tiktok.com" in url:
        handle = url.split("@")[-1].split("?")[0] if "@" in url else url.split("/")[-1]
        return _fetch_tiktok(handle)
    elif "instagram.com" in url:
        handle = url.split("instagram.com/")[-1].split("/")[0].split("?")[0]
        return _fetch_instagram(handle)
    elif "linkedin.com" in url:
        m = re.search(r'linkedin\.com/in/([A-Za-z0-9_-]+)', url)
        handle = m.group(1) if m else url.split("/")[-1]
        results = _search_ddg(f'site:linkedin.com/in/{handle}', 3)
        r = results[0] if results else {"title": handle, "snippet": ""}
        return _fetch_linkedin_from_snippet(handle, r["title"], r["snippet"])
    elif "twitter.com" in url or "x.com" in url:
        m = re.search(r'(?:twitter|x)\.com/([A-Za-z0-9_]+)', url)
        handle = m.group(1) if m else url.split("/")[-1]
        results = _search_ddg(f'site:twitter.com/{handle} OR site:x.com/{handle}', 3)
        r = results[0] if results else {"title": handle, "snippet": ""}
        return _fetch_twitter_from_snippet(handle, r["title"], r["snippet"])
    elif "reddit.com" in url:
        m = re.search(r'reddit\.com/u(?:ser)?/([A-Za-z0-9_-]+)', url)
        handle = m.group(1) if m else url.split("/")[-1]
        return _fetch_reddit_from_snippet(handle, handle, "")
    else:
        handle = url.split("/")[-1].split("?")[0].lstrip("@")
        return {
            "platform": "unknown", "handle": handle.lower(), "name": handle,
            "profile_url": url, "bio": "", "followers": 0, "posts_summary": "",
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

CRITICAL: Return terms used by POTENTIAL CLIENTS (people who have the pain), NOT by coaches.
Return ONLY a JSON array of strings, no explanation:
["term1", "term2", ...]""",
        }],
    )
    text = msg.content[0].text
    start, end = text.find("["), text.rfind("]") + 1
    return json.loads(text[start:end])
