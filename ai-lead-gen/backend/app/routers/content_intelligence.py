"""
Content Intelligence — analyze a coach's social content to find lead-gen opportunities.

POST /api/content-intelligence/analyze   – start analysis (background)
GET  /api/content-intelligence           – get latest analysis result
"""
import json
import os
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_coach, decrypt_handle
from ..database import get_db
from .. import models

router = APIRouter(prefix="/api/content-intelligence", tags=["content-intelligence"])


class AnalyzeRequest(BaseModel):
    platform: str = "instagram"   # instagram|tiktok|youtube
    handle: str | None = None     # override stored handle


def _fetch_content_data(platform: str, handle: str) -> list[dict]:
    """Fetch recent content data for a handle using ddgs search."""
    try:
        from ddgs import DDGS
        query = f"site:{platform}.com {handle} comments views"
        if platform == "instagram":
            query = f"instagram.com/{handle} posts"
        elif platform == "tiktok":
            query = f"tiktok.com/@{handle}"
        elif platform == "youtube":
            query = f"youtube.com {handle} videos"

        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=15):
                results.append({
                    "title": r.get("title", ""),
                    "body": r.get("body", ""),
                    "href": r.get("href", ""),
                })
        return results
    except Exception as e:
        print(f"[content-intel] ddgs error: {e}")
        return []


def _analyze_with_claude(
    platform: str,
    handle: str,
    content_data: list[dict],
    coach_niche: str,
    coach_offer: str,
) -> dict:
    """Use Claude to analyze content and extract lead-gen insights."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or len(api_key) < 40 or api_key.startswith("sk-ant-api03-test"):
        return _mock_analysis(handle, platform)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        content_text = "\n\n".join(
            f"[Post/Video]\nTitre: {item['title']}\nDescription: {item['body'][:300]}"
            for item in content_data[:12]
        ) if content_data else "Données insuffisantes - analyse basée sur le profil uniquement"

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1200,
            messages=[{
                "role": "user",
                "content": f"""Analyse le contenu social d'un coach.

Plateforme: {platform}
Handle: @{handle}
Niche du coach: {coach_niche}
Offre: {coach_offer}

Données de contenu récent:
{content_text}

Analyse et retourne un JSON avec:
1. "top_content_themes": liste de 3-5 thèmes de contenu qui génèrent le plus d'engagement (basé sur les titres/descriptions)
2. "audience_pain_points": liste de 5-8 points de douleur que l'audience exprime dans les commentaires
3. "audience_questions": liste de 5 questions fréquentes de l'audience
4. "suggested_topics": liste de 5 sujets de contenu à créer pour générer plus de leads qualifiés
5. "lead_gen_hooks": liste de 3 accroches (hooks) de contenu qui performent bien dans cette niche
6. "keyword_triggers": liste de 3-5 mots-clés que l'audience commente naturellement (ex: "GUIDE", "FOI", "MÉTHODE")
7. "best_posting_time": moment optimal pour poster (ex: "Lundi-Mercredi 18h-20h")
8. "content_score": score 0-100 du potentiel de génération de leads du compte actuel

Réponds UNIQUEMENT avec du JSON valide, sans markdown.""",
            }],
        )

        text = response.content[0].text.strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        return json.loads(text[start:end])

    except Exception as e:
        print(f"[content-intel] Claude error: {e}")
        return _mock_analysis(handle, platform)


def _mock_analysis(handle: str, platform: str) -> dict:
    return {
        "top_content_themes": [
            "Transformation client (avant/après)",
            "Erreurs fréquentes dans la niche",
            "Témoignages et résultats",
            "Conseils rapides et actionnables",
        ],
        "audience_pain_points": [
            "Manque de résultats malgré les efforts",
            "Ne sait pas par où commencer",
            "A essayé des solutions qui n'ont pas marché",
            "Manque de temps ou d'argent",
            "Peur d'investir sans garantie",
        ],
        "audience_questions": [
            f"Comment tu as commencé @{handle} ?",
            "C'est possible pour quelqu'un comme moi ?",
            "Tu as un programme ou une formation ?",
            "Combien de temps ça prend ?",
            "Tu fais des coachings individuels ?",
        ],
        "suggested_topics": [
            "La méthode exacte que j'utilise avec mes clients pour [résultat]",
            "3 erreurs qui empêchent 90% des gens d'obtenir [résultat]",
            "Ce que j'aurais aimé savoir avant de commencer",
            "Témoignage client : de [situation] à [résultat] en [temps]",
            "Réponse à vos questions les plus posées",
        ],
        "lead_gen_hooks": [
            "Commente GUIDE pour recevoir ma méthode gratuite",
            "Tape OUI en commentaire si tu veux que je t'explique comment",
            "Commente COACHING pour réserver un appel découverte",
        ],
        "keyword_triggers": ["GUIDE", "OUI", "COACHING", "MÉTHODE", "INFO"],
        "best_posting_time": "Mardi-Jeudi 18h-21h et Samedi 10h-12h",
        "content_score": 65,
        "_demo": True,
    }


def _run_analysis(coach_id: int, platform: str, handle: str):
    """Background task: fetch + analyze content, save to DB."""
    from ..database import SessionLocal
    db = SessionLocal()
    try:
        coach = db.query(models.Coach).filter(models.Coach.id == coach_id).first()
        if not coach:
            return

        content_data = _fetch_content_data(platform, handle)
        analysis = _analyze_with_claude(
            platform=platform,
            handle=handle,
            content_data=content_data,
            coach_niche=coach.niche or "",
            coach_offer=coach.offer_description or "",
        )

        # Upsert analysis record
        existing = db.query(models.ContentAnalysis).filter(
            models.ContentAnalysis.coach_id == coach_id,
            models.ContentAnalysis.platform == platform,
            models.ContentAnalysis.handle == handle,
        ).first()

        if existing:
            existing.analysis_data = json.dumps(analysis)
            existing.analyzed_at = datetime.utcnow()
        else:
            record = models.ContentAnalysis(
                coach_id=coach_id,
                platform=platform,
                handle=handle,
                analysis_data=json.dumps(analysis),
            )
            db.add(record)

        db.commit()
        print(f"[content-intel] Analysis complete for @{handle} on {platform}")
    except Exception as e:
        print(f"[content-intel] Analysis failed: {e}")
    finally:
        db.close()


@router.post("/analyze", status_code=202)
def analyze_content(
    req: AnalyzeRequest,
    background_tasks: BackgroundTasks,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    # Resolve handle: use provided override or stored handle
    handle = req.handle
    if not handle:
        if req.platform == "instagram":
            handle = decrypt_handle(getattr(coach, "instagram_handle", None))
        elif req.platform == "tiktok":
            handle = decrypt_handle(getattr(coach, "tiktok_handle", None))
        elif req.platform == "twitter":
            handle = decrypt_handle(getattr(coach, "twitter_handle", None))
        elif req.platform == "youtube":
            handle = coach.linkedin_url  # repurpose for YouTube channel handle

    if not handle:
        raise HTTPException(400, f"No {req.platform} handle configured. Set it in Settings or provide a handle.")

    handle = handle.lstrip("@")
    background_tasks.add_task(_run_analysis, coach.id, req.platform, handle)
    return {"ok": True, "message": f"Analyse démarrée pour @{handle} sur {req.platform}. Résultats dans 30-60 secondes."}


@router.get("")
def get_analysis(
    platform: str = "instagram",
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    analysis = db.query(models.ContentAnalysis).filter(
        models.ContentAnalysis.coach_id == coach.id,
        models.ContentAnalysis.platform == platform,
    ).order_by(models.ContentAnalysis.analyzed_at.desc()).first()

    if not analysis:
        return {"analysis": None, "handle": None, "analyzed_at": None}

    return {
        "analysis": json.loads(analysis.analysis_data),
        "handle": analysis.handle,
        "platform": analysis.platform,
        "analyzed_at": analysis.analyzed_at.isoformat(),
    }


@router.get("/all")
def get_all_analyses(
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    analyses = db.query(models.ContentAnalysis).filter(
        models.ContentAnalysis.coach_id == coach.id,
    ).order_by(models.ContentAnalysis.analyzed_at.desc()).all()

    return [
        {
            "id": a.id,
            "platform": a.platform,
            "handle": a.handle,
            "analyzed_at": a.analyzed_at.isoformat(),
            "content_score": json.loads(a.analysis_data).get("content_score", 0),
        }
        for a in analyses
    ]
