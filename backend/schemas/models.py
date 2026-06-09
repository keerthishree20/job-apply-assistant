from pydantic import BaseModel
from typing import Optional


class ScrapeRequest(BaseModel):
    url: str


class ScrapeResponse(BaseModel):
    job_title: str
    company: str
    job_description: str
    source: str


class ScrapeError(BaseModel):
    error: str
    message: str


class GenerateRequest(BaseModel):
    base_resume: str
    job_description: str
    job_title: Optional[str] = ""
    company: Optional[str] = ""
    generate_cover_letter: bool = True


class DiffChange(BaseModel):
    type: str
    phrase: Optional[str] = None
    original: Optional[str] = None
    new: Optional[str] = None


class GenerateResponse(BaseModel):
    tailored_resume: str
    cover_letter: str
    keywords_added: list[str]
    diff: list[DiffChange]


class QAItem(BaseModel):
    question: str
    answer: str


class AnswersRequest(BaseModel):
    job_description: str
    job_title: Optional[str] = ""
    company: Optional[str] = ""
    tailored_resume: str
    questions: list[str]


class AnswersResponse(BaseModel):
    answers: list[QAItem]


class UserProfile(BaseModel):
    name: str
    email: str
    phone: str
    linkedin_url: Optional[str] = ""
    github_url: Optional[str] = ""
    portfolio_url: Optional[str] = ""
    college: Optional[str] = ""
    graduation_year: Optional[str] = ""


class ApplyRequest(BaseModel):
    job_url: str
    resume_pdf_base64: str
    profile: UserProfile
    screening_answers: Optional[list[QAItem]] = []


class ApplyPreviewResponse(BaseModel):
    status: str
    screenshot_base64: str
    fields_filled: list[str]
    session_id: str


class ApplyConfirmRequest(BaseModel):
    session_id: str


class ApplyConfirmResponse(BaseModel):
    status: str
    message: str
