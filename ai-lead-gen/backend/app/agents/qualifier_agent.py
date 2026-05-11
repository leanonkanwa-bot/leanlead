"""
Qualifier Agent
Scores a social-media profile 0–100 for fit with a coach's niche/offer using Claude.
Scoring: pain_intensity(35) + buying_readiness(25) + audience_fit(25) + authenticity(15)
Hard-disqualifies brands, coaches, and accounts >50k followers before any AI call.
"""
import json
import os
import re

import anthropic

_client: anthropic.Anthropic | None = None

# Patterns that auto-disqualify without spending an API call
_BRAND_RE = re.compile(
    r'\b(llc|inc\b|corp\b|ltd\b|agency|studio|official|media|solutions|services|'
    r'consulting|enterprises|group\b|brand\b|shop\b|store\b|boutique|company)\b',
    re.IGNORECASE,
)
_COACH_RE = re.compile(
    r'\b(certified coach|life coach|business coach|executive coach|health coach|'
    r'fitness coach|mindset coach|nlp practitioner|mentor\b|consultant\b|trainer\b|'
    r'helping (clients|people|entrepreneurs)|i help (clients|people)|'
    r'book a call|free discovery|dm me to|click the link|work with me|'
    r'coaching program|my program|join my|enroll now|limited spots)\b',
    re.IGNORECASE,
)


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


def _hard_disqualify(profile: dict) -> str | None:
    """Return a reason string if this profile should be skipped, else None."""
    followers = profile.get("followers") or 0
    if followers > 50_000:
        return f"too many followers ({followers:,})"
    combined = f"{profile.get('name', '')} {profile.get('bio', '')} {profile.get('posts_summary', '')}".strip()
    if _BRAND_RE.search(combined):
        return "brand or business account"
    if _COACH_RE.search(combined):
        return "appears to be a coach/trainer themselves"
    return None


def qualify_lead(
    lead_data: dict,
    coach_niche: str,
    coach_offer: str,
    icp_pain_points: list[str] | None = None,
) -> dict:
    """
    Returns:
        {
          "score": int (0–100),
          "reason": str,
          "pain_points": list[str],
          "recommended_angle": str,
          "disqualified": bool,
          "disqualify_reason": str | None,
        }
    """
    disqualify_reason = _hard_disqualify(lead_data)
    if disqualify_reason:
        return {
            "score": 0,
            "reason": f"Auto-disqualified: {disqualify_reason}",
            "pain_points": [],
            "recommended_angle": "",
            "disqualified": True,
            "disqualify_reason": disqualify_reason,
        }

    icp_section = ""
    if icp_pain_points:
        icp_section = f"\nICP pain points to watch for: {', '.join(icp_pain_points)}"

    prompt = f"""You are an elite lead qualifier for online coaches. Your job is to identify POTENTIAL CLIENTS who have pain — NOT other coaches, NOT businesses, NOT brands.

Coach niche: {coach_niche}
Coach offer: {coach_offer}{icp_section}

Profile to evaluate:
- Name: {lead_data.get("name", "Unknown")}
- Handle: @{lead_data.get("handle", "")}
- Platform: {lead_data.get("platform", "instagram")}
- Bio: {lead_data.get("bio", "No bio available")}
- Followers: {lead_data.get("followers", 0):,}
- Posts / snippets: {lead_data.get("posts_summary", "N/A")}

Score this profile 0–100 using this exact breakdown:

PAIN INTENSITY (0–35): Does their content/bio show real pain, frustration, or struggle relevant to the coach's niche?
  35 = explicitly expressing pain  |  20 = hints at struggle  |  5 = no visible pain

BUYING READINESS (0–25): Are they actively seeking solutions? (asking questions, researching, expressing desire for change)
  25 = actively seeking help  |  15 = open to solutions  |  5 = passive

AUDIENCE FIT (0–25): Do they match the target audience? (demographics, life stage, interests)
  25 = perfect match  |  15 = partial match  |  5 = poor match

AUTHENTICITY (0–15): Is this a real individual person (not a brand, bot, or coach)?
  15 = clearly a real person  |  8 = uncertain  |  0 = brand/coach/bot

IMMEDIATELY return 0 with disqualified=true if:
- They ARE a coach/consultant/mentor themselves
- They are a brand, business, or official account
- They have >50k followers
- Bio reads like a sales page

Respond ONLY with valid JSON (no markdown):
{{"score": <0-100>, "reason": "<2-3 sentences explaining score with breakdown>", "pain_points": ["<specific pain 1>", "<specific pain 2>"], "recommended_angle": "<what to lead with in outreach>", "disqualified": false, "disqualify_reason": null}}"""

    msg = _get_client().messages.create(
        model="claude-opus-4-7",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text
    start, end = text.find("{"), text.rfind("}") + 1
    result = json.loads(text[start:end])

    # Clamp score
    result["score"] = max(0, min(100, int(result.get("score", 0))))
    result.setdefault("disqualified", False)
    result.setdefault("disqualify_reason", None)

    return result
