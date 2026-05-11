from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session
import json
import os

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
    icp_pain_points: list[str] | None = None


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
    offer_price: float | None = None
    icp_pain_points: list[str] | None = None


@router.patch("/settings")
def update_settings(
    req: SettingsRequest,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    data = req.model_dump(exclude_unset=True)
    for field, value in data.items():
        if field == "apify_api_key":
            setattr(coach, field, value or None)
        elif field == "icp_pain_points":
            setattr(coach, field, json.dumps(value) if value is not None else None)
        else:
            setattr(coach, field, value)
    coach.onboarded = True
    db.commit()
    return {"ok": True}


@router.get("/me")
def me(coach: models.Coach = Depends(get_current_coach)):
    pain_points = []
    if coach.icp_pain_points:
        try:
            pain_points = json.loads(coach.icp_pain_points)
        except Exception:
            pass
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
        "offer_price": coach.offer_price,
        "icp_pain_points": pain_points,
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
    if req.icp_pain_points is not None:
        coach.icp_pain_points = json.dumps(req.icp_pain_points)
    coach.onboarded = True
    db.commit()
    db.refresh(coach)
    return {"ok": True, "onboarded": True}


class DetectNicheRequest(BaseModel):
    description: str


@router.post("/detect-niche")
def detect_niche(req: DetectNicheRequest):
    """Use Claude to auto-detect niche, target audience, pain points, and hashtags from a free-form description."""
    import anthropic as _anthropic

    if not req.description or len(req.description.strip()) < 10:
        raise HTTPException(status_code=400, detail="Description too short")

    client = _anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    msg = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=512,
        messages=[{
            "role": "user",
            "content": f"""You are an expert at identifying coaching niches.

From this description, extract:
- niche: a concise 1-sentence niche description
- target_audience: who the ideal client is (1-2 sentences)
- pain_points: 4-6 specific pain points the ICP has (array of strings)
- hashtags: 6 hashtags (without #) that POTENTIAL CLIENTS (not coaches) use

Description: {req.description}

Respond ONLY with valid JSON:
{{"niche": "...", "target_audience": "...", "pain_points": ["..."], "hashtags": ["..."]}}""",
        }],
    )
    text = msg.content[0].text
    start, end = text.find("{"), text.rfind("}") + 1
    return json.loads(text[start:end])
