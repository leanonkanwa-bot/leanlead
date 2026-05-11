"""Autonomous lead generation engine — orchestrates multi-platform search with intelligence signals."""
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from . import prospector_agent, qualifier_agent, writer_agent

logger = logging.getLogger(__name__)

# Buying intent signals — high-priority leads
_BUYING_INTENT_RE = re.compile(
    r'\b(how much (does it cost|is it)|where do i start|how do i (get started|start)|'
    r'looking for a coach|need a coach|hire a coach|recommend.{0,20}coach|'
    r'any (good )?coach|coach recommendations|any recommendations|'
    r'help me with|i need help|need guidance|need support|'
    r'struggling with|can\'t seem to|overwhelmed by|lost with|confused about|'
    r'finally ready|taking action|starting my journey|tired of (being|feeling)|'
    r'want to (change|improve|transform|level up)|ready to (change|invest|commit))\b',
    re.IGNORECASE,
)

# Life event triggers — context that increases buying intent
_LIFE_EVENT_RE = re.compile(
    r'\b(just lost my job|lost my job|quit my job|left my job|quit my 9.?5|'
    r'new year new|starting over|fresh start|big changes|new chapter|'
    r'just had a baby|new mom|new dad|recently divorced|going through a divorce|'
    r'turned 3[0-9]|turning 3[0-9]|turned 4[0-9]|turning 4[0-9]|turning 50|'
    r'just graduated|starting a business|launched my|'
    r'just moved|relocated|new city|career change|pivot)\b',
    re.IGNORECASE,
)


def _has_buying_intent(text: str) -> bool:
    return bool(_BUYING_INTENT_RE.search(text))


def _has_life_event(text: str) -> bool:
    return bool(_LIFE_EVENT_RE.search(text))


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
) -> dict[str, Any]:
    """
    Run one full autonomous prospecting cycle for a coach.
    Returns stats dict with keys: leads_found, leads_qualified, dms_generated,
    high_score_leads, leads (list of dicts ready for DB insertion).
    """
    stats: dict[str, Any] = {
        "leads_found": 0, "leads_qualified": 0, "dms_generated": 0, "high_score_leads": 0,
    }

    # Determine max per search term
    max_terms = max(1, max(len(search_terms_per_platform.get(p, [])) for p in platforms) if platforms else 1)
    max_per_term = max(3, max_per_platform // max_terms)

    # Search all platforms concurrently
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

    # Deduplicate by handle
    seen_handles: set[str] = set(existing_handles)
    unique_profiles: list[dict] = []
    for p in all_raw:
        handle = (p.get("handle") or "").strip().lower()
        if handle and handle not in seen_handles:
            seen_handles.add(handle)
            unique_profiles.append(p)

    # Sort: highest buying intent first to maximize value within API budget
    def _priority(p: dict) -> int:
        text = f"{p.get('bio', '')} {p.get('posts_summary', '')}"
        score = 0
        if _has_buying_intent(text):
            score += 2
        if _has_life_event(text):
            score += 1
        return -score

    unique_profiles.sort(key=_priority)

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
            "disqualified": False, "disqualify_reason": "",
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

        outreach_message = None
        if qualification["score"] >= dm_threshold and coach_niche and coach_offer:
            try:
                outreach_message = writer_agent.write_outreach_message(
                    lead_data=lead_data,
                    coach_name=coach_name,
                    coach_niche=coach_niche,
                    coach_offer=coach_offer,
                    qualification=qualification,
                )
                stats["dms_generated"] += 1
            except Exception as e:
                logger.warning("DM generation failed for %s: %s", handle, e)

        if qualification["score"] >= 70:
            stats["high_score_leads"] += 1

        new_leads.append({
            **profile,
            "handle": handle,
            "qualification_score": qualification["score"],
            "qualification_reason": qualification.get("reason", ""),
            "pain_points": json.dumps(qualification.get("pain_points", [])),
            "recommended_angle": qualification.get("recommended_angle", ""),
            "outreach_message": outreach_message,
        })
        stats["leads_found"] += 1

    return {**stats, "leads": new_leads}
