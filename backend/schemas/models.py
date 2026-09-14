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
    # True when the candidate must answer personally -- legal status, protected
    # characteristics, anything a guess would misrepresent. See llm_client.
    needs_review: bool = False


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
    # Send the tailored resume text and the backend renders a real PDF from it, or
    # send an existing PDF as base64. At least one is required.
    resume_text: Optional[str] = ""
    resume_pdf_base64: Optional[str] = ""
    cover_letter: Optional[str] = ""
    profile: UserProfile
    screening_answers: Optional[list[QAItem]] = []
    company: Optional[str] = ""
    role: Optional[str] = ""


class ApplyPreviewResponse(BaseModel):
    status: str
    screenshot_base64: str
    fields_filled: list[str]
    # Left blank on purpose: legal or personal-status questions, required fields
    # with no data, and answers that did not match an option. The candidate fills
    # these in the browser window before confirming.
    needs_input: list[str] = []
    session_id: str


class ApplyConfirmRequest(BaseModel):
    session_id: str


class ApplyConfirmResponse(BaseModel):
    # "submitted": the page confirmed it, and it was logged to the tracker.
    # "failed": the page showed errors; the session stays open to fix and retry.
    # "unconfirmed": no confirmation or error appeared; not logged, check the site.
    status: str
    message: str
    session_open: bool = False
