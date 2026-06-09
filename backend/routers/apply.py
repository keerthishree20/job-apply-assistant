import uuid
from fastapi import APIRouter, HTTPException
from schemas.models import (
    ApplyRequest, ApplyPreviewResponse,
    ApplyConfirmRequest, ApplyConfirmResponse,
)
from services.scraper import detect_site
from services.linkedin_bot import LinkedInBot
from services.ats_bot import ATSBot
from services.excel_tracker import append_application

router = APIRouter()

# In-memory session store: session_id → bot instance kept alive between preview and confirm
_sessions: dict[str, object] = {}


def _get_bot(job_url: str):
    site, _ = detect_site(job_url)
    if "linkedin.com" in job_url:
        return LinkedInBot()
    return ATSBot(ats_type=site)


@router.post("/api/apply", response_model=ApplyPreviewResponse)
async def apply_preview(req: ApplyRequest):
    bot = _get_bot(req.job_url)
    try:
        preview = await bot.fill_form(
            job_url=req.job_url,
            resume_pdf_base64=req.resume_pdf_base64,
            profile=req.profile.model_dump(),
            screening_answers=[a.model_dump() for a in (req.screening_answers or [])],
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    session_id = str(uuid.uuid4())
    _sessions[session_id] = bot

    return ApplyPreviewResponse(
        status="preview_ready",
        screenshot_base64=preview["screenshot_base64"],
        fields_filled=preview["fields_filled"],
        session_id=session_id,
    )


@router.post("/api/apply/confirm", response_model=ApplyConfirmResponse)
async def apply_confirm(req: ApplyConfirmRequest):
    bot = _sessions.pop(req.session_id, None)
    if bot is None:
        raise HTTPException(status_code=404, detail="Session not found or already used.")
    try:
        result = await bot.submit()
        append_application(
            company=result.get("company", ""),
            role=result.get("role", ""),
            url=result.get("url", ""),
            cover_letter=result.get("cover_letter", False),
            resume_snippet=result.get("resume_snippet", ""),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        await bot.close()

    return ApplyConfirmResponse(status="submitted", message="Application submitted successfully!")
