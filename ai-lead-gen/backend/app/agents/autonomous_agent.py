"""Autonomous lead generation engine — multi-platform search with intelligence signals."""
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import httpx

from . import prospector_agent, qualifier_agent, writer_agent, viral_hijacker_agent

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

_RESERVED = {"explore", "accounts", "reels", "p", "stories", "reel", "tv", "tags", "about"}

# ---------------------------------------------------------------------------
# Signal detectors — fast, no API call (FR + EN)
# ---------------------------------------------------------------------------

_BUYING_INTENT_RE = re.compile(
    r'\b('
    # French
    r'combien [çca]a co[uû]te|c\'est combien|quel tarif|comment vous contacter|'
    r'o[uù] trouver|j\'ai besoin d\'aide|quelqu\'un peut m\'aider|'
    r'cherche un coach|besoin d\'un coach|qui peut m\'aider|'
    r'comment commencer|par o[uù] commencer|comment (tu|vous) (fais|faites)|'
    # English
    r'how much|how do i start|where do i start|looking for a coach|'
    r'need a coach|any recommendations|how do i|someone help|advice please|'
    r'ready to invest|ready to change|need guidance'
    r')\b',
    re.IGNORECASE,
)

_LIFE_EVENT_RE = re.compile(
    r'\b('
    # French
    r'nouvelle ann[ée]e?|nouvel an|nouveau d[ée]part|tout recommencer|repartir de z[ée]ro|'
    r'nouvelle vie|changer de vie|licenci[ée](e)?|au ch[ôo]mage|d[ée]mission|'
    r'j\'ai quitt[ée]|reconversion|j\'en peux plus|j\'en ai marre|ras le bol|'
    r'divorc[ée](e)?|s[ée]paration|rupture|b[ée]b[ée]|enceinte|accouchement|'
    r'mariage|fianç|j\'ai d[ée]cid[ée]|cette fois c\'est la bonne|maintenant ou jamais|'
    r'je me lance|j\'ose enfin|'
    # English
    r'new year|fresh start|starting over|just lost my job|quit my job|left my job|'
    r'just divorced|just had a baby|new chapter|rock bottom|enough is enough|'
    r'turning point|wake up call|life change|career change|'
    r'turned 3\d|turning 3\d|turned 4\d|turning 4\d|just graduated|just moved'
    r')\b',
    re.IGNORECASE,
)

# Engagement patterns in competitor comment sections
_COMMENTER_ENGAGEMENT_RE = re.compile(
    r'\b('
    r'merci|comment (tu|vous|faire|on)|c\'est quoi|o[uù] trouver|combien|'
    r'int[ée]ress[ée](e)?|comment commencer|j\'aimerais|j\'adore|j\'aime|'
    r'thank you|thanks|how do you|what is|where can i|how much|interested|'
    r'amazing|love this|can you|question|help me|reply|how to|'
    r'incroyable|magnifique|bravo|super|génial|waouh|chapeau'
    r')\b',
    re.IGNORECASE,
)


def _has_buying_intent(text: str) -> bool:
    return bool(_BUYING_INTENT_RE.search(text))


def _has_life_event(text: str) -> bool:
    return bool(_LIFE_EVENT_RE.search(text))


# ---------------------------------------------------------------------------
# DDG search helper
# ---------------------------------------------------------------------------

def _search_ddg(query: str, max_results: int = 30) -> list[dict]:
    """Search DuckDuckGo HTML and return [{url, title, snippet}]."""
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
    # Extract result blocks
    blocks = re.findall(
        r'class="result__body".*?class="result__snippet">(.*?)</a>',
        resp.text,
        re.DOTALL,
    )
    urls = re.findall(r'class="result__url"[^>]*>(.*?)</a>', resp.text, re.DOTALL)
    titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', resp.text, re.DOTALL)

    for i, snippet in enumerate(blocks[:max_results]):
        snippet_clean = re.sub(r'<[^>]+>', '', snippet).strip()
        url = urls[i].strip() if i < len(urls) else ""
        title = re.sub(r'<[^>]+>', '', titles[i]).strip() if i < len(titles) else ""
        results.append({"url": url, "title": title, "snippet": snippet_clean})

    return results


# ---------------------------------------------------------------------------
# Platform search
# ---------------------------------------------------------------------------

def _search_platform(platform: str, terms: list[str], max_per_term: int) -> list[dict]:
    results: list[dict] = []
    for term in terms:
        try:
            raw = prospector_agent.prospect(
                platform=platform,
                hashtags=[term],
                max_results=max_per_term,
            )
            results.extend(raw)
        except Exception as e:
            logger.warning("Platform %s term %s failed: %s", platform, term, e)
    return results


# ---------------------------------------------------------------------------
# Competitor audience hijack
# ---------------------------------------------------------------------------

def scan_competitor_comments(competitor_url: str, platform: str, max_results: int = 30) -> list[dict]:
    """
    Find people actively engaging with a competitor's content.
    Searches DDG for posts/comments mentioning the competitor handle,
    then extracts @mentions from snippets showing buying-mode engagement.
    """
    # Extract handle from URL
    handle = competitor_url.strip().rstrip("/").split("@")[-1].split("?")[0]
    if "/" in handle:
        handle = handle.split("/")[-1]
    handle = handle.lstrip("@").lower()
    if not handle:
        return []

    site_map = {
        "instagram": "instagram.com",
        "tiktok": "tiktok.com",
        "twitter": "twitter.com",
        "linkedin": "linkedin.com",
    }
    site = site_map.get(platform, f"{platform}.com")

    # Two search strategies: direct handle mentions + site search
    queries = [
        f'"@{handle}"',
        f'site:{site} "{handle}"',
    ]

    all_snippets: list[str] = []
    for q in queries:
        for item in _search_ddg(q, max_results // 2):
            all_snippets.append(f"{item.get('title', '')} {item.get('snippet', '')}")

    profiles: list[dict] = []
    seen_handles: set[str] = set()

    for snippet in all_snippets:
        # Only process snippets with real engagement signals
        if not _COMMENTER_ENGAGEMENT_RE.search(snippet):
            continue

        # Extract @mentions that are NOT the competitor
        mentioned = re.findall(r'@([a-zA-Z0-9_.]{3,30})', snippet)
        for m in mentioned:
            h = m.lower()
            if h == handle or h in _RESERVED or h in seen_handles:
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
                    f"Engagé sous le contenu de @{handle} ({platform}): "
                    + snippet[:250]
                ),
            })

    return profiles[:max_results]


# ---------------------------------------------------------------------------
# Main autonomous run
# ---------------------------------------------------------------------------

def run_autonomous(
    coach_id: int,
    coach_niche: str,
    coach_offer: str,
    coach_name: str,
    icp_pain_points: list[str] | None,
    platforms: list[str],
    search_terms_per_platform: dict[str, list[str]],
    max_per_platform: int,
    dm_threshold: int,
    existing_handles: set[str],
    competitor_accounts: list[dict] | None = None,
    viral_hijack_enabled: bool = True,
) -> dict[str, Any]:
    """
    Run one full autonomous prospecting cycle for a coach.
    Returns stats + leads list ready for DB insertion.
    """
    stats: dict[str, Any] = {
        "leads_found": 0, "leads_qualified": 0, "dms_generated": 0, "high_score_leads": 0,
    }

    max_terms = max(1, max(len(search_terms_per_platform.get(p, [])) for p in platforms) if platforms else 1)
    max_per_term = max(3, max_per_platform // max_terms)

    # 1. Search all platforms concurrently
    all_raw: list[dict] = []
    with ThreadPoolExecutor(max_workers=min(len(platforms), 5)) as exe:
        futures = {
            exe.submit(
                _search_platform,
                platform,
                search_terms_per_platform.get(platform, []),
                max_per_term,
            ): platform
            for platform in platforms
            if search_terms_per_platform.get(platform)
        }
        for future in as_completed(futures):
            try:
                all_raw.extend(future.result())
            except Exception as e:
                logger.warning("Platform search failed: %s", e)

    # 2. Viral post hijacker — find commenters on viral niche posts
    if viral_hijack_enabled and coach_niche:
        for platform in platforms[:2]:  # limit to first 2 platforms to save time
            try:
                viral_leads = viral_hijacker_agent.scan_viral_posts(
                    niche=coach_niche,
                    platform=platform,
                    max_commenters=20,
                )
                for lead in viral_leads:
                    lead["_source_tag"] = "viral_post"
                all_raw.extend(viral_leads)
                logger.info("Viral hijacker found %d candidates on %s", len(viral_leads), platform)
            except Exception as e:
                logger.warning("Viral hijacker failed for %s: %s", platform, e)

    # 3. Scan competitor comment sections concurrently
    if competitor_accounts:
        with ThreadPoolExecutor(max_workers=min(len(competitor_accounts), 4)) as exe:
            comp_futures = {
                exe.submit(
                    scan_competitor_comments,
                    comp["url"],
                    comp.get("platform", "instagram"),
                    25,
                ): comp
                for comp in competitor_accounts
                if comp.get("url")
            }
            for future in as_completed(comp_futures):
                comp = comp_futures[future]
                try:
                    comp_leads = future.result()
                    # Mark source so DM can reference it
                    for lead in comp_leads:
                        lead["_source"] = f"concurrent:{comp.get('handle', comp['url'])}"
                    all_raw.extend(comp_leads)
                    logger.info(
                        "Competitor scan @%s found %d candidates",
                        comp.get("handle", "?"), len(comp_leads),
                    )
                except Exception as e:
                    logger.warning("Competitor scan failed for %s: %s", comp.get("url"), e)

    # 3. Deduplicate by handle
    seen_handles: set[str] = set(existing_handles)
    unique_profiles: list[dict] = []
    for p in all_raw:
        handle = (p.get("handle") or "").strip().lower()
        if handle and handle not in seen_handles:
            seen_handles.add(handle)
            unique_profiles.append(p)

    # 4. Sort by signal strength (buying intent + life events first = max value per API $)
    def _priority(p: dict) -> int:
        text = f"{p.get('bio', '')} {p.get('posts_summary', '')}"
        score = 0
        if _has_buying_intent(text):
            score += 3
        if _has_life_event(text):
            score += 2
        # Competitor audience leads get priority — they've already shown engagement
        if p.get("_source", "").startswith("concurrent:"):
            score += 1
        return -score

    unique_profiles.sort(key=_priority)

    # 5. Qualify + optionally generate DMs
    new_leads: list[dict] = []

    for profile in unique_profiles:
        handle = (profile.get("handle") or "").strip().lower()
        lead_data = {
            "name": profile.get("name", ""),
            "handle": handle,
            "platform": profile.get("platform", "unknown"),
            "bio": profile.get("bio", "") or "",
            "followers": profile.get("followers", 0),
            "posts_summary": profile.get("posts_summary", "") or "",
        }

        qualification: dict[str, Any] = {
            "score": 0, "reason": "", "pain_points": [], "recommended_angle": "",
            "disqualified": False,
        }

        try:
            result = qualifier_agent.qualify_lead(
                lead_data=lead_data,
                coach_niche=coach_niche,
                coach_offer=coach_offer,
                icp_pain_points=icp_pain_points or None,
            )
            qualification = result
            stats["leads_qualified"] += 1
        except Exception as e:
            logger.warning("Qualification failed for %s: %s", handle, e)

        if qualification.get("disqualified"):
            continue

        psycho = qualification.get("psychographic", {})
        language = psycho.get("language", "fr") or "fr"

        outreach_message = None
        dm_variant_b = None
        if qualification["score"] >= dm_threshold and coach_niche and coach_offer:
            try:
                va, vb = writer_agent.write_ab_variants(
                    lead_data=lead_data,
                    coach_name=coach_name,
                    coach_niche=coach_niche,
                    coach_offer=coach_offer,
                    qualification=qualification,
                    language=language,
                )
                outreach_message = va
                dm_variant_b = vb
                stats["dms_generated"] += 1
            except Exception as e:
                logger.warning("DM generation failed for %s: %s", handle, e)

        if qualification["score"] >= 70:
            stats["high_score_leads"] += 1

        # Determine source tag
        source_tag = profile.get("_source_tag") or (
            "competitor_audience" if profile.get("_source", "").startswith("concurrent:")
            else "hashtag"
        )

        new_leads.append({
            **profile,
            "handle": handle,
            "qualification_score": qualification["score"],
            "qualification_reason": qualification.get("reason", ""),
            "pain_points": json.dumps(qualification.get("pain_points", [])),
            "recommended_angle": qualification.get("recommended_angle", ""),
            "outreach_message": outreach_message,
            "dm_variant_b": dm_variant_b,
            "language": language,
            "psychographic_profile": json.dumps(psycho) if psycho else None,
            "response_probability": qualification.get("response_probability", 0),
            "source_tag": source_tag,
        })
        stats["leads_found"] += 1

    return {**stats, "leads": new_leads}
