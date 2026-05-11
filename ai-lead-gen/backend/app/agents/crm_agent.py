"""
CRM Agent — leads are stored in SQLite, no external CRM sync needed.
These stubs preserve the function signatures so existing callers don't break.
"""


def sync_lead(
    lead_data: dict,
    airtable_base_id: str = "",
    airtable_api_key: str = "",
    record_id: str | None = None,
) -> str:
    return ""


def delete_lead(
    record_id: str,
    airtable_base_id: str = "",
    airtable_api_key: str = "",
) -> None:
    pass
