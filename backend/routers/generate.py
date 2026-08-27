import asyncio
from fastapi import APIRouter
from schemas.models import GenerateRequest, GenerateResponse
from services.llm_client import generate_resume_and_cover_letter

router = APIRouter()


@router.post("/api/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    result = await generate_resume_and_cover_letter(
        base_resume=req.base_resume,
        job_description=req.job_description,
        job_title=req.job_title,
        company=req.company,
    )
    return GenerateResponse(**result)
