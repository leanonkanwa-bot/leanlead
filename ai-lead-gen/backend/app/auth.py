import os
import secrets
import smtplib
import base64
import hashlib
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText

import bcrypt
import jwt
from cryptography.fernet import Fernet
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import get_db
from . import models

# ---------------------------------------------------------------------------
# Social handle encryption (Fernet symmetric)
# ---------------------------------------------------------------------------

def _get_fernet() -> "Fernet | None":
    key_raw = os.getenv("ENCRYPTION_KEY", "")
    if not key_raw:
        return None
    # Derive 32-byte key from whatever string the user provides
    digest = hashlib.sha256(key_raw.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_handle(value: "str | None") -> "str | None":
    if not value:
        return value
    f = _get_fernet()
    if f is None:
        return value
    return f.encrypt(value.encode()).decode()


def decrypt_handle(value: "str | None") -> "str | None":
    if not value:
        return value
    f = _get_fernet()
    if f is None:
        return value
    try:
        return f.decrypt(value.encode()).decode()
    except Exception:
        return value  # already plain text (migration case)


# ---------------------------------------------------------------------------
# Email verification helpers
# ---------------------------------------------------------------------------

def _send_welcome_email(to_email: str, coach_name: str, trial_end_date: "datetime") -> bool:
    """Send welcome email with trial details. Returns True if sent."""
    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASSWORD", "")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)
    base_url = os.getenv("APP_BASE_URL", "http://localhost:8000")

    if not smtp_host or not smtp_user:
        print(f"[email] SMTP not configured — skipping welcome email for {to_email}")
        return False

    trial_date_str = trial_end_date.strftime("%d/%m/%Y")
    body = f"""Bonjour {coach_name},

Bienvenue sur LeanLead ! 🎉

Vous bénéficiez d'un essai Agency GRATUIT de 14 jours, valable jusqu'au {trial_date_str}.

Pendant votre essai, vous avez accès à toutes les fonctionnalités Agency :
• Prospects illimités sur toutes les plateformes
• Agent autonome de génération de leads
• Séquences de nurturing automatisées
• Intelligence prédictive avancée

Commencez dès maintenant : {base_url}/dashboard

À la fin de votre essai, vous pourrez choisir :
• Growth €49/mois — 200 leads/mois, 5 plateformes
• Agency €129/mois — tout inclus, illimité

— L'équipe LeanLead
"""
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = "Bienvenue sur LeanLead — Essai Agency gratuit 14 jours !"
    msg["From"] = smtp_from
    msg["To"] = to_email

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as s:
            s.starttls()
            s.login(smtp_user, smtp_pass)
            s.sendmail(smtp_from, [to_email], msg.as_string())
        print(f"[email] Welcome email sent to {to_email}")
        return True
    except Exception as exc:
        print(f"[email] Failed to send welcome email: {exc}")
        return False


def _send_trial_reminder_email(to_email: str, coach_name: str, days_left: int, trial_end_date: "datetime") -> bool:
    """Send trial expiry reminder. Returns True if sent."""
    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASSWORD", "")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)
    base_url = os.getenv("APP_BASE_URL", "http://localhost:8000")

    if not smtp_host or not smtp_user:
        print(f"[email] SMTP not configured — skipping trial reminder for {to_email}")
        return False

    trial_date_str = trial_end_date.strftime("%d/%m/%Y")
    body = f"""Bonjour {coach_name},

Votre essai Agency LeanLead se termine dans {days_left} jour{"s" if days_left > 1 else ""} (le {trial_date_str}).

Pour continuer à générer des leads sans interruption, choisissez votre plan :

→ Growth €49/mois : 200 leads/mois, 5 plateformes
→ Agency €129/mois : illimité, agent autonome, toutes fonctionnalités

Upgrader maintenant : {base_url}/dashboard

Après le {trial_date_str}, votre compte passera automatiquement en plan Gratuit (20 leads, Instagram uniquement).

— L'équipe LeanLead
"""
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = f"⚠️ Votre essai LeanLead expire dans {days_left} jour{'s' if days_left > 1 else ''}"
    msg["From"] = smtp_from
    msg["To"] = to_email

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as s:
            s.starttls()
            s.login(smtp_user, smtp_pass)
            s.sendmail(smtp_from, [to_email], msg.as_string())
        print(f"[email] Trial reminder ({days_left}d) sent to {to_email}")
        return True
    except Exception as exc:
        print(f"[email] Failed to send trial reminder: {exc}")
        return False


def _send_verification_email(to_email: str, token: str, coach_name: str) -> bool:
    """Send verification email. Returns True if sent, False if SMTP not configured."""
    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASSWORD", "")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)
    base_url = os.getenv("APP_BASE_URL", "http://localhost:8000")

    if not smtp_host or not smtp_user:
        print(f"[email] SMTP not configured — verification token for {to_email}: {token}")
        return False

    verify_url = f"{base_url}/api/auth/verify-email?token={token}"
    body = f"""Bonjour {coach_name},

Bienvenue sur LeanLead ! Cliquez sur le lien ci-dessous pour vérifier votre email :

{verify_url}

Ce lien expire dans 48h.

— L'équipe LeanLead
"""
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = "Vérifiez votre email LeanLead"
    msg["From"] = smtp_from
    msg["To"] = to_email

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as s:
            s.starttls()
            s.login(smtp_user, smtp_pass)
            s.sendmail(smtp_from, [to_email], msg.as_string())
        print(f"[email] Verification email sent to {to_email}")
        return True
    except Exception as exc:
        print(f"[email] Failed to send verification email: {exc}")
        return False


# ---------------------------------------------------------------------------

SECRET_KEY = os.getenv("JWT_SECRET", "change-me-to-a-random-secret-string-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24 * 7  # 7 days

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def create_access_token(coach_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    return jwt.encode({"sub": str(coach_id), "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def get_current_coach(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.Coach:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        coach_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise exc
    coach = db.query(models.Coach).filter(models.Coach.id == coach_id).first()
    if not coach:
        raise exc
    return coach
