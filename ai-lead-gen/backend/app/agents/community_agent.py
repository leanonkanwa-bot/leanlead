"""
Community Infiltration Agent — mines untapped lead sources without posting.

Sources:
  1. Reddit/Facebook community posts  → pain signals in comment threads
  2. Google Reviews mining            → unhappy buyers of competitor coaches
  3. YouTube comment mining           → people asking "does this work?"

All via DuckDuckGo HTML search — no API keys required.
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

_PAIN_SIGNAL_RE = re.compile(
    r'\b('
    # French
    r'j\'en peux plus|j\'ai besoin d\'aide|aidez[- ]moi|je cherche|j\'ai essayé|'
    r'comment (vous|tu) (faites?|fais)|quelqu\'un peut|est-ce que ça marche|'
    r'je galère|c\'est possible|je veux changer|j\'ai du mal|je lutte|'
    r'quelqu\'un a essayé|j\'ai acheté|j\'ai payé|a pas fonctionné|'
    r'arnaque|arnaqu[ée]|escroquerie|pas de résultats|aucun résultat|'
    r'# English
    r'anyone tried|does this work|i need help|looking for advice|'
    r'struggling with|can\'t seem to|nothing works|wasted money|'
    r'got scammed|didn\'t work|no results|i tried everything|'
    r'how do you|is it possible|please help|someone help|'
    r'want to change|ready to change|stuck in'
    r')\b',
    re.IGNORECASE,
)

_FAILED_BUYER_RE = re.compile(
    r'\b('
    r'j\'ai (acheté|payé|investi).{0,40}(coach|formation|programme|cours)|'
    r'(formation|programme|coach).{0,40}(arnaque|marche pas|pas fonctionné|déçu|remboursement)|'
    r'wasted.{0,20}(money|€|\$)|paid.{0,20}(coach|program|course).{0,30}(didn\'t|not|no result)|'
    r'got scammed.{0,30}coach|coach.{0,30}scam|refund.{0,20}coach|'
    r'money back.{0,20}(program|coaching)|coaching.{0,30}waste'
    r')',
    re.IGNORECASE,
)

_HANDLE_RE = re.compile(r'u/([a-zA-Z0-9_]{3,30})|@([a-zA-Z0-9_.]{3,30})')
_REDDIT_USER_RE = re.compile(r'reddit\.com/u(?:ser)?/([a-zA-Z0-9_-]{3,30})')


def _search_ddg(query: str, max_results: int = 20) -> list[dict]:
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
    blocks = re.findall(
        r'class="result__body".*?class="result__snippet">(.*?)</a>',
        resp.text, re.DOTALL,
    )
    urls = re.findall(r'class="result__url"[^>]*>(.*?)</a>', resp.text, re.DOTALL)
    titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', resp.text, re.DOTALL)

    for i, snippet in enumerate(blocks[:max_results]):
        snippet_clean = re.sub(r'<[^>]+>', '', snippet).strip()
        url = urls[i].strip() if i < len(urls) else ""
        title = re.sub(r'<[^>]+>', '', titles[i]).strip() if i < len(titles) else ""
        results.append({"url": url, "title": title, "snippet": snippet_clean})
    return results


def scan_communities(niche: str, max_leads: int = 30) -> list[dict]:
    """
    Infiltrate Reddit and Facebook communities for the niche.
    Scans pain-signal posts without ever posting.
    Returns lead profiles extracted from comment snippets.
    """
    queries = [
        f'site:reddit.com "{niche}" (help OR advice OR "j\'ai besoin" OR struggling)',
        f'site:reddit.com "{niche}" (comment OR how OR "est-ce que" OR "does it work")',
        f'"{niche}" site:facebook.com/groups (aide OR problem OR help)',
    ]

    leads: list[dict] = []
    seen: set[str] = set()

    for query in queries:
        results = _search_ddg(query, max_results=15)
        for item in results:
            text = f"{item['title']} {item['snippet']}"
            if not _PAIN_SIGNAL_RE.search(text):
                continue

            # Extract Reddit usernames from URL or snippet
            reddit_users = _REDDIT_USER_RE.findall(item["url"])
            handles_from_text = _HANDLE_RE.findall(text)

            all_handles = list(reddit_users)
            for groups in handles_from_text:
                all_handles.extend(h for h in groups if h)

            is_reddit = "reddit.com" in item["url"]
            platform = "reddit" if is_reddit else "facebook"
            base_url = "https://reddit.com/u/" if is_reddit else "https://facebook.com/"

            for handle in all_handles[:3]:
                h = handle.lower().strip("_")
                if not h or h in seen or h in {"deleted", "moderator", "automoderator"}:
                    continue
                seen.add(h)
                is_failed_buyer = bool(_FAILED_BUYER_RE.search(text))
                leads.append({
                    "handle": h,
                    "name": handle,
                    "platform": platform,
                    "profile_url": f"{base_url}{handle}",
                    "bio": "",
                    "followers": 0,
                    "posts_summary": (
                        f"[{'Acheteur raté' if is_failed_buyer else 'Communauté'}] "
                        + text[:300]
                    ),
                    "_source_tag": "community",
                    "_is_failed_buyer": is_failed_buyer,
                })

        if len(leads) >= max_leads:
            break

    return leads[:max_leads]


def scan_google_reviews(competitor_names: list[str], max_leads: int = 20) -> list[dict]:
    """
    Mine 1-star Google reviews of competitor coaches.
    Unhappy coaching buyers who still want results — easiest converts.
    """
    leads: list[dict] = []
    seen: set[str] = set()

    for coach_name in competitor_names[:5]:
        queries = [
            f'"{coach_name}" avis "1 étoile" OR "arnaque" OR "déception" OR "remboursement"',
            f'"{coach_name}" review "scam" OR "waste" OR "didn\'t work" OR "refund"',
            f'"{coach_name}" commentaire négatif site:trustpilot.com OR site:google.com',
        ]
        for query in queries:
            results = _search_ddg(query, max_results=10)
            for item in results:
                text = f"{item['title']} {item['snippet']}"
                if not _PAIN_SIGNAL_RE.search(text) and not _FAILED_BUYER_RE.search(text):
                    continue
                handles = [h for groups in _HANDLE_RE.findall(text) for h in groups if h]
                for handle in handles[:2]:
                    h = handle.lower()
                    if not h or h in seen:
                        continue
                    seen.add(h)
                    leads.append({
                        "handle": h,
                        "name": handle,
                        "platform": "google_reviews",
                        "profile_url": "",
                        "bio": "",
                        "followers": 0,
                        "posts_summary": (
                            f"[Acheteur raté — ex-client de {coach_name}] "
                            + text[:300]
                        ),
                        "_source_tag": "community",
                        "_is_failed_buyer": True,
                    })
        if len(leads) >= max_leads:
            break

    return leads[:max_leads]


def scan_youtube_comments(niche: str, max_leads: int = 30) -> list[dict]:
    """
    Mine YouTube comment sections for people asking "does this really work?" —
    millions of qualified leads nobody else is touching.
    """
    queries = [
        f'site:youtube.com "{niche}" "est-ce que ça marche" OR "how do you" OR "does this work"',
        f'site:youtube.com "{niche}" "j\'ai essayé" OR "i tried" OR "nothing works" OR "still struggling"',
        f'site:youtube.com "{niche}" comments "before and after" OR "avant après" OR "want this"',
    ]

    leads: list[dict] = []
    seen: set[str] = set()

    for query in queries:
        results = _search_ddg(query, max_results=12)
        for item in results:
            text = f"{item['title']} {item['snippet']}"
            if not _PAIN_SIGNAL_RE.search(text):
                continue
            handles = [h for groups in _HANDLE_RE.findall(text) for h in groups if h]
            for handle in handles[:2]:
                h = handle.lower()
                if not h or h in seen:
                    continue
                seen.add(h)
                leads.append({
                    "handle": h,
                    "name": handle,
                    "platform": "youtube",
                    "profile_url": f"https://youtube.com/@{handle}",
                    "bio": "",
                    "followers": 0,
                    "posts_summary": f"[Commentaire YouTube — niche {niche}] " + text[:300],
                    "_source_tag": "community",
                })
        if len(leads) >= max_leads:
            break

    return leads[:max_leads]
