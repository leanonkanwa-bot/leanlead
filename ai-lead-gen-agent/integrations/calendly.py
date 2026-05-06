"""Calendly helpers — just exposes the configured link for injection into messages."""

from config import CALENDLY_LINK


def get_booking_link() -> str:
    if not CALENDLY_LINK:
        raise ValueError("CALENDLY_LINK not configured in environment.")
    return CALENDLY_LINK


def format_calendly_cta(link: str | None = None) -> str:
    link = link or get_booking_link()
    return f"Voici mon lien pour qu'on échange : {link} 🗓️"
