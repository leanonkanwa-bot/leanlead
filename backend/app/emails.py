"""Transactional email module — all sends are fire-and-forget, fail-open,
and skip founder profiles.

Gate: set EMAILS_ENABLED=true on Railway to activate. When unset or false,
every function is a no-op (safe for dev/test without side effects).
Sender: hello@leanretention.com (Resend verified domain).
"""
from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path

try:
    import resend as _resend_lib
    _HAS_RESEND = True
except ImportError:
    _HAS_RESEND = False

_FROM = "hello@leanretention.com"
_APP_URL = "https://leanretention.com/app"
_PRICING_URL = "https://leanretention.com/#pricing"


# ── Internal helpers ──────────────────────────────────────────────────────────

def _enabled() -> bool:
    return os.environ.get("EMAILS_ENABLED", "").strip().lower() == "true"


def _api_key() -> str:
    return os.environ.get("RESEND_API_KEY", "").strip()


def _send_blocking(to: str, subject: str, html: str) -> None:
    if not _HAS_RESEND or not _enabled():
        return
    key = _api_key()
    if not key:
        return
    try:
        _resend_lib.api_key = key
        _resend_lib.Emails.send({"from": _FROM, "to": [to], "subject": subject, "html": html})
        print(f"[email] sent '{subject}' to {to}")
    except Exception as e:
        print(f"[email] failed '{subject}' to {to}: {e}")


def _send(to: str, subject: str, html: str) -> None:
    """Dispatch in a daemon thread — never blocks the calling request."""
    threading.Thread(target=_send_blocking, args=(to, subject, html), daemon=True).start()


def _shell(body: str) -> str:
    """Wrap body in the standard dark-theme email shell."""
    return (
        '<!DOCTYPE html><html lang="fr">'
        '<head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1"></head>'
        '<body style="margin:0;padding:0;background:#0d0d0d">'
        '<div style="font-family:\'Helvetica Neue\',Arial,sans-serif;background:#0d0d0d;'
        'color:#F5F5F6;padding:48px 32px;max-width:560px;margin:0 auto">'
        '<div style="margin-bottom:32px">'
        '<img src="https://leanretention.com/public/logo.png" alt="LeanRetention"'
        ' height="36" style="display:block;max-width:180px" />'
        '</div>'
        + body
        + '<div style="margin-top:48px;padding-top:20px;border-top:1px solid rgba(255,255,255,.08)">'
        '<p style="color:rgba(245,245,246,.3);font-size:11px;margin:0">'
        'LeanRetention · '
        '<a href="mailto:hello@leanretention.com" style="color:#FF7751;text-decoration:none">'
        'Nous contacter</a></p></div>'
        '</div></body></html>'
    )


def _cta(url: str, label: str) -> str:
    return (
        '<a href="' + url + '" style="display:inline-block;background:#FF7751;color:#fff;'
        'padding:14px 28px;border-radius:8px;text-decoration:none;font-weight:700;'
        'font-size:15px;box-shadow:0 0 24px rgba(255,119,81,.35)">' + label + '</a>'
    )


def _h1(text: str) -> str:
    return (
        '<h1 style="font-size:26px;font-weight:800;letter-spacing:-.02em;margin:0 0 12px">'
        + text + '</h1>'
    )


def _p(text: str, extra_style: str = "") -> str:
    style = "font-size:16px;color:rgba(245,245,246,.65);line-height:1.7;margin:0 0 28px"
    if extra_style:
        style += ";" + extra_style
    return '<p style="' + style + '">' + text + '</p>'


def _first_name(profile: dict) -> str:
    parts = (profile.get("name") or profile.get("brandName") or "").split()
    return parts[0] if parts else "toi"


# ── A — Welcome ───────────────────────────────────────────────────────────────

def send_welcome(profile: dict) -> None:
    """Sent once when a new profile is created via Google OAuth (or waitlist)."""
    if profile.get("is_founder"):
        return
    email = (profile.get("email") or "").strip()
    if not email:
        return
    first = _first_name(profile)
    subject = "Bienvenue sur LeanRetention, " + first + " \U0001f44b"
    body = (
        _h1("Bienvenue sur LeanRetention, " + first + " \U0001f44b")
        + _p(
            "Ton compte est prêt. LeanRetention analyse ta vidéo, "
            "réécrit le hook, supprime les silences et exporte "
            "automatiquement en 9:16 et 16:9.<br><br>"
            "Ta première vidéo est "
            '<strong style="color:#FF7751">offerte</strong>. '
            "Aucune carte requise."
        )
        + _cta(_APP_URL, "Commencer l’édition →")
    )
    _send(email, subject, _shell(body))


# ── B — Vidéo prête ───────────────────────────────────────────────────────────

def send_video_ready(profile: dict) -> None:
    """Sent when a render job reaches status=done."""
    if profile.get("is_founder"):
        return
    email = (profile.get("email") or "").strip()
    if not email:
        return
    first = _first_name(profile)
    subject = "Ta vidéo est prête à télécharger \U0001f3ac"
    body = (
        _h1("Ta vidéo est prête à télécharger \U0001f3ac")
        + _p(
            "Hey " + first + ", ton édition vient de se terminer. "
            "Télécharge-la directement depuis l’app."
        )
        + _cta(_APP_URL, "Voir ma vidéo →")
    )
    _send(email, subject, _shell(body))


# ── C — Re-engagement ─────────────────────────────────────────────────────────

def send_reengagement(profile: dict, profile_path: Path) -> bool:
    """Sent if no video edited in >=7 days. Caller checks edit recency first.
    Handles per-profile throttle (no re-send within another 7-day window).
    Returns True if an email was queued."""
    if profile.get("is_founder"):
        return False
    email = (profile.get("email") or "").strip()
    if not email:
        return False
    last_ts = profile.get("reengagement_sent_at")
    if last_ts and (time.time() - float(last_ts)) < 7 * 24 * 3600:
        return False
    first = _first_name(profile)
    subject = "Tu n’as pas édité de vidéo depuis une semaine..."
    body = (
        _h1("Tu n’as pas édité de vidéo depuis une semaine...")
        + _p(
            "Hey " + first + ", ça fait 7 jours que tu n’es plus passé par ici.<br><br>"
            "Chaque vidéo non éditée, c’est du temps perdu et de la "
            "rétention qui s’envole. Reprends là où tu t’es "
            "arrêté. Moins de 5 minutes pour uploader et lancer l’édition."
        )
        + _cta(_APP_URL, "Reprendre l’édition →")
    )
    try:
        profile["reengagement_sent_at"] = time.time()
        profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[email] throttle stamp failed for {profile_path.stem}: {e}")
    _send(email, subject, _shell(body))
    return True


# ── D — Quota warning ─────────────────────────────────────────────────────────

def send_quota_warning(profile: dict, profile_path: Path, used: int, limit: int) -> None:
    """Sent when usage crosses 80% of the monthly quota. Once per calendar month."""
    if profile.get("is_founder"):
        return
    email = (profile.get("email") or "").strip()
    if not email:
        return
    this_month = datetime.utcnow().strftime("%Y-%m")
    if profile.get("quota_warning_sent_month") == this_month:
        return
    first = _first_name(profile)
    remaining = limit - used
    subject = "Tu approches de ta limite de vidéos ce mois-ci"
    body = (
        _h1("Tu approches de ta limite de vidéos ce mois-ci")
        + _p("Hey " + first + ",", extra_style="margin:0 0 8px")
        + _p(
            "Tu as utilisé "
            '<strong style="color:#FF7751">'
            + str(used) + " vidéo" + ("s" if used > 1 else "") + " sur " + str(limit)
            + "</strong>"
            " ce mois-ci. Il te reste seulement "
            "<strong>" + str(remaining) + " créneau" + ("x" if remaining > 1 else "") + "</strong>."
            "<br><br>Passe à un plan supérieur pour ne jamais être bloqué."
        )
        + _cta(_PRICING_URL, "Voir les plans →")
    )
    try:
        profile["quota_warning_sent_month"] = this_month
        profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[email] quota throttle stamp failed for {profile_path.stem}: {e}")
    _send(email, subject, _shell(body))


# ── E — Nurture J+2 (pas encore édité) ───────────────────────────────────────

def send_nurture_d2(profile: dict, profile_path: Path) -> bool:
    """J+2 sans render. Returns True if email was queued."""
    if profile.get("is_founder"):
        return False
    email = (profile.get("email") or "").strip()
    if not email:
        return False
    if profile.get("nurture_d2_sent"):
        return False
    first = _first_name(profile)
    subject = "Ta première vidéo t'attend, " + first
    body = (
        _h1("Ta première vidéo t'attend")
        + _p(
            "Hey " + first + ", tu t'es inscrit il y a 2 jours "
            "mais tu n'as pas encore lancé ton premier montage.<br><br>"
            "C'est normal d'hésiter. LeanRetention est là pour supprimer "
            "le montage de ta liste de tâches, pas pour l'allonger.<br><br>"
            "Balance ta vidéo brute. On s'occupe du reste en moins de 5 minutes."
        )
        + _cta(_APP_URL, "Lancer mon premier montage →")
    )
    try:
        profile["nurture_d2_sent"] = time.time()
        profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[email] nurture_d2 stamp failed for {profile_path.stem}: {e}")
    _send(email, subject, _shell(body))
    return True


# ── F — Nurture J+5 (conseil rétention) ──────────────────────────────────────

def send_nurture_d5(profile: dict, profile_path: Path) -> bool:
    """J+5 sans render. Returns True if email was queued."""
    if profile.get("is_founder"):
        return False
    email = (profile.get("email") or "").strip()
    if not email:
        return False
    if profile.get("nurture_d5_sent"):
        return False
    first = _first_name(profile)
    subject = "Le secret des vidéos qui gardent l'attention"
    body = (
        _h1("Le secret des vidéos qui gardent l'attention")
        + _p(
            "Hey " + first + ", voici ce que les créateurs avec 60 % de "
            "rétention font différemment."
        )
        + _p(
            '<strong style="color:#FF7751">1. Le hook en 3 secondes.</strong><br>'
            "Commence par la conclusion ou la tension. Pas par l'intro. "
            "Pas par \"Bonjour, aujourd'hui on va parler de...\"<br><br>"
            '<strong style="color:#FF7751">2. Les pauses courtes.</strong><br>'
            "Chaque silence de plus de 0,8 seconde fait décrocher. "
            "LeanRetention les supprime automatiquement à chaque export.<br><br>"
            '<strong style="color:#FF7751">3. La relance à mi-vidéo.</strong><br>'
            "Ajoute une promesse ou une question à la moitié de ta vidéo "
            "pour relancer l'attention."
        )
        + _cta(_APP_URL, "Tester sur ma prochaine vidéo →")
    )
    try:
        profile["nurture_d5_sent"] = time.time()
        profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[email] nurture_d5 stamp failed for {profile_path.stem}: {e}")
    _send(email, subject, _shell(body))
    return True


# ── G — Nurture J+10 (démo avant/après) ──────────────────────────────────────

def send_nurture_d10(profile: dict, profile_path: Path) -> bool:
    """J+10 sans render. Returns True if email was queued."""
    if profile.get("is_founder"):
        return False
    email = (profile.get("email") or "").strip()
    if not email:
        return False
    if profile.get("nurture_d10_sent"):
        return False
    first = _first_name(profile)
    subject = "Avant / Après LeanRetention (résultat réel)"
    body = (
        _h1("Avant / Après LeanRetention")
        + _p(
            "Hey " + first + ", voici ce que donne LeanRetention "
            "sur une vidéo brute de 8 minutes."
        )
        + (
            '<div style="background:rgba(255,119,81,.08);border:1px solid '
            'rgba(255,119,81,.2);border-radius:12px;padding:20px 24px;margin:0 0 28px">'
            '<p style="margin:0 0 8px;font-size:12px;color:rgba(245,245,246,.4);'
            'text-transform:uppercase;letter-spacing:.08em">Avant</p>'
            '<p style="margin:0 0 20px;font-size:15px;color:rgba(245,245,246,.65)">'
            "8 min 12 sec. 12 % de rétention. 4 silences de plus de 2 secondes. "
            "Hook flou.</p>"
            '<p style="margin:0 0 8px;font-size:12px;color:#FF7751;'
            'text-transform:uppercase;letter-spacing:.08em">Après</p>'
            '<p style="margin:0;font-size:15px;color:rgba(245,245,246,.65)">'
            "2 min 38 sec. 61 % de rétention. Silences supprimés. "
            "Hook réécrit automatiquement.</p>"
            "</div>"
        )
        + _p(
            "Le même résultat t'attend. Upload ta vidéo, "
            "LeanRetention fait le montage en quelques minutes."
        )
        + _cta(_APP_URL, "Voir ma vidéo transformée →")
    )
    try:
        profile["nurture_d10_sent"] = time.time()
        profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[email] nurture_d10 stamp failed for {profile_path.stem}: {e}")
    _send(email, subject, _shell(body))
    return True


# ── H — Post-render J+1 ───────────────────────────────────────────────────────

def send_post_render_d1(
    profile: dict, profile_path: Path, render_minutes: int | None = None
) -> bool:
    """J+1 after first completed render (window: 1-7 days). Returns True if email was queued."""
    if profile.get("is_founder"):
        return False
    email = (profile.get("email") or "").strip()
    if not email:
        return False
    if profile.get("post_render_d1_sent"):
        return False
    first = _first_name(profile)

    if render_minutes and render_minutes >= 1:
        time_str = f"en {render_minutes} minute{'s' if render_minutes > 1 else ''}"
    else:
        time_str = "en quelques minutes"

    subject = "Ta vidéo a été montée " + time_str + ", " + first
    body = (
        _h1("Ta vidéo a été montée " + time_str + ".")
        + _p(
            "Hey " + first + ", tu viens de faire quelque chose que la plupart "
            "des créateurs repoussent a demain.<br><br>"
            "Tu as filmé. Tu as uploadé. LeanRetention a fait le montage " + time_str + "."
        )
        + _p(
            "Si tu postes 3 vidéos par semaine, LeanRetention peut t'en monter "
            '<strong style="color:#FF7751">12 ce mois</strong> '
            "sans toucher a un logiciel de montage.<br><br>"
            "Voila comment :"
        )
        + (
            '<div style="background:rgba(255,119,81,.08);border:1px solid '
            'rgba(255,119,81,.2);border-radius:12px;padding:20px 24px;margin:0 0 28px">'
            '<p style="margin:0 0 12px;font-size:15px;color:rgba(245,245,246,.9)">'
            '<strong style="color:#FF7751">1.</strong> '
            "Publie la video d'hier dans les prochaines 24h.</p>"
            '<p style="margin:0 0 12px;font-size:15px;color:rgba(245,245,246,.9)">'
            '<strong style="color:#FF7751">2.</strong> '
            "Filme ta prochaine video cette semaine.</p>"
            '<p style="margin:0;font-size:15px;color:rgba(245,245,246,.9)">'
            '<strong style="color:#FF7751">3.</strong> '
            "Passe au plan Starter pour monter les 15 suivantes ce mois.</p>"
            '</div>'
        )
        + _cta(_PRICING_URL, "Voir les plans →")
    )
    try:
        profile["post_render_d1_sent"] = time.time()
        profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[email] post_render_d1 stamp failed for {profile_path.stem}: {e}")
    _send(email, subject, _shell(body))
    return True


# ── I — Report notification (founder alert) ───────────────────────────────────

_FOUNDER_ALERT_EMAIL = "leankanwa@gmail.com"


def send_report_notification(report: dict) -> None:
    """Alert the founder on every user report. Not gated by is_founder."""
    if not _HAS_RESEND or not _enabled() or not _api_key():
        return
    email_user = report.get("email") or "anonyme"
    page = (report.get("url") or "inconnue")[:120]
    raw_msg = report.get("message") or ""
    safe_msg = raw_msg.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    ts = report.get("timestamp", "")
    try:
        ts = datetime.fromisoformat(ts).strftime("%d/%m/%Y %H:%M UTC")
    except Exception:
        pass
    short = raw_msg[:60] + ("..." if len(raw_msg) > 60 else "")
    subject = "Signalement : " + short
    body = (
        _h1("Nouveau signalement")
        + _p(
            "<strong>De :</strong> " + email_user + "<br>"
            "<strong>Page :</strong> " + page + "<br>"
            "<strong>Date :</strong> " + str(ts),
            extra_style="margin:0 0 16px",
        )
        + (
            '<div style="background:rgba(255,119,81,.08);border-left:3px solid #FF7751;'
            'padding:16px 20px;border-radius:0 8px 8px 0;margin:0 0 28px">'
            '<p style="margin:0;font-size:15px;color:#F5F5F6;line-height:1.7;'
            'white-space:pre-wrap">' + safe_msg + "</p></div>"
        )
    )
    _send(_FOUNDER_ALERT_EMAIL, subject, _shell(body))
