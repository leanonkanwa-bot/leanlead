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
    icp_pain_points: list[str] | None = None
    calendly_link: str | None = None
    instagram_handle: str | None = None
    tiktok_handle: str | None = None
    twitter_handle: str | None = None
    reddit_handle: str | None = None
    facebook_url: str | None = None
    linkedin_url: str | None = None


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
    icp_pain_points: list[str] | None = None
    calendly_link: str | None = None
    instagram_handle: str | None = None
    tiktok_handle: str | None = None
    twitter_handle: str | None = None
    reddit_handle: str | None = None
    facebook_url: str | None = None
    linkedin_url: str | None = None
    offer_price: float | None = None
    testimonials: list[dict] | None = None  # [{name, situation, result}, ...]


@router.patch("/settings")
def update_settings(
    req: SettingsRequest,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    import json as _json
    data = req.model_dump(exclude_unset=True)
    for field, value in data.items():
        if field in ("icp_pain_points", "testimonials"):
            setattr(coach, field, _json.dumps(value) if value is not None else None)
        elif field in ("instagram_handle", "tiktok_handle", "twitter_handle", "reddit_handle"):
            setattr(coach, field, (value or "").lstrip("@") or None)
        else:
            setattr(coach, field, value)
    coach.onboarded = True
    db.commit()
    return {"ok": True}


@router.get("/me")
def me(coach: models.Coach = Depends(get_current_coach)):
    import json as _json
    return {
        "id": coach.id,
        "email": coach.email,
        "name": coach.name,
        "niche": coach.niche,
        "offer_description": coach.offer_description,
        "target_audience": coach.target_audience,
        "calendly_link": coach.calendly_link,
        "plan": getattr(coach, "plan", "free") or "free",
        "instagram_handle": coach.instagram_handle,
        "tiktok_handle": coach.tiktok_handle,
        "twitter_handle": getattr(coach, "twitter_handle", None),
        "reddit_handle": getattr(coach, "reddit_handle", None),
        "facebook_url": coach.facebook_url,
        "linkedin_url": coach.linkedin_url,
        "onboarded": coach.onboarded,
        "offer_price": coach.offer_price,
        "icp_pain_points": _json.loads(coach.icp_pain_points) if coach.icp_pain_points else [],
        "testimonials": _json.loads(coach.testimonials) if getattr(coach, "testimonials", None) else [],
    }


class DetectNicheRequest(BaseModel):
    description: str


def _dev_mock_niche(desc: str) -> dict:
    """Keyword-based mock response for dev/test environments without a real API key."""
    d = desc.lower()
    if any(w in d for w in ["business", "entrepreneur", "scal", "revenus", "vente", "client", "agence"]):
        return {
            "niche": "Business en ligne",
            "target_audience": "Entrepreneurs et indépendants qui veulent développer leur activité en ligne et atteindre 10k€/mois sans épuisement.",
            "pain_points": [
                "Je travaille 60h/semaine et mes revenus stagnent toujours au même niveau",
                "Je ne sais pas comment trouver des clients réguliers en ligne",
                "J'ai peur d'augmenter mes tarifs et de perdre les quelques clients que j'ai",
            ],
            "hashtags": ["pasentrepreneur", "galeredentrepreneur", "revenusinstables", "clientsintrouvables",
                         "burnoutentrepreneur", "indépendant", "tropdetravail", "freelancegalère"],
        }
    if any(w in d for w in ["maigrir", "poids", "minceur", "fitness", "sport", "corps", "nutrition"]):
        return {
            "niche": "Remise en forme",
            "target_audience": "Femmes de 30-45 ans qui veulent perdre du poids durablement sans régime restrictif ni privations.",
            "pain_points": [
                "J'ai essayé tous les régimes mais je reprends toujours le poids perdu en quelques semaines",
                "Je n'arrive pas à me motiver à faire du sport régulièrement plus de 2 semaines",
                "Mon corps ne répond plus comme avant depuis ma grossesse et ça me déprime",
            ],
            "hashtags": ["regimeechec", "plusjamaisderegime", "corpsapresaccouchement", "motivationsport",
                         "mincirfemme", "pesermoins", "fatiguedemaigrir", "rechutedieete"],
        }
    if any(w in d for w in ["confiance", "estime", "mental", "mindset", "développement", "personnel", "anxiété"]):
        return {
            "niche": "Confiance en soi",
            "target_audience": "Personnes qui souffrent de manque de confiance et veulent s'affirmer dans leur vie professionnelle et personnelle.",
            "pain_points": [
                "Je n'ose jamais prendre la parole en réunion tellement j'ai peur du jugement des autres",
                "Je dis toujours oui même quand ça me pèse parce que je n'arrive pas à décevoir",
                "Je sabote tout ce qui commence bien dans ma vie sans comprendre pourquoi",
            ],
            "hashtags": ["manquedeconfiance", "peurduregard", "syndromeimposteur", "oserparler",
                         "autosabotage", "anxietesociale", "peurdejugement", "hypersensible"],
        }
    if any(w in d for w in ["relation", "couple", "amour", "séduction", "dating", "rencontre"]):
        return {
            "niche": "Relations amoureuses",
            "target_audience": "Célibataires et personnes en couple qui veulent construire une relation épanouissante et attirer le bon partenaire.",
            "pain_points": [
                "Je rencontre toujours le même type de personnes qui me font souffrir",
                "Je suis célibataire depuis des années malgré tous mes efforts pour me faire remarquer",
                "Mon couple s'est éteint progressivement et on ne sait plus comment se reconnecter",
            ],
            "hashtags": ["celibatairechronique", "attirerlamour", "relationtoxique", "couplequis éloigne",
                         "problemecouple", "rencontreimpossible", "seductionrate", "solitudeamoureuse"],
        }
    return {
        "niche": "Coaching personnel",
        "target_audience": "Personnes en transition de vie qui cherchent à retrouver clarté, direction et épanouissement durable.",
        "pain_points": [
            "Je me sens complètement perdu(e) et je ne sais plus ce que je veux vraiment",
            "J'ai l'impression de vivre la vie des autres, pas la mienne",
            "Je tourne en rond depuis des mois sans avancer malgré tous mes efforts",
        ],
        "hashtags": ["perduedansmavie", "transitiondevie", "quefairedemavie", "sansdirection",
                     "changement", "reconversionforcee", "viequineplaitpas", "sensduvide"],
    }


@router.post("/detect-niche")
def detect_niche(req: DetectNicheRequest, coach: models.Coach = Depends(get_current_coach)):
    """
    Takes a free-text coaching description and returns AI-detected niche,
    ICP pain points, and pain-expression hashtags. No DB write — caller confirms.
    Falls back to keyword-based mock when no valid API key is present (dev mode).
    """
    import json as _json
    import traceback
    import anthropic

    desc = req.description.strip()
    if len(desc) < 10:
        raise HTTPException(status_code=400, detail="Description trop courte (minimum 10 caractères)")

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    print(f"[detect-niche] api_key present={bool(api_key)} prefix={api_key[:12] if api_key else 'NONE'}...")

    is_real_key = bool(api_key) and len(api_key) > 40 and not api_key.startswith("sk-ant-api03-test-key")
    if not is_real_key:
        print("[detect-niche] DEV MODE: no valid API key — returning keyword-based mock")
        result = _dev_mock_niche(desc)
        result["_demo"] = True
        return result

    try:
        print("[detect-niche] Calling claude-opus-4-7...")
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=600,
            messages=[{
                "role": "user",
                "content": f"""You are an expert at analyzing coaching niches. A coach described their work in their own words.

Description: "{desc}"

Your task — respond in the SAME LANGUAGE as the description:
1. "niche": A precise 2-5 word category label (e.g. "Confiance en soi", "Business en ligne", "Remise en forme femmes 40+")
2. "target_audience": 1-2 sentences describing exactly who this coach helps and what transformation they get
3. "pain_points": Exactly 3 pains the ideal client expresses on social media — in first person, emotional, specific to this niche. These should sound like real posts, not marketing copy.
4. "hashtags": 8-10 Instagram/TikTok hashtags used by POTENTIAL CLIENTS who are venting about this problem — NOT coaching hashtags, NOT solution hashtags. Think about what a struggling person posts.

Respond ONLY with valid JSON, no markdown:
{{"niche": "...", "target_audience": "...", "pain_points": ["...", "...", "..."], "hashtags": ["tag1", "tag2", ...]}}""",
            }],
        )
        text = msg.content[0].text.strip()
        print(f"[detect-niche] Raw response (first 200 chars): {text[:200]}")
        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError(f"No JSON object in response: {text[:300]}")
        result = _json.loads(text[start:end])
        print(f"[detect-niche] Parsed niche={result.get('niche')}")
    except anthropic.AuthenticationError as exc:
        print(f"[detect-niche] AUTH ERROR: {exc}")
        raise HTTPException(status_code=500, detail="Clé API Anthropic invalide ou expirée — vérifiez ANTHROPIC_API_KEY dans votre .env")
    except anthropic.APIConnectionError as exc:
        print(f"[detect-niche] CONNECTION ERROR: {exc}")
        raise HTTPException(status_code=503, detail="Impossible de joindre l'API Anthropic — vérifiez votre connexion internet")
    except HTTPException:
        raise
    except Exception as exc:
        print(f"[detect-niche] UNEXPECTED ERROR: {type(exc).__name__}: {exc}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'analyse : {type(exc).__name__}: {exc}")

    result["pain_points"] = result.get("pain_points", [])[:5]
    result["hashtags"] = result.get("hashtags", [])[:10]
    return result


@router.post("/onboard")
def onboard(req: OnboardRequest, coach: models.Coach = Depends(get_current_coach), db: Session = Depends(get_db)):
    import json as _json
    coach.niche = req.niche
    coach.offer_description = req.offer_description
    coach.target_audience = req.target_audience
    coach.calendly_link = req.calendly_link
    coach.instagram_handle = (req.instagram_handle or "").lstrip("@") or None
    coach.tiktok_handle = (req.tiktok_handle or "").lstrip("@") or None
    coach.twitter_handle = (req.twitter_handle or "").lstrip("@") or None
    coach.reddit_handle = (req.reddit_handle or "").lstrip("@") or None
    coach.facebook_url = req.facebook_url or None
    coach.linkedin_url = req.linkedin_url or None
    if req.icp_pain_points is not None:
        coach.icp_pain_points = _json.dumps(req.icp_pain_points)
    coach.onboarded = True
    db.commit()
    db.refresh(coach)
    return {"ok": True, "onboarded": True}
