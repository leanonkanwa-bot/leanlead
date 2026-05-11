"""
Trends Agent — Real-time intent signal monitoring.

Scrapes Google Trends topic volume + DDG news for niche keyword demand spikes.
When searches surge for niche pain points, autonomous agent targets those terms first.
Strike when demand peaks — cheapest acquisition window.
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

# French-speaking market keywords for global arbitrage
_FR_MARKETS = {
    "france":     ["paris", "france", "fr", "hexagone"],
    "quebec":     ["québec", "montreal", "canada francophone"],
    "belgium":    ["belgique", "bruxelles", "wallonie"],
    "switzerland":["suisse", "genève", "lausanne"],
    "morocco":    ["maroc", "casablanca", "rabat"],
    "senegal":    ["sénégal", "dakar"],
    "ivory_coast":["côte d'ivoire", "abidjan"],
}


def _ddg_search(query: str, max_results: int = 20) -> list[dict]:
    try:
        resp = httpx.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers=BROWSER_HEADERS,
            timeout=12,
            follow_redirects=True,
        )
        resp.raise_for_status()
    except Exception as e:
        logger.warning("DDG trends query failed %r: %s", query, e)
        return []

    results = []
    titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', resp.text, re.DOTALL)
    snippets = re.findall(r'class="result__snippet">(.*?)</a>', resp.text, re.DOTALL)
    urls = re.findall(r'class="result__url"[^>]*>(.*?)</a>', resp.text, re.DOTALL)

    for i, (t, s) in enumerate(zip(titles, snippets)):
        results.append({
            "title": re.sub(r'<[^>]+>', '', t).strip(),
            "snippet": re.sub(r'<[^>]+>', '', s).strip(),
            "url": urls[i].strip() if i < len(urls) else "",
        })
    return results[:max_results]


def get_trending_pain_terms(niche: str, icp_pain_points: list[str] | None = None) -> list[str]:
    """
    Discovers currently trending pain search terms for a niche.
    Returns terms ranked by apparent recency/demand (most urgent first).
    Used by autonomous agent to order hashtag prospecting.
    """
    queries = [
        f'"{niche}" "comment" OR "problème" OR "aide" site:reddit.com OR site:quora.com',
        f'"{niche}" OR "{niche} coaching" "2025" trending discussions forum',
        f'"{niche}" question OR "est-ce que" OR "how do" site:reddit.com',
    ]
    if icp_pain_points:
        for pain in icp_pain_points[:2]:
            queries.append(f'"{pain}" "{niche}" site:reddit.com OR site:forum')

    term_freq: dict[str, int] = {}
    stop_words = {"the", "and", "for", "are", "but", "not", "you", "all", "can",
                  "les", "des", "une", "est", "que", "qui", "sur", "dans", "avec"}

    for query in queries:
        results = _ddg_search(query, max_results=15)
        for item in results:
            text = f"{item['title']} {item['snippet']}".lower()
            words = re.findall(r'\b[a-zàâäéèêëîïôùûü]{4,}\b', text)
            for i in range(len(words) - 1):
                if words[i] in stop_words or words[i + 1] in stop_words:
                    continue
                bigram = f"{words[i]} {words[i + 1]}"
                if niche.lower() in bigram or any(
                    p.lower() in bigram for p in (icp_pain_points or [])
                ):
                    term_freq[bigram] = term_freq.get(bigram, 0) + 1

    # Sort by frequency (proxy for trending volume)
    sorted_terms = sorted(term_freq, key=lambda t: term_freq[t], reverse=True)
    return sorted_terms[:15]


def get_trending_hashtags(niche: str, platform: str = "instagram") -> list[str]:
    """
    Returns currently trending hashtags for the niche on a given platform.
    Used to inject real-time demand signals into prospecting.
    """
    site_map = {
        "instagram": "instagram.com",
        "tiktok": "tiktok.com",
        "twitter": "twitter.com",
        "linkedin": "linkedin.com",
    }
    site = site_map.get(platform, "instagram.com")
    query = f'site:{site} "{niche}" trending hashtag 2025 viral'

    results = _ddg_search(query, max_results=15)
    hashtags: list[str] = []
    seen: set[str] = set()

    for item in results:
        text = f"{item['title']} {item['snippet']}"
        found = re.findall(r'#([a-zA-Z0-9_]{3,30})', text)
        for tag in found:
            t = tag.lower()
            if t not in seen:
                seen.add(t)
                hashtags.append(t)

    return hashtags[:10]


def get_global_fr_search_terms(niche: str, markets: list[str] | None = None) -> dict[str, list[str]]:
    """
    Feature 8: Global Lead Arbitrage.
    Generates French-speaking market-specific search terms for each target country.
    Returns {market: [terms]} — used to expand prospecting to untapped geographies.
    """
    target = markets or list(_FR_MARKETS.keys())
    result: dict[str, list[str]] = {}

    for market in target:
        if market not in _FR_MARKETS:
            continue
        geo_keywords = _FR_MARKETS[market]
        terms: list[str] = []
        for geo in geo_keywords[:2]:
            terms.append(f"{niche} {geo}")
            terms.append(f"coach {niche} {geo}")
        result[market] = terms

    return result
