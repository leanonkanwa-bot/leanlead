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
