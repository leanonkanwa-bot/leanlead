"""
Viral Post Hijacker Agent
Finds trending/viral posts in the coach's niche and extracts commenters
who are expressing pain signals — these are buyers already engaged with the topic.
"""
import logging
import re

import httpx

logger = logging.getLogger(__name__)

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.google.com/",
}

_RESERVED = {"explore", "accounts", "reels", "p", "stories", "reel", "tv", "tags", "about", "hashtag"}

# Keywords that indicate a real pain-expressing commenter (not just a fan)
_PAIN_COMMENT_RE = re.compile(
    r'\b('
    # French
    r'merci|comment (tu|vous|faire)|c\'est quoi|o[uù] trouver|combien|'
    r'int[ée]ress[ée]|comment commencer|j\'aimerais|j\'en peux plus|moi aussi|'
    r'pareil pour moi|c\'est exactement|je vis (la même|ça)|j\'ai v[ée]cu|'
    r'tu peux m\'aider|aide moi|j\'ai besoin|quelqu\'un qui|'
    # English
    r'thank you|how do you|what is|where can i|how much|interested|'
    r'amazing|same here|me too|this is exactly|i feel this|'
    r'can you help|i need|i\'ve been|how long did it take|'
    # Spanish / Portuguese
    r'gracias|c[oó]mo (lo haces|empezar)|cuanto|interesado|igual que yo|'
    r'obrigad[ao]|como (fazer|começ)|quanto custa|interessad[ao]'
    r')\b',
    re.IGNORECASE,
)


def _search_ddg(query: str, max_results: int = 20) -> list[dict]:
    """Return [{url, title, snippet}] from DuckDuckGo HTML search."""
    try:
        resp = httpx.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers=BROWSER_HEADERS,
            timeout=15,
            follow_redirects=True,
        )
        resp.raise_for_status()
    except Exception as e:
        logger.warning("DDG search failed for %r: %s", query, e)
        return []

    results: list[dict] = []
    snippets = re.findall(r'class="result__snippet">(.*?)</a>', resp.text, re.DOTALL)
    urls = re.findall(r'class="result__url"[^>]*>(.*?)</a>', resp.text, re.DOTALL)
    titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', resp.text, re.DOTALL)

    for i, snippet in enumerate(snippets[:max_results]):
        clean = re.sub(r'<[^>]+>', '', snippet).strip()
        url = re.sub(r'<[^>]+>', '', urls[i]).strip() if i < len(urls) else ""
        title = re.sub(r'<[^>]+>', '', titles[i]).strip() if i < len(titles) else ""
        results.append({"url": url, "title": title, "snippet": clean})

    return results


def scan_viral_posts(
    niche: str,
    platform: str = "instagram",
    max_commenters: int = 30,
) -> list[dict]:
    """
    Search for viral/trending posts in the niche and extract people who
    commented with pain signals. Returns profiles ready for qualification.
    """
    site_map = {
        "instagram": "instagram.com",
        "tiktok": "tiktok.com",
        "twitter": "twitter.com",
        "reddit": "reddit.com",
    }
    site = site_map.get(platform, f"{platform}.com")

    # Build search queries targeting high-engagement posts in the niche
    queries = [
        f'site:{site} "{niche}" commentaires OR comments viral',
        f'site:{site} "{niche}" likes OR vues trending',
        f'"{niche}" site:{site} -coach -programme -formation',
    ]

    all_snippets: list[dict] = []
    for q in queries:
        all_snippets.extend(_search_ddg(q, max_results=15))

    profiles: list[dict] = []
    seen_handles: set[str] = set()

    for item in all_snippets:
        text = f"{item.get('title', '')} {item.get('snippet', '')}"

        # Only extract from snippets showing pain-expressing engagement
        if not _PAIN_COMMENT_RE.search(text):
            continue

        # Extract @mentions — these are the commenters
        mentioned = re.findall(r'@([a-zA-Z0-9_.]{3,30})', text)
        for m in mentioned:
            h = m.lower()
            if h in _RESERVED or h in seen_handles:
                continue
            seen_handles.add(h)

            profiles.append({
                "handle": h,
                "name": m,
                "platform": platform,
                "profile_url": f"https://{site}/{h}",
                "bio": "",
                "followers": 0,
                "posts_summary": (
                    f"Commenté sous un post viral sur '{niche}' ({platform}): "
                    + text[:250]
                ),
                "_source_tag": "viral_post",
            })

        if len(profiles) >= max_commenters:
            break

    return profiles[:max_commenters]
