import asyncio
import json
import os
import re
from groq import AsyncGroq, APIStatusError, NotFoundError

# Groq retires models on a rolling basis -- llama-3.3-70b-versatile was the
# original choice here and has since been decommissioned, which surfaced as a
# 404 on every generate call. Keep it overridable so the next retirement is an
# .env change rather than a code change.
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")


class LLMUnavailable(RuntimeError):
    """Raised when the model cannot be reached, with a message worth showing."""


# Built lazily so importing this module doesn't require the key to be set --
# `main.py` calls load_dotenv() before importing routers, but that ordering
# shouldn't be load-bearing.
_client: AsyncGroq | None = None


def _get_client() -> AsyncGroq:
    global _client
    if _client is None:
        key = os.getenv("GROQ_API_KEY")
        if not key:
            raise LLMUnavailable(
                "No GROQ_API_KEY set. Copy backend/.env.example to backend/.env "
                "and add a key from https://console.groq.com/keys"
            )
        _client = AsyncGroq(api_key=key)
    return _client


async def _ask(system: str, user: str) -> str:
    try:
        response = await _get_client().chat.completions.create(
            model=MODEL,
            max_tokens=4096,
            temperature=0.4,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
        )
    except NotFoundError as exc:
        raise LLMUnavailable(
            f"Groq has no model named {MODEL!r} on this account -- it was most "
            f"likely retired. Set GROQ_MODEL in backend/.env to a current one; "
            f"https://console.groq.com/docs/models lists what is available."
        ) from exc
    except APIStatusError as exc:
        raise LLMUnavailable(f"Groq returned {exc.status_code}: {exc.message}") from exc

    return response.choices[0].message.content


RESUME_SYSTEM = """You are a senior technical recruiter and resume expert at a top tech company. Your job is to transform a candidate's resume into a highly targeted, ATS-optimized resume for a specific job.

RULES (follow strictly):
1. NEVER invent skills, experience, projects, or achievements not in the original resume
2. Keep ALL dates, company names, college names, and GPA exactly as-is
3. Rewrite every bullet point using strong action verbs (Built, Developed, Designed, Implemented, Optimized, Led, Automated, Reduced, Increased)
4. Mirror the exact keywords and phrases from the job description naturally into the resume
5. Reorder sections and bullets to put the most relevant experience FIRST
6. Rewrite the Professional Summary/Objective to directly address the job title and company
7. Quantify achievements wherever possible (e.g., "reduced load time by 40%", "built REST API serving 1000+ requests")
8. Use strong, specific language — remove weak phrases like "helped with", "assisted in", "worked on"
9. Output length must be within ±15% of original

OUTPUT FORMAT:
- Return ONLY the complete tailored resume as plain text
- No markdown, no code fences, no commentary
- After the resume, on a NEW LINE write exactly:
CHANGES_JSON: [{"type":"added","phrase":"exact keyword or phrase added"}]"""

COVER_LETTER_SYSTEM = """You are an expert career coach who writes cover letters that get interviews. Write a cover letter that is professional, specific, and compelling.

STRICT RULES:
- Maximum 220 words
- NEVER use: "I am excited to apply", "I am writing to express my interest", "To whom it may concern", "I believe I would be a great fit"
- DO NOT start with "I" — start with a strong hook about the company or role
- Be specific: mention the company name, role title, and 1-2 specific skills from the JD
- Reference actual projects/skills from the resume — be concrete, not vague
- Sound like a confident professional, not a desperate student
- End with a clear, short call to action

STRUCTURE:
Para 1 (2-3 sentences): Hook — what draws you to THIS company + role specifically, show you know what they do
Para 2 (3-4 sentences): What you bring — cite 2 specific projects or skills from resume that directly match the JD
Para 3 (1-2 sentences): Brief, confident closing with call to action

Return ONLY the cover letter text. No subject line, no "Dear Hiring Manager", just the body paragraphs."""

QA_SYSTEM = """You are helping a CS student fill out job application screening questions. Answer honestly and professionally based only on their resume.

RULES:
- 1-2 sentences max per answer — short and direct
- Sound like a real person, not a robot
- Use first person
- For "notice period" / "when can you start" / "availability" → "I am immediately available"
- For "years of experience" → count months/years from the first relevant project or internship listed
- For "expected salary" / "CTC" / "package" → "I am flexible and open to discussion based on the role"
- For "why this company" → give a specific, honest 1-2 sentence answer based on the company name
- For "relocate" → "Yes, I am open to relocation"
- NEVER fabricate certifications, awards, or experience
- NEVER assert a legal or protected-characteristic fact that is not stated in
  the resume — work authorisation, visa or sponsorship status, citizenship,
  age, disability, veteran status, criminal record, security clearance,
  driving licence. Getting one of these wrong is a misrepresentation on a job
  application, not a rough draft. For any such question answer exactly:
  NEEDS_CANDIDATE_INPUT

Answer ONLY in this format (no extra text):
1. [answer]
2. [answer]
3. [answer]"""


async def generate_resume_and_cover_letter(
    base_resume: str,
    job_description: str,
    job_title: str,
    company: str,
) -> dict:
    resume_user = (
        f"TARGET JOB: {job_title} at {company}\n\n"
        f"JOB DESCRIPTION:\n{job_description}\n\n"
        f"{'='*60}\n\n"
        f"CANDIDATE'S ORIGINAL RESUME:\n{base_resume}"
    )
    cover_user = (
        f"Candidate Resume:\n{base_resume}\n\n"
        f"{'='*60}\n\n"
        f"Job Title: {job_title}\n"
        f"Company: {company}\n\n"
        f"Key Job Requirements:\n{job_description[:800]}"
    )

    raw_resume, cover_letter = await asyncio.gather(
        _ask(RESUME_SYSTEM, resume_user),
        _ask(COVER_LETTER_SYSTEM, cover_user),
    )

    changes = []
    if "CHANGES_JSON:" in raw_resume:
        parts = raw_resume.split("CHANGES_JSON:", 1)
        resume_text = parts[0].strip()
        try:
            changes = json.loads(parts[1].strip())
        except json.JSONDecodeError:
            changes = []
    else:
        resume_text = raw_resume.strip()

    keywords_added = [c["phrase"] for c in changes if c.get("type") == "added" and c.get("phrase")]

    return {
        "tailored_resume": resume_text,
        "cover_letter": cover_letter.strip(),
        "keywords_added": keywords_added,
        "diff": changes,
    }


# Questions whose answer is a legal fact about the candidate. A wrong answer
# here is a misrepresentation on a job application, so these are never left to
# the model -- the prompt asks it to defer, and this catches the cases where it
# doesn't. Matched against the question, not the answer.
#
# Matched as a flat keyword list rather than as phrases, because word order
# varies more than it looks: "work authorisation", "authorised to work" and
# "right to work" are the same question. Over-flagging costs the candidate a
# few seconds; under-flagging puts a false legal claim on an application, so
# this errs deliberately toward flagging.
ELIGIBILITY_PATTERN = re.compile(
    r"\b("
    # work eligibility and immigration status
    r"authoris\w*|authoriz\w*|sponsorship|sponsor|visa|citizen\w*|nationality"
    r"|passport|immigration|residen\w*|permanent\s+resident|green\s+card"
    r"|right\s+to\s+work|eligible\s+to\s+work|legally\s+\w+\s+to\s+work"
    r"|work\s+permit"
    # protected characteristics
    r"|disab\w*|veteran|gender|ethnic\w*|\brace\b|religion|marital|pregnan\w*"
    r"|sexual\s+orientation|date\s+of\s+birth|how\s+old\s+are|\bage\b"
    # background and clearance
    r"|criminal|conviction|convicted|felony|background\s+check"
    r"|security\s+clearance|drug\s+test"
    # licences
    r"|driv\w*\s+licen[cs]e|licen[cs]e\s+to\s+driv\w*"
    r")\b",
    re.IGNORECASE,
)

NEEDS_INPUT = "NEEDS_CANDIDATE_INPUT"
NEEDS_INPUT_TEXT = (
    "You need to answer this one yourself — it is a legal or personal-status "
    "question, and a guessed answer would be a misrepresentation."
)


def _finalise(question: str, answer: str) -> dict:
    """Flag anything the candidate must answer personally."""
    needs_review = bool(ELIGIBILITY_PATTERN.search(question)) or NEEDS_INPUT in answer
    return {
        "question": question,
        "answer": NEEDS_INPUT_TEXT if needs_review else answer,
        "needs_review": needs_review,
    }


async def answer_screening_questions(
    tailored_resume: str,
    job_title: str,
    company: str,
    questions: list[str],
) -> list[dict]:
    questions_text = "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))
    user = (
        f"Candidate Resume:\n{tailored_resume}\n\n"
        f"Applying for: {job_title} at {company}\n\n"
        f"Screening Questions:\n{questions_text}"
    )
    raw = await _ask(QA_SYSTEM, user)
    answers = []
    lines = re.split(r'\n(?=\d+\.)', raw.strip())
    for i, line in enumerate(lines):
        answer_text = re.sub(r'^\d+\.\s*', '', line).strip()
        if i < len(questions):
            answers.append(_finalise(questions[i], answer_text))
    if len(answers) != len(questions):
        # The numbered format didn't parse. Hand back the raw reply rather than
        # mis-pairing answers to questions, and flag every one for review.
        answers = [
            {"question": q, "answer": raw, "needs_review": True} for q in questions
        ]
    return answers
