import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from agents.qualifier_agent import qualify_lead
from agents.writer_agent import write_dm_sequence
from agents.reply_agent import handle_reply
from agents.crm_agent import (
    create_lead,
    update_stage,
    get_pipeline_stats,
    sync_qualified_lead,
    sync_reply_event,
    send_daily_summary,
)

app = FastAPI(title="AI Lead Gen Agent")


# ── Models ────────────────────────────────────────────────────────────────────

class ProfileURL(BaseModel):
    url: str
    auto_write_dm: bool = True


class ReplyInput(BaseModel):
    incoming_message: str
    conversation_history: list
    exchange_count: int
    record_id: str


class WebhookEvent(BaseModel):
    event_type: str          # "new_lead" | "new_dm" | "daily_summary"
    profile_url: Optional[str] = None
    record_id: Optional[str] = None
    message: Optional[str] = None
    conversation_history: list = []
    exchange_count: int = 1
    metadata: dict = {}


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/qualify")
def qualify(data: ProfileURL):
    lead = qualify_lead(data.url)

    if not lead["icp_match"]:
        return {"lead": lead, "sequence": None, "message": "Lead non qualifié (score < 70)"}

    sequence = write_dm_sequence(lead) if data.auto_write_dm else None

    try:
        if sequence:
            record = sync_qualified_lead(lead, sequence)
        else:
            record = create_lead(lead)
        airtable_id = record.get("id")
    except Exception as exc:
        print(f"[CRM] Airtable sync failed: {exc}")
        airtable_id = None

    return {"lead": lead, "sequence": sequence, "airtable_record_id": airtable_id}


@app.post("/reply")
def reply(data: ReplyInput):
    result = handle_reply(data.incoming_message, data.conversation_history, data.exchange_count)

    try:
        sync_reply_event(data.record_id, result, data.exchange_count)
    except Exception as exc:
        print(f"[CRM] Airtable reply sync failed: {exc}")

    return result


@app.get("/pipeline")
def pipeline():
    return get_pipeline_stats()


@app.post("/webhook")
def webhook(body: WebhookEvent, background_tasks: BackgroundTasks):
    event = body.event_type

    if event == "new_lead" and body.profile_url:
        background_tasks.add_task(_process_new_lead, body.profile_url)
        return {"accepted": True, "event": event}

    if event == "new_dm" and body.record_id and body.message:
        background_tasks.add_task(
            _process_incoming_dm,
            body.record_id,
            body.message,
            body.conversation_history,
            body.exchange_count,
        )
        return {"accepted": True, "event": event}

    if event == "daily_summary":
        background_tasks.add_task(send_daily_summary)
        return {"accepted": True, "event": event}

    raise HTTPException(status_code=400, detail=f"Événement inconnu ou incomplet : '{event}'")


# ── Background tasks ──────────────────────────────────────────────────────────

def _process_new_lead(profile_url: str):
    try:
        lead = qualify_lead(profile_url)
        if lead["icp_match"]:
            sequence = write_dm_sequence(lead)
            sync_qualified_lead(lead, sequence)
    except Exception as exc:
        print(f"[webhook/new_lead] Error: {exc}")


def _process_incoming_dm(record_id: str, message: str, history: list, exchange_count: int):
    try:
        result = handle_reply(message, history, exchange_count)
        sync_reply_event(record_id, result, exchange_count)
    except Exception as exc:
        print(f"[webhook/new_dm] Error: {exc}")
