"""
CRM Agent
Syncs lead data to Airtable (create or update a record in the "Leads" table).
"""
import httpx

AIRTABLE_BASE_URL = "https://api.airtable.com/v0"


def _headers(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def _build_fields(lead_data: dict) -> dict:
    field_map = {
        "Name": lead_data.get("name", ""),
        "Handle": lead_data.get("handle", ""),
        "Platform": lead_data.get("platform", ""),
        "Profile URL": lead_data.get("profile_url", ""),
        "Bio": lead_data.get("bio", ""),
        "Followers": lead_data.get("followers", 0),
        "Qualification Score": lead_data.get("qualification_score", 0),
        "Qualification Reason": lead_data.get("qualification_reason", ""),
        "Stage": lead_data.get("stage", "new"),
        "Outreach Message": lead_data.get("outreach_message", ""),
        "Notes": lead_data.get("notes", ""),
    }
    # Drop empty strings and None
    return {k: v for k, v in field_map.items() if v not in (None, "", 0)}


def sync_lead(
    lead_data: dict,
    airtable_base_id: str,
    airtable_api_key: str,
    record_id: str | None = None,
) -> str:
    """
    Create or update a lead record in Airtable.
    Returns the Airtable record_id.
    Raises httpx.HTTPStatusError on failure.
    """
    url = f"{AIRTABLE_BASE_URL}/{airtable_base_id}/Leads"
    fields = _build_fields(lead_data)

    if record_id:
        resp = httpx.patch(
            f"{url}/{record_id}",
            json={"fields": fields},
            headers=_headers(airtable_api_key),
            timeout=15,
        )
    else:
        resp = httpx.post(
            url,
            json={"fields": fields},
            headers=_headers(airtable_api_key),
            timeout=15,
        )

    resp.raise_for_status()
    return resp.json()["id"]


def delete_lead(
    record_id: str,
    airtable_base_id: str,
    airtable_api_key: str,
) -> None:
    """Delete a lead record from Airtable."""
    url = f"{AIRTABLE_BASE_URL}/{airtable_base_id}/Leads/{record_id}"
    resp = httpx.delete(url, headers=_headers(airtable_api_key), timeout=15)
    resp.raise_for_status()
