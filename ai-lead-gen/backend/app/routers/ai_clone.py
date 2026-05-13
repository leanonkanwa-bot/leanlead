"""
AI Clone — conversational qualifier bot.

POST /api/ai-clone/{lead_id}/start        – start a new conversation (or resume existing)
POST /api/ai-clone/{lead_id}/message      – send a lead message, get AI reply
GET  /api/ai-clone/{lead_id}              – get conversation state
POST /api/ai-clone/{lead_id}/hand-off     – mark as handed off to coach
"""
import json
import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_coach
from ..database import get_db
from .. import models

router = APIRouter(prefix="/api/ai-clone", tags=["ai-clone"])

HOT_LEAD_THRESHOLD = 80

QUALIFYING_QUESTIONS = [
    "C'est quoi ton plus grand défi en ce moment avec {niche} ?",
    "Depuis combien de temps tu cherches une solution à ce problème ?",
    "Qu'est-ce que tu as déjà essayé pour résoudre ça ?",
    "Si tu réglais ce problème, ça changerait quoi concrètement pour toi ?",
    "Tu as un budget défini pour investir dans une solution ?",
]


def _get_client():
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None
    try:
        import anthropic
        return anthropic.Anthropic(api_key=api_key)
    except Exception:
        return None


def _ai_reply(
    coach_niche: str,
    coach_offer: str,
    coach_name: str,
    icp_pain_points: list,
    conversation_history: list,
    lead_name: str,
    lead_bio: str,
) -> tuple[str, float]:
    """
    Returns (reply_text, new_score).
    Falls back to template responses if no API key.
    """
    client = _get_client()

    if not client:
        # Dev fallback
        turn_count = len([m for m in conversation_history if m["role"] == "user"])
        if turn_count <= 1:
            return (
                f"Merci d'avoir répondu ! Pour mieux comprendre ta situation, "
                f"dis-moi : c'est quoi ton plus grand défi en ce moment avec {coach_niche} ?",
                20.0,
            )
        elif turn_count <= 2:
            return (
                "Je comprends ! Depuis combien de temps tu cherches une solution à ça ?",
                40.0,
            )
        elif turn_count <= 3:
            return (
                f"C'est exactement le type de situation que {coach_name} aide à résoudre. "
                "Qu'est-ce que tu as déjà essayé pour t'en sortir ?",
                55.0,
            )
        else:
            return (
                f"Tu sembles vraiment motivé(e) à changer les choses. "
                f"On a quelques places disponibles pour un appel découverte gratuit avec {coach_name}. "
                "Est-ce que ça t'intéresserait ?",
                85.0,
            )

    # Build pain points context
    pain_ctx = ""
    if icp_pain_points:
        pain_ctx = "\nPain points typiques de l'ICP:\n" + "\n".join(f"- {p}" for p in icp_pain_points[:5])

    # Format conversation for Claude
    messages_for_claude = []
    for msg in conversation_history:
        messages_for_claude.append({
            "role": msg["role"],
            "content": msg["content"],
        })

    system = f"""Tu es l'assistant IA de {coach_name}, un(e) coach spécialisé(e) en {coach_niche}.

Transformation proposée: {coach_offer}
{pain_ctx}

Tu qualifies des prospects qui ont répondu à un DM. Ton rôle:
1. Parler EXACTEMENT comme {coach_name} parlerait (chaleureux, direct, sans jargon)
2. Poser UNE seule question qualifiante à la fois
3. Évaluer le score de qualification (0-100) selon:
   - Exprime une vraie douleur (0-40 pts)
   - A déjà cherché des solutions (0-20 pts)
   - Budget ou intention d'investir (0-20 pts)
   - Timing urgent (0-20 pts)
4. Quand score ≥ {HOT_LEAD_THRESHOLD}: proposer un appel découverte

Prospect: {lead_name}
Contexte: {lead_bio[:300] if lead_bio else 'Inconnu'}

IMPORTANT: Réponds UNIQUEMENT avec du JSON:
{{"reply": "...", "score": 0-100, "reasoning": "..."}}
Pas de markdown, pas de texte hors JSON."""

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            system=system,
            messages=messages_for_claude,
        )
        text = response.content[0].text.strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        data = json.loads(text[start:end])
        return data.get("reply", ""), float(data.get("score", 0))
    except Exception as e:
        print(f"[ai-clone] Error: {e}")
        return (
            f"Merci pour ta réponse ! Pour mieux t'aider, peux-tu me dire depuis combien de temps tu es confronté(e) à ça ?",
            30.0,
        )


def _serialize_conv(conv: models.AIConversation) -> dict:
    return {
        "id": conv.id,
        "lead_id": conv.lead_id,
        "coach_id": conv.coach_id,
        "messages": json.loads(conv.messages or "[]"),
        "current_score": conv.current_score,
        "status": conv.status,
        "created_at": conv.created_at.isoformat() if conv.created_at else None,
        "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
    }


@router.get("/{lead_id}")
def get_conversation(
    lead_id: int,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    lead = db.query(models.Lead).filter(
        models.Lead.id == lead_id,
        models.Lead.coach_id == coach.id,
    ).first()
    if not lead:
        raise HTTPException(404, "Lead not found")

    conv = db.query(models.AIConversation).filter(
        models.AIConversation.lead_id == lead_id,
        models.AIConversation.coach_id == coach.id,
    ).order_by(models.AIConversation.created_at.desc()).first()

    return {"conversation": _serialize_conv(conv) if conv else None}


@router.post("/{lead_id}/start")
def start_conversation(
    lead_id: int,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    """Start or return existing active conversation for a lead."""
    lead = db.query(models.Lead).filter(
        models.Lead.id == lead_id,
        models.Lead.coach_id == coach.id,
    ).first()
    if not lead:
        raise HTTPException(404, "Lead not found")

    existing = db.query(models.AIConversation).filter(
        models.AIConversation.lead_id == lead_id,
        models.AIConversation.coach_id == coach.id,
        models.AIConversation.status == "active",
    ).first()
    if existing:
        return {"conversation": _serialize_conv(existing), "created": False}

    # Generate opening message from AI
    niche = coach.niche or "coaching"
    icp_pains = json.loads(coach.icp_pain_points or "[]")

    opening = (
        f"Salut {lead.name or 'toi'} ! Super content(e) que tu aies répondu 😊 "
        f"Pour que je puisse vraiment t'aider, j'aurais quelques questions rapides. "
        f"C'est quoi ton plus grand défi en ce moment avec {niche} ?"
    )

    messages = [{"role": "assistant", "content": opening, "ts": datetime.utcnow().isoformat()}]

    conv = models.AIConversation(
        lead_id=lead_id,
        coach_id=coach.id,
        messages=json.dumps(messages),
        current_score=0.0,
        status="active",
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return {"conversation": _serialize_conv(conv), "created": True}


class MessageIn(BaseModel):
    content: str


@router.post("/{lead_id}/message")
def send_message(
    lead_id: int,
    req: MessageIn,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    """Process a lead's reply and generate AI clone response."""
    lead = db.query(models.Lead).filter(
        models.Lead.id == lead_id,
        models.Lead.coach_id == coach.id,
    ).first()
    if not lead:
        raise HTTPException(404, "Lead not found")

    conv = db.query(models.AIConversation).filter(
        models.AIConversation.lead_id == lead_id,
        models.AIConversation.coach_id == coach.id,
        models.AIConversation.status == "active",
    ).first()
    if not conv:
        raise HTTPException(400, "No active conversation. Call /start first.")

    messages = json.loads(conv.messages or "[]")

    # Add lead message
    messages.append({
        "role": "user",
        "content": req.content,
        "ts": datetime.utcnow().isoformat(),
    })

    # Get AI reply
    icp_pains = json.loads(coach.icp_pain_points or "[]")
    reply_text, new_score = _ai_reply(
        coach_niche=coach.niche or "coaching",
        coach_offer=coach.offer_description or "",
        coach_name=coach.name,
        icp_pain_points=icp_pains,
        conversation_history=[{"role": m["role"], "content": m["content"]} for m in messages],
        lead_name=lead.name or "",
        lead_bio=lead.bio or "",
    )

    # Add AI reply
    messages.append({
        "role": "assistant",
        "content": reply_text,
        "ts": datetime.utcnow().isoformat(),
    })

    # Update conversation
    conv.messages = json.dumps(messages)
    conv.current_score = new_score
    conv.updated_at = datetime.utcnow()

    # Auto-escalate if hot lead
    if new_score >= HOT_LEAD_THRESHOLD and conv.status == "active":
        conv.status = "hot"
        # Update lead score
        lead.qualification_score = max(lead.qualification_score or 0, new_score)

    db.commit()

    return {
        "reply": reply_text,
        "score": new_score,
        "status": conv.status,
        "is_hot": conv.status == "hot",
        "conversation": _serialize_conv(conv),
    }


@router.post("/{lead_id}/hand-off")
def hand_off(
    lead_id: int,
    coach: models.Coach = Depends(get_current_coach),
    db: Session = Depends(get_db),
):
    conv = db.query(models.AIConversation).filter(
        models.AIConversation.lead_id == lead_id,
        models.AIConversation.coach_id == coach.id,
    ).order_by(models.AIConversation.created_at.desc()).first()
    if not conv:
        raise HTTPException(404, "No conversation found")
    conv.status = "handed_off"
    db.commit()
    return {"ok": True, "status": "handed_off"}
