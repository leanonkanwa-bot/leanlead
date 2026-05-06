from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import create_access_token, get_current_coach, hash_password, verify_password
from ..database import get_db
from .. import models

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str


class OnboardRequest(BaseModel):
    niche: str
    offer_description: str
    target_audience: str
    calendly_link: str | None = None
    airtable_base_id: str | None = None
    airtable_api_key: str | None = None
    apify_api_key: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    coach_id: int
    name: str
    onboarded: bool


@router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(models.Coach).filter(models.Coach.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    coach = models.Coach(
        email=req.email,
        password_hash=hash_password(req.password),
        name=req.name,
    )
    db.add(coach)
    db.commit()
    db.refresh(coach)
    token = create_access_token(coach.id)
    return TokenResponse(access_token=token, coach_id=coach.id, name=coach.name, onboarded=False)


@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    coach = db.query(models.Coach).filter(models.Coach.email == form.username).first()
    if not coach or not verify_password(form.password, coach.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(coach.id)
    return TokenResponse(
        access_token=token, coach_id=coach.id, name=coach.name, onboarded=coach.onboarded
    )


class SettingsRequest(BaseModel):
    niche: str | None = None
    offer_description: str | None = None
    target_audience: str | None = None
    calendly_link: str | None = None
    apify_api_key: str | None = None


@router.patch("/settings")
def update_settings(
    req: SettingsRequest,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    if req.niche is not None:
        coach.niche = req.niche
    if req.offer_description is not None:
        coach.offer_description = req.offer_description
    if req.target_audience is not None:
        coach.target_audience = req.target_audience
    if req.calendly_link is not None:
        coach.calendly_link = req.calendly_link
    if req.apify_api_key is not None:
        coach.apify_api_key = req.apify_api_key or None
    db.commit()
    return {"ok": True}


@router.get("/me")
def me(coach: models.Coach = Depends(get_current_coach)):
    return {
        "id": coach.id,
        "email": coach.email,
        "name": coach.name,
        "niche": coach.niche,
        "offer_description": coach.offer_description,
        "target_audience": coach.target_audience,
        "calendly_link": coach.calendly_link,
        "onboarded": coach.onboarded,
        "has_apify_key": bool(coach.apify_api_key),
    }


@router.post("/onboard")
def onboard(req: OnboardRequest, coach: models.Coach = Depends(get_current_coach), db: Session = Depends(get_db)):
    coach.niche = req.niche
    coach.offer_description = req.offer_description
    coach.target_audience = req.target_audience
    coach.calendly_link = req.calendly_link
    if req.airtable_base_id:
        coach.airtable_base_id = req.airtable_base_id
    if req.airtable_api_key:
        coach.airtable_api_key = req.airtable_api_key
    if req.apify_api_key:
        coach.apify_api_key = req.apify_api_key
    coach.onboarded = True
    db.commit()
    db.refresh(coach)
    return {"ok": True, "onboarded": True}
