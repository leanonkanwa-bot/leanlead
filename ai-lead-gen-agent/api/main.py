"""FastAPI entry point — exposes the 4-agent pipeline as REST endpoints."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from agents.qualifier_agent import qualify_lead
from agents.writer_agent import write_dm_sequence
from agents.reply_agent import handle_reply
from agents import crm_agent


# ── Request / Response models ─────────────────────────────────────────────────

class QualifyRequest(BaseModel):
    profile_url: str
    auto_write_dm: bool = True


class QualifyResponse(BaseModel):
    profile_url: str
    platform: str
    username: str
    score: int
    niche: str
    icp_match: bool
    reason: str
    passed_threshold: bool
    dm_sequence: Optional[dict] = None
    airtable_record_id: Optional[str] = None


class ReplyRequest(BaseModel):
    record_id: str
    incoming_message: str
    conversation_history: list[dict] = []
    exchange_count: int = 1


class ReplyResponse(BaseModel):
    reply: str
    classification: str
    inject_calendly: bool
    flag_human: bool
    airtable_updated: bool


class WebhookEvent(BaseModel):
    event_type: str
    profile_url: Optional[str] = None
    record_id: Optional[str] = None
    message: Optional[str] = None
    conversation_history: list[dict] = []
    exchange_count: int = 1
    metadata: dict = {}


# ── App ───────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="AI Lead Gen — Francophone Coaches",
    description="Système multi-agents de prospection automatique pour coachs francophones.",
    version="1.0.0",
    lifespan=lifespan,
)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/qualify", response_model=QualifyResponse)
async def qualify_endpoint(body: QualifyRequest):
    try:
        result = await asyncio.to_thread(qualify_lead, body.profile_url)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Qualification failed: {exc}")

    dm_sequence = None
    airtable_record_id = None

    if result["passed_threshold"]:
        if body.auto_write_dm:
            try:
                dm_sequence = await asyncio.to_thread(write_dm_sequence, result)
            except Exception as exc:
                raise HTTPException(status_code=502, detail=f"DM writing failed: {exc}")

        if dm_sequence:
            try:
                record = await asyncio.to_thread(crm_agent.sync_qualified_lead, result, dm_sequence)
                airtable_record_id = record.get("id")
            except Exception as exc:
                print(f"[CRM] Airtable sync failed: {exc}")

    return QualifyResponse(
        profile_url=result["url"],
        platform=result["platform"],
        username=result["username"],
        score=result["score"],
        niche=result["niche"],
        icp_match=result["icp_match"],
        reason=result["reason"],
        passed_threshold=result["passed_threshold"],
        dm_sequence=dm_sequence,
        airtable_record_id=airtable_record_id,
    )


@app.post("/reply", response_model=ReplyResponse)
async def reply_endpoint(body: ReplyRequest):
    try:
        result = await asyncio.to_thread(
            handle_reply,
            body.incoming_message,
            body.conversation_history,
            body.exchange_count,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Reply generation failed: {exc}")

    airtable_updated = False
    try:
        await asyncio.to_thread(crm_agent.sync_reply_event, body.record_id, result, body.exchange_count)
        airtable_updated = True
    except Exception as exc:
        print(f"[CRM] Airtable reply sync failed: {exc}")

    return ReplyResponse(
        reply=result["reply"],
        classification=result["classification"],
        inject_calendly=result["inject_calendly"],
        flag_human=result["flag_human"],
        airtable_updated=airtable_updated,
    )


@app.get("/pipeline")
async def pipeline_endpoint():
    try:
        stats = await asyncio.to_thread(crm_agent.get_pipeline)
        return JSONResponse(content=stats)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Airtable fetch failed: {exc}")


@app.post("/webhook")
async def webhook_endpoint(body: WebhookEvent, background_tasks: BackgroundTasks):
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
        background_tasks.add_task(crm_agent.send_daily_summary)
        return {"accepted": True, "event": event}

    raise HTTPException(
        status_code=400,
        detail=f"Unknown or incomplete event_type '{event}'.",
    )


# ── Background task helpers ───────────────────────────────────────────────────

async def _process_new_lead(profile_url: str):
    try:
        result = await asyncio.to_thread(qualify_lead, profile_url)
        if result["passed_threshold"]:
            dm_sequence = await asyncio.to_thread(write_dm_sequence, result)
            await asyncio.to_thread(crm_agent.sync_qualified_lead, result, dm_sequence)
    except Exception as exc:
        print(f"[webhook/_process_new_lead] Error: {exc}")


async def _process_incoming_dm(
    record_id: str,
    message: str,
    history: list[dict],
    exchange_count: int,
):
    try:
        result = await asyncio.to_thread(handle_reply, message, history, exchange_count)
        await asyncio.to_thread(crm_agent.sync_reply_event, record_id, result, exchange_count)
    except Exception as exc:
        print(f"[webhook/_process_incoming_dm] Error: {exc}")
