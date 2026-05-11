"""
CRM Enrichment Agent — auto-enriches leads with DDG-scraped intelligence.

LinkedIn job history, engagement rate estimation, income bracket inference,
tech stack detection, content consumption patterns.
Zero API keys required — pure DDG + Claude inference.
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


def _ddg(query: str, max_results: int = 8) -> list[dict]:
    try:
        resp = httpx.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers=BROWSER_HEADERS,
            timeout=10,
            follow_redirects=True,
        )
        resp.raise_for_status()
    except Exception as e:
        logger.warning("DDG enrichment failed %r: %s", query, e)
        return []
    titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', resp.text, re.DOTALL)
    snippets = re.findall(r'class="result__snippet">(.*?)</a>', resp.text, re.DOTALL)
    urls = re.findall(r'class="result__url"[^>]*>(.*?)</a>', resp.text, re.DOTALL)
    results = []
    for i, (t, s) in enumerate(zip(titles, snippets)):
        results.append({
            "title": re.sub(r'<[^>]+>', '', t).strip(),
            "snippet": re.sub(r'<[^>]+>', '', s).strip(),
            "url": urls[i].strip() if i < len(urls) else "",
        })
    return results[:max_results]


def enrich_lead(handle: str, platform: str, name: str = "", bio: str = "") -> dict:
    """
    CRM-grade auto-enrichment for a lead.
    Returns enriched_data dict with LinkedIn role, income estimate, tech stack, etc.
    """
    enriched: dict = {
        "linkedin_role": None,
        "linkedin_company": None,
        "estimated_income": None,
        "income_confidence": "low",
        "content_consumption": [],
        "tech_stack": [],
        "interests": [],
        "other_platforms": [],
        "engagement_signals": None,
        "business_type": None,
    }

    all_context_parts: list[str] = [f"Handle: @{handle}, Platform: {platform}"]
    if name:
        all_context_parts.append(f"Name: {name}")
    if bio:
        all_context_parts.append(f"Bio: {bio}")

    # LinkedIn lookup
    ln_results = _ddg(f'site:linkedin.com/in "{handle}" OR "{name}"', max_results=4)
    if ln_results:
        text = f"{ln_results[0]['title']} {ln_results[0]['snippet']}"
        all_context_parts.append(f"LinkedIn: {text[:300]}")
        job_match = re.search(
            r'\b(CEO|CTO|COO|CFO|Founder|Co-founder|Director|Manager|'
            r'Coach|Consultant|Freelance|Creator|Entrepreneur|VP|Lead|'
            r'PDG|Directeur|Gérant|Fondateur|Auto-entrepreneur|Indépendant)\b',
            text, re.IGNORECASE,
        )
        if job_match:
            enriched["linkedin_role"] = job_match.group(0)
        company_match = re.search(r'(?:at|chez|@)\s+([A-Z][a-zA-Z0-9\s&]{2,25})', text)
        if company_match:
            enriched["linkedin_company"] = company_match.group(1).strip()

    # Content consumption: YouTube, podcasts, newsletters
    content_results = _ddg(f'"@{handle}" site:youtube.com OR site:substack.com OR podcast', max_results=5)
    platforms_found = set()
    for r in content_results:
        t = (r["title"] + r["snippet"]).lower()
        if "youtube" in t:
            platforms_found.add("YouTube")
        if "podcast" in t:
            platforms_found.add("Podcast")
        if "substack" in t or "newsletter" in t:
            platforms_found.add("Newsletter/Substack")
        if "twitter" in t or "x.com" in t:
            platforms_found.add("Twitter/X")
        if "tiktok" in t:
            platforms_found.add("TikTok")
    enriched["content_consumption"] = list(platforms_found)

    # Other platforms
    other_results = _ddg(f'"{handle}" site:tiktok.com OR site:twitter.com OR site:linkedin.com', max_results=4)
    other_platforms = []
    for r in other_results:
        if "tiktok" in r["url"] and "tiktok" not in platform:
            other_platforms.append("tiktok")
        if ("twitter" in r["url"] or "x.com" in r["url"]) and "twitter" not in platform:
            other_platforms.append("twitter")
        if "linkedin" in r["url"] and "linkedin" not in platform:
            other_platforms.append("linkedin")
    enriched["other_platforms"] = list(set(other_platforms))
    all_context_parts.extend([f"Found on {p}" for p in other_platforms])

    # Claude inference for income bracket, tech stack, interests, business type
    all_context = " | ".join(all_context_parts)[:800]
    try:
        msg = _get_client().messages.create(
            model="claude-opus-4-7",
            max_tokens=300,
            messages=[{"role": "user", "content": f"""Based on this person's profile, infer their financial and professional profile.

Profile: {all_context}

Return ONLY valid JSON:
{{
  "income_bracket": "<under_30k|30k_60k|60k_100k|100k_250k|250k_plus>",
  "income_confidence": "<low|medium|high>",
  "tech_stack": ["<2-3 tools/software they likely use based on their role>"],
  "interests": ["<2-3 professional topics they care about>"],
  "business_type": "<employee|freelance|entrepreneur|creator|student|other>",
  "engagement_signals": "<brief note on their likely activity level>"
}}"""}],
        )
        text = msg.content[0].text
        start, end = text.find("{"), text.rfind("}") + 1
        inferred = json.loads(text[start:end])
        enriched["estimated_income"] = inferred.get("income_bracket")
        enriched["income_confidence"] = inferred.get("income_confidence", "low")
        enriched["tech_stack"] = inferred.get("tech_stack", [])
        enriched["interests"] = inferred.get("interests", [])
        enriched["business_type"] = inferred.get("business_type")
        enriched["engagement_signals"] = inferred.get("engagement_signals")
    except Exception as e:
        logger.warning("Claude enrichment inference failed for @%s: %s", handle, e)

    return enriched
