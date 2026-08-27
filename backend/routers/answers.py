from fastapi import APIRouter
from schemas.models import AnswersRequest, AnswersResponse, QAItem
from services.llm_client import answer_screening_questions

router = APIRouter()


@router.post("/api/answers", response_model=AnswersResponse)
async def answers(req: AnswersRequest):
    result = await answer_screening_questions(
        tailored_resume=req.tailored_resume,
        job_title=req.job_title,
        company=req.company,
        questions=req.questions,
    )
    return AnswersResponse(answers=[QAItem(**a) for a in result])
