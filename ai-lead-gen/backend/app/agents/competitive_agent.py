"""
Competitive Intelligence Agent — automatically monitors competitor coaches.

Agencies charge €1000/month for competitor analysis.
LeanLead does it automatically for free via DDG mining.

Tracks: content themes, pricing signals, dissatisfied clients,
positioning gaps, and coaching style weaknesses.
"""
import json
import logging
import os
import re

import anthropic
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

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


def _ddg(query: str, max_results: int = 10) -> list[dict]:
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
        logger.warning("DDG competitive query failed: %s", e)
        return []
    titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', resp.text, re.DOTALL)
    snippets = re.findall(r'class="result__snippet">(.*?)</a>', resp.text, re.DOTALL)
    results = []
    for t, s in zip(titles, snippets):
        results.append({
            "title": re.sub(r'<[^>]+>', '', t).strip(),
            "snippet": re.sub(r'<[^>]+>', '', s).strip(),
        })
    return results[:max_results]


_PRICE_RE = re.compile(
    r'(\d{1,5})\s*(?:€|EUR|dollars?|\$|£)',
    re.IGNORECASE,
)

_NEGATIVE_RE = re.compile(
    r'\b('
    r'arnaque|arnaqu[ée]|déception|d[ée]çu|pas de r[ée]sultat|aucun r[ée]sultat|'
    r'remboursement|inutile|ne vaut rien|trop cher|vol|escroquerie|'
    r'scam|waste|disappointed|no result|refund|didn\'t work|not worth'
    r')\b',
    re.IGNORECASE,
)


def scan_competitor(handle: str, platform: str, niche: str) -> dict:
    """
    Full competitive intelligence scan for one competitor coach.
    Returns content themes, pricing signals, weaknesses, dissatisfied client count.
    """
    site_map = {
        "instagram": "instagram.com",
        "tiktok": "tiktok.com",
        "twitter": "twitter.com",
        "linkedin": "linkedin.com",
    }
    site = site_map.get(platform, f"{platform}.com")

    # Gather their content themes
    content_results = _ddg(f'site:{site} "@{handle}" "{niche}"', max_results=10)
    # Check for pricing mentions
    pricing_results = _ddg(f'"@{handle}" (tarif OR prix OR price OR "€" OR programme)', max_results=8)
    # Find dissatisfied clients
    neg_results = _ddg(f'"@{handle}" (arnaque OR déception OR "pas de résultats" OR scam OR refund OR "didn\'t work")', max_results=8)

    all_content = " ".join(f"{r['title']} {r['snippet']}" for r in content_results)

    # Extract pricing
    prices_found = [int(m.group(1)) for m in _PRICE_RE.finditer(
        " ".join(f"{r['title']} {r['snippet']}" for r in pricing_results)
    )]
    price_signal = None
    if prices_found:
        max_price = max(prices_found)
        if max_price >= 500:
            price_signal = max_price

    # Count dissatisfied mentions
    neg_count = sum(1 for r in neg_results if _NEGATIVE_RE.search(f"{r['title']} {r['snippet']}"))

    # Extract @mentions from dissatisfied posts (these are warm leads)
    dissatisfied_handles = []
    handle_re = re.compile(r'@([a-zA-Z0-9_.]{3,30})')
    for r in neg_results:
        text = f"{r['title']} {r['snippet']}"
        if _NEGATIVE_RE.search(text):
            found = handle_re.findall(text)
            for h in found:
                if h.lower() != handle.lower():
                    dissatisfied_handles.append(h.lower())

    # Use Claude to analyze content strategy and find gaps
    content_analysis = {}
    if all_content:
        try:
            msg = _get_client().messages.create(
                model="claude-opus-4-7",
                max_tokens=400,
                messages=[{"role": "user", "content": f"""Analyze this competitor coach's content and positioning.

Competitor: @{handle} ({platform})
Niche: {niche}
Content snippets: {all_content[:1200]}

Return ONLY valid JSON:
{{
  "content_themes": ["<top 3 topics they cover>"],
  "messaging_style": "<aggressive|empathetic|educational|inspirational|direct>",
  "apparent_strengths": ["<what they do well — be specific>"],
  "gaps": ["<what they miss or do poorly — coaching opportunity>"],
  "positioning": "<their main promise in 10 words>",
  "audience_overlap": "<high|medium|low overlap with a coach targeting {niche}>"
}}"""}],
            )
            text = msg.content[0].text
            start, end = text.find("{"), text.rfind("}") + 1
            content_analysis = json.loads(text[start:end])
        except Exception as e:
            logger.warning("Claude competitive analysis failed for @%s: %s", handle, e)

    return {
        "handle": handle,
        "platform": platform,
        "price_signal": price_signal,
        "dissatisfied_count": neg_count,
        "dissatisfied_handles": list(set(dissatisfied_handles))[:10],
        "content_themes": content_analysis.get("content_themes", []),
        "messaging_style": content_analysis.get("messaging_style"),
        "gaps": content_analysis.get("gaps", []),
        "positioning": content_analysis.get("positioning"),
        "audience_overlap": content_analysis.get("audience_overlap"),
    }


def generate_competitive_report(
    competitor_scans: list[dict],
    coach_niche: str,
    coach_offer: str,
    coach_name: str,
) -> dict:
    """
    Full competitive intelligence report — finds positioning opportunities.
    """
    if not competitor_scans:
        return {"opportunities": [], "unique_angle": "", "market_gaps": []}

    scans_summary = json.dumps(competitor_scans, ensure_ascii=False)[:2000]
    try:
        msg = _get_client().messages.create(
            model="claude-opus-4-7",
            max_tokens=600,
            messages=[{"role": "user", "content": f"""You are a marketing strategist. Based on competitive intelligence, find positioning opportunities.

Coach: {coach_name}
Niche: {coach_niche}
Offer: {coach_offer}

Competitor intelligence:
{scans_summary}

Return ONLY valid JSON:
{{
  "market_gaps": ["<gaps in competitor messaging that {coach_name} can fill>"],
  "unique_angle": "<{coach_name}'s unique positioning vs all competitors — 15 words max>",
  "opportunities": ["<top 3 specific opportunities: e.g. 'Target ex-clients of @X who mention Y'>"],
  "avoid": ["<messaging/angles that are oversaturated among competitors>"],
  "price_position": "<underpriced|competitive|premium — relative to competitors>",
  "alert": "<any urgent signal — e.g. competitor raised prices, competitor went quiet>"
}}"""}],
        )
        text = msg.content[0].text
        start, end = text.find("{"), text.rfind("}") + 1
        return json.loads(text[start:end])
    except Exception as e:
        logger.warning("Competitive report generation failed: %s", e)
        return {"opportunities": [], "unique_angle": "", "market_gaps": []}
