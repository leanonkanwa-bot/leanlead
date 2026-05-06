import os
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .database import get_db
from . import models

SECRET_KEY = os.getenv("JWT_SECRET", "change-me-to-a-random-secret-string-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24 * 7  # 7 days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(coach_id: int) -> str:
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
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
    except (JWTError, KeyError, ValueError):
        raise exc
    coach = db.query(models.Coach).filter(models.Coach.id == coach_id).first()
    if not coach:
        raise exc
    return coach
