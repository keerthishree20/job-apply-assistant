import asyncio
import base64
import binascii
import os
import time
import uuid
from dataclasses import dataclass

from fastapi import APIRouter, HTTPException
from schemas.models import (
    ApplyRequest, ApplyPreviewResponse,
    ApplyConfirmRequest, ApplyConfirmResponse,
)
from services.scraper import detect_site
from services.linkedin_bot import LinkedInBot
from services.ats_bot import ATSBot
from services.excel_tracker import append_application
from services.resume_pdf import render_resume_pdf

router = APIRouter()


@dataclass
class _Session:
    bot: object
    created: float
    company: str
    role: str
    resume_snippet: str
    busy: bool = False


# session_id -> an open browser between preview and confirm. Each one holds a
# Chromium process, so sessions expire and their browsers are closed.
_sessions: dict[str, _Session] = {}


def _ttl() -> float:
    return float(os.getenv("APPLY_SESSION_TTL", "900"))


async def _expire_sessions() -> None:
    cutoff = time.monotonic() - _ttl()
    for sid in [s for s, sess in _sessions.items() if sess.created < cutoff and not sess.busy]:
        sess = _sessions.pop(sid)
        try:
            await sess.bot.close()
        except Exception:
            pass


def _get_bot(job_url: str):
    site, _ = detect_site(job_url)
    if "linkedin.com" in job_url:
        return LinkedInBot()
    return ATSBot(ats_type=site)


async def _resume_bytes(req: ApplyRequest) -> bytes:
    if req.resume_pdf_base64:
        try:
            data = base64.b64decode(req.resume_pdf_base64, validate=True)
        except (binascii.Error, ValueError):
            raise HTTPException(status_code=400, detail="resume_pdf_base64 is not valid base64.")
        if not data.startswith(b"%PDF"):
            raise HTTPException(status_code=400, detail="resume_pdf_base64 does not contain a PDF.")
        return data
    if req.resume_text and req.resume_text.strip():
        return await render_resume_pdf(req.resume_text)
    raise HTTPException(status_code=400, detail="Send resume_text or resume_pdf_base64.")


@router.post("/api/apply", response_model=ApplyPreviewResponse)
async def apply_preview(req: ApplyRequest):
    await _expire_sessions()
    pdf = await _resume_bytes(req)
    bot = _get_bot(req.job_url)
    try:
        preview = await bot.fill_form(
            job_url=req.job_url,
            resume_pdf=pdf,
            profile=req.profile.model_dump(),
            screening_answers=[a.model_dump() for a in (req.screening_answers or [])],
            cover_letter=req.cover_letter or "",
        )
    except Exception as exc:
        await bot.close()
        raise HTTPException(status_code=500, detail=str(exc))

    session_id = str(uuid.uuid4())
    _sessions[session_id] = _Session(
        bot=bot,
        created=time.monotonic(),
        company=req.company or "",
        role=req.role or "",
        resume_snippet=(req.resume_text or "")[:120],
    )

    return ApplyPreviewResponse(
        status="preview_ready",
        screenshot_base64=base64.b64encode(preview["screenshot"]).decode(),
        fields_filled=preview["fields_filled"],
        needs_input=preview["needs_input"],
        session_id=session_id,
    )


@router.post("/api/apply/confirm", response_model=ApplyConfirmResponse)
async def apply_confirm(req: ApplyConfirmRequest):
    await _expire_sessions()
    sess = _sessions.get(req.session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail="Session not found, expired, or already used.")
    if sess.busy:
        raise HTTPException(status_code=409, detail="This application is already being submitted.")
    sess.busy = True
    try:
        result = await sess.bot.submit()
    except Exception as exc:
        result = {"status": "unconfirmed", "detail": f"Submit raised an error: {exc}"}
    finally:
        sess.busy = False

    status = result["status"]
    if status == "failed":
        # Nothing was accepted, so a retry cannot double-submit. Keep the browser
        # open for the candidate to fix the listed fields.
        sess.created = time.monotonic()
        return ApplyConfirmResponse(
            status="failed",
            message=f"The form was not accepted: {result['detail']}. Fix it in the browser window, then confirm again.",
            session_open=True,
        )

    _sessions.pop(req.session_id, None)
    try:
        if status == "submitted":
            meta = sess.bot.meta
            append_application(
                company=sess.company,
                role=sess.role,
                url=meta.get("url", ""),
                cover_letter=meta.get("cover_letter", False),
                resume_snippet=sess.resume_snippet,
                notes=f"Confirmed by page: {result['detail']}"[:200],
            )
            return ApplyConfirmResponse(status="submitted", message="Application submitted and confirmed by the site.")
        # Unconfirmed: a retry could submit twice, so the session ends and nothing is logged.
        return ApplyConfirmResponse(
            status="unconfirmed",
            message=f"{result['detail']} It may or may not have gone through; check the site or your email. Not added to the tracker.",
        )
    finally:
        await sess.bot.close()


@router.post("/api/apply/cancel")
async def apply_cancel(req: ApplyConfirmRequest):
    sess = _sessions.pop(req.session_id, None)
    if sess is not None:
        await sess.bot.close()
    return {"status": "cancelled"}


async def close_all_sessions() -> None:
    sessions = list(_sessions.values())
    _sessions.clear()
    await asyncio.gather(*(s.bot.close() for s in sessions), return_exceptions=True)
