"""
Prospector Agent v2
Finds potential coaching clients on Instagram and TikTok using:
  1. ddgs package (DuckDuckGo) — primary search
  2. Direct hashtag page scraping (Instagram + TikTok) — fallback
  3. Instagram profile API — profile enrichment

No API keys required.
"""
import json
import os
import re
import time
import random

import httpx
from bs4 import BeautifulSoup

# ── HTTP helpers ───────────────────────────────────────────────────────────────

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]


def _hdrs(extra: dict | None = None) -> dict:
    base = {
        "User-Agent": random.choice(_USER_AGENTS),
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    if extra:
        base.update(extra)
    return base


SUPPORTED_PLATFORMS = ("instagram", "tiktok", "linkedin", "twitter", "reddit")

_IG_RESERVED = frozenset({
    "explore", "accounts", "reels", "p", "stories", "reel", "tv", "tags",
    "search", "trending", "about", "developer", "legal", "help", "press",
    "privacy", "safety", "api", "oauth", "graphql", "static", "cdn",
})

_TT_RESERVED = frozenset({
    "tag", "trending", "foryou", "following", "friends", "live",
    "discover", "search", "explore", "challenge",
})


# ── DuckDuckGo search ──────────────────────────────────────────────────────────

def _ddg_search(query: str, max_results: int = 30) -> list[dict]:
    """
    Search via the ddgs package. Returns list of {url, title, snippet}.
    Falls back to empty list on any error.
    """
    try:
        from ddgs import DDGS
        with DDGS() as ddg:
            raw = list(ddg.text(query, max_results=max_results))
        results = [
            {"url": r.get("href", ""), "title": r.get("title", ""), "snippet": r.get("body", "")}
            for r in raw if r.get("href")
        ]
        print(f"[prospector] ddgs '{query[:60]}' → {len(results)} hits")
        return results
    except Exception as exc:
        print(f"[prospector] ddgs error for '{query[:60]}': {exc}")
        return []


# ── Instagram ──────────────────────────────────────────────────────────────────

def _ig_api(handle: str) -> dict | None:
    """Fetch profile via Instagram's unofficial mobile API."""
    try:
        resp = httpx.get(
            "https://i.instagram.com/api/v1/users/web_profile_info/",
            params={"username": handle},
            headers=_hdrs({"x-ig-app-id": "936619743392459", "Accept": "application/json"}),
            timeout=12,
            follow_redirects=True,
        )
        if resp.status_code != 200:
            return None
        user = resp.json()["data"]["user"]
        # Extract last 3 post captions
        caps = []
        try:
            edges = user.get("edge_owner_to_timeline_media", {}).get("edges", [])
            for e in edges[:3]:
                cap_edges = e["node"].get("edge_media_to_caption", {}).get("edges", [])
                if cap_edges:
                    caps.append(cap_edges[0]["node"].get("text", "")[:150])
        except Exception:
            pass
        return {
            "platform": "instagram",
            "handle": handle,
            "name": user.get("full_name") or handle,
            "profile_url": f"https://www.instagram.com/{handle}/",
            "bio": user.get("biography", ""),
            "followers": (user.get("edge_followed_by") or {}).get("count", 0),
            "posts_summary": " | ".join(c for c in caps if c),
        }
    except Exception:
        return None


def _ig_html(handle: str) -> dict | None:
    """Fallback: scrape Instagram profile page HTML."""
    url = f"https://www.instagram.com/{handle}/"
    try:
        resp = httpx.get(url, headers=_hdrs(), timeout=12, follow_redirects=True)
        if resp.status_code != 200:
            return None
        html = resp.text
        bio_m = re.search(r'"biography":"(.*?)"', html)
        name_m = re.search(r'"full_name":"(.*?)"', html)
        fc_m = re.search(r'"edge_followed_by":\{"count":(\d+)\}', html)
        bio = bio_m.group(1).encode().decode("unicode_escape") if bio_m else ""
        return {
            "platform": "instagram",
            "handle": handle,
            "name": name_m.group(1) if name_m else handle,
            "profile_url": url,
            "bio": bio,
            "followers": int(fc_m.group(1)) if fc_m else 0,
            "posts_summary": "",
        }
    except Exception:
        return None


def _fetch_instagram(handle: str) -> dict:
    fallback = {
        "platform": "instagram", "handle": handle, "name": handle,
        "profile_url": f"https://www.instagram.com/{handle}/",
        "bio": "", "followers": 0, "posts_summary": "",
    }
    return _ig_api(handle) or _ig_html(handle) or fallback


def _ig_hashtag_page(hashtag: str, limit: int, seen: set) -> list[dict]:
    """
    Scrape Instagram's public explore/tags page.
    Extracts usernames from embedded JSON (application/json script tags)
    and from raw HTML username patterns.
    """
    url = f"https://www.instagram.com/explore/tags/{hashtag}/"
    profiles: list[dict] = []
    try:
        resp = httpx.get(url, headers=_hdrs(), timeout=15, follow_redirects=True)
        if resp.status_code != 200:
            print(f"[prospector] IG tags page → {resp.status_code}")
            return []

        html = resp.text
        handles_found: list[str] = []

        # Method A: <script type="application/json"> embedded data
        soup = BeautifulSoup(html, "lxml")
        for script in soup.find_all("script", {"type": "application/json"}):
            try:
                data = json.loads(script.string or "")
                handles_found.extend(_extract_json_usernames(data, "username"))
            except Exception:
                continue

        # Method B: raw regex on full HTML
        handles_found.extend(re.findall(r'"username":"([A-Za-z0-9_.]{2,30})"', html))

        for h in handles_found:
            h = h.lower()
            if h in _IG_RESERVED or h in seen or len(h) < 2:
                continue
            seen.add(h)
            profile = _fetch_instagram(h)
            profiles.append(profile)
            print(f"[prospector] IG tag page @{h} followers={profile['followers']}")
            if len(profiles) >= limit:
                break
    except Exception as exc:
        print(f"[prospector] IG tag page error: {exc}")
    return profiles


def _search_instagram(hashtag: str, max_results: int) -> list[dict]:
    seen: set[str] = set()
    profiles: list[dict] = []
    tag = hashtag.lstrip("#")

    # Strategy 1: DDG search
    for query in [
        f'site:instagram.com "#{tag}"',
        f'site:instagram.com "{tag}"',
    ]:
        if len(profiles) >= max_results:
            break
        for r in _ddg_search(query, max_results * 3):
            m = re.search(r'instagram\.com/([A-Za-z0-9_.]{2,30})(?:/|\?|$)', r["url"])
            if not m:
                continue
            h = m.group(1).lower()
            if h in _IG_RESERVED or h in seen:
                continue
            seen.add(h)
            profile = _fetch_instagram(h)
            if r["snippet"] and not profile["posts_summary"]:
                profile["posts_summary"] = r["snippet"][:300]
            profiles.append(profile)
            print(f"[prospector] IG ddg @{h} followers={profile['followers']}")
            if len(profiles) >= max_results:
                return profiles
        time.sleep(1.5)

    # Strategy 2: direct hashtag page
    if len(profiles) < max_results:
        extra = _ig_hashtag_page(tag, max_results - len(profiles), seen)
        profiles.extend(extra)

    return profiles[:max_results]


# ── TikTok ─────────────────────────────────────────────────────────────────────

def _fetch_tiktok(handle: str) -> dict:
    url = f"https://www.tiktok.com/@{handle}"
    fallback = {
        "platform": "tiktok", "handle": handle, "name": handle,
        "profile_url": url, "bio": "", "followers": 0, "posts_summary": "",
    }
    try:
        resp = httpx.get(url, headers=_hdrs(), timeout=15, follow_redirects=True)
        if resp.status_code != 200:
            return fallback
        m = re.search(
            r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>',
            resp.text, re.DOTALL,
        )
        if not m:
            return fallback
        data = json.loads(m.group(1))
        user_info = data["__DEFAULT_SCOPE__"]["webapp.user-detail"]["userInfo"]
        user, stats = user_info["user"], user_info["stats"]
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


def _tt_hashtag_page(hashtag: str, limit: int, seen: set) -> list[dict]:
    """Scrape TikTok challenge/tag page for creator usernames."""
    url = f"https://www.tiktok.com/tag/{hashtag}"
    profiles: list[dict] = []
    try:
        resp = httpx.get(url, headers=_hdrs(), timeout=15, follow_redirects=True)
        if resp.status_code != 200:
            print(f"[prospector] TT tag page → {resp.status_code}")
            return []

        html = resp.text
        handles_found: list[str] = []

        m = re.search(
            r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>',
            html, re.DOTALL,
        )
        if m:
            try:
                data = json.loads(m.group(1))
                handles_found.extend(_extract_json_usernames(data, "uniqueId"))
            except Exception:
                pass

        # Fallback regex
        handles_found.extend(re.findall(r'"uniqueId":"([A-Za-z0-9_.]{2,30})"', html))

        for h in handles_found:
            h = h.lower()
            if h in _TT_RESERVED or h in seen or len(h) < 2:
                continue
            seen.add(h)
            profile = _fetch_tiktok(h)
            profiles.append(profile)
            print(f"[prospector] TT tag page @{h} followers={profile['followers']}")
            if len(profiles) >= limit:
                break
    except Exception as exc:
        print(f"[prospector] TT tag page error: {exc}")
    return profiles


def _search_tiktok(hashtag: str, max_results: int) -> list[dict]:
    seen: set[str] = set()
    profiles: list[dict] = []
    tag = hashtag.lstrip("#")

    for query in [
        f'site:tiktok.com "#{tag}"',
        f'site:tiktok.com "{tag}"',
    ]:
        if len(profiles) >= max_results:
            break
        for r in _ddg_search(query, max_results * 3):
            m = re.search(r'tiktok\.com/@([A-Za-z0-9_.]{2,30})', r["url"])
            if not m:
                continue
            h = m.group(1).lower()
            if h in _TT_RESERVED or h in seen:
                continue
            seen.add(h)
            profile = _fetch_tiktok(h)
            if r["snippet"] and not profile["posts_summary"]:
                profile["posts_summary"] = r["snippet"][:300]
            profiles.append(profile)
            print(f"[prospector] TT ddg @{h} followers={profile['followers']}")
            if len(profiles) >= max_results:
                return profiles
        time.sleep(1.5)

    if len(profiles) < max_results:
        profiles.extend(_tt_hashtag_page(tag, max_results - len(profiles), seen))

    return profiles[:max_results]


# ── LinkedIn / Twitter / Reddit (DDG-only) ─────────────────────────────────────

def _search_linkedin(keyword: str, max_results: int) -> list[dict]:
    seen: set[str] = set()
    profiles: list[dict] = []
    for r in _ddg_search(f'site:linkedin.com/in "{keyword}"', max_results * 3):
        m = re.search(r'linkedin\.com/in/([A-Za-z0-9_-]{2,60})(?:/|\?|$)', r["url"])
        if not m:
            continue
        h = m.group(1).lower()
        if h in seen:
            continue
        seen.add(h)
        name = r["title"].replace(" | LinkedIn", "").split(" - ")[0].strip() or h
        profiles.append({
            "platform": "linkedin", "handle": h, "name": name,
            "profile_url": f"https://www.linkedin.com/in/{h}/",
            "bio": r["snippet"][:400], "followers": 0, "posts_summary": r["snippet"],
        })
        if len(profiles) >= max_results:
            break
    return profiles


def _search_twitter(keyword: str, max_results: int) -> list[dict]:
    _skip = {"search", "home", "explore", "i", "intent", "settings", "notifications"}
    seen: set[str] = set()
    profiles: list[dict] = []
    for r in _ddg_search(f'(site:twitter.com OR site:x.com) "{keyword}"', max_results * 3):
        m = re.search(r'(?:twitter|x)\.com/([A-Za-z0-9_]{1,15})(?:/|\?|$)', r["url"])
        if not m:
            continue
        h = m.group(1).lower()
        if h in _skip or h in seen:
            continue
        seen.add(h)
        name = re.sub(r'\(@[^)]+\)', '', r["title"]).replace("on Twitter", "").replace("on X", "").strip()
        profiles.append({
            "platform": "twitter", "handle": h, "name": name or h,
            "profile_url": f"https://twitter.com/{h}",
            "bio": r["snippet"][:400], "followers": 0, "posts_summary": r["snippet"],
        })
        if len(profiles) >= max_results:
            break
    return profiles


def _search_reddit(subreddit: str, max_results: int) -> list[dict]:
    _skip = {"automoderator", "deleted", "removed"}
    sub = subreddit.lstrip("r/")
    seen: set[str] = set()
    profiles: list[dict] = []
    for r in _ddg_search(f'site:reddit.com/r/{sub}', max_results * 3):
        combined = r["url"] + " " + r["snippet"]
        m = re.search(r'reddit\.com/u(?:ser)?/([A-Za-z0-9_-]{3,30})', combined)
        if not m:
            m = re.search(r'u/([A-Za-z0-9_-]{3,30})', r["snippet"])
        if not m:
            continue
        h = m.group(1).lower()
        if h in _skip or h in seen:
            continue
        seen.add(h)
        profiles.append({
            "platform": "reddit", "handle": h, "name": h,
            "profile_url": f"https://www.reddit.com/user/{h}",
            "bio": "", "followers": 0, "posts_summary": r["snippet"],
        })
        if len(profiles) >= max_results:
            break
    return profiles


# ── JSON recursive username extractor ─────────────────────────────────────────

def _extract_json_usernames(data, key: str) -> list[str]:
    """Walk a nested JSON structure and collect all values for `key`."""
    found: list[str] = []
    if isinstance(data, dict):
        if key in data and isinstance(data[key], str) and 2 <= len(data[key]) <= 30:
            found.append(data[key])
        for v in data.values():
            found.extend(_extract_json_usernames(v, key))
    elif isinstance(data, list):
        for item in data:
            found.extend(_extract_json_usernames(item, key))
    return found


# ── Public API ─────────────────────────────────────────────────────────────────

def prospect(
    platform: str,
    hashtags: list[str],
    max_results: int,
    **kwargs,
) -> list[dict]:
    """
    Search for profiles matching the given hashtags/keywords on a platform.
    Uses DDG as primary source, platform hashtag pages as fallback.
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
    per_tag = max(max_results // max(len(hashtags[:5]), 1), 5)

    for term in hashtags[:5]:
        found = search_fn(term, per_tag + 5)
        for p in found:
            h = (p.get("handle") or "").lower()
            if not h or h in seen:
                continue
            seen.add(h)
            profiles.append(p)
            if len(profiles) >= max_results:
                return profiles
        time.sleep(0.5)

    return profiles


def prospect_by_url(profile_url: str, **kwargs) -> dict:
    """Scrape a single profile URL and return normalized profile dict."""
    url = profile_url.strip().rstrip("/")
    if "tiktok.com" in url:
        h = url.split("@")[-1].split("?")[0] if "@" in url else url.split("/")[-1]
        return _fetch_tiktok(h)
    if "instagram.com" in url:
        h = url.split("instagram.com/")[-1].split("/")[0].split("?")[0]
        return _fetch_instagram(h)
    if "linkedin.com" in url:
        m = re.search(r'linkedin\.com/in/([A-Za-z0-9_-]+)', url)
        h = m.group(1) if m else url.split("/")[-1]
        rs = _ddg_search(f'site:linkedin.com/in/{h}', 3)
        r = rs[0] if rs else {}
        return {"platform": "linkedin", "handle": h, "name": r.get("title", h),
                "profile_url": url, "bio": r.get("snippet", ""), "followers": 0, "posts_summary": r.get("snippet", "")}
    if "twitter.com" in url or "x.com" in url:
        m = re.search(r'(?:twitter|x)\.com/([A-Za-z0-9_]+)', url)
        h = m.group(1) if m else url.split("/")[-1]
        return {"platform": "twitter", "handle": h, "name": h,
                "profile_url": url, "bio": "", "followers": 0, "posts_summary": ""}
    if "reddit.com" in url:
        m = re.search(r'reddit\.com/u(?:ser)?/([A-Za-z0-9_-]+)', url)
        h = m.group(1) if m else url.split("/")[-1]
        return {"platform": "reddit", "handle": h, "name": h,
                "profile_url": url, "bio": "", "followers": 0, "posts_summary": ""}
    h = url.split("/")[-1].split("?")[0].lstrip("@")
    return {"platform": "unknown", "handle": h.lower(), "name": h,
            "profile_url": url, "bio": "", "followers": 0, "posts_summary": ""}


def suggest_hashtags(
    niche: str,
    target_audience: str,
    icp_pain_points: list[str] | None = None,
) -> list[str]:
    """Use Claude to generate pain-expression hashtags for prospecting."""
    import anthropic

    pain_block = ""
    if icp_pain_points:
        formatted = "\n".join(f"  - {p}" for p in icp_pain_points)
        pain_block = f"\nPains the ICP typically expresses:\n{formatted}\n"

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    msg = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=256,
        messages=[{
            "role": "user",
            "content": f"""Suggest 8 Instagram/TikTok hashtags used by POTENTIAL CLIENTS who are venting about or living the problem the coach below solves.

Coach niche: {niche}
Target audience: {target_audience}{pain_block}

Return ONLY a JSON array, no explanation:
["term1", "term2", ...]""",
        }],
    )
    text = msg.content[0].text
    start, end = text.find("["), text.rfind("]") + 1
    return json.loads(text[start:end])
