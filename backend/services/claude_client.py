import asyncio
import json
import os
import re
import google.generativeai as genai

genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
_model = genai.GenerativeModel("gemini-1.5-flash")


async def _ask(prompt: str) -> str:
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, _model.generate_content, prompt)
    return response.text


RESUME_PROMPT = """\
You are an expert resume coach. Rewrite the resume below to match the job description by:
1. Reordering bullet points to foreground relevant experience
2. Adjusting the Professional Summary to mirror the job's exact language
3. Adding keywords from the JD where they honestly apply to the candidate
4. NEVER inventing skills or experience not present in the original resume
5. Keeping all dates, companies, and factual claims exactly as-is
6. Keeping output length within +-10% of the original

Return ONLY the tailored resume as plain text. No commentary, no markdown fences.
After the resume text, on a new line output exactly:
CHANGES_JSON: [{{"type":"added","phrase":"..."}}]
where each entry is a keyword added or phrase reworded.

JOB: {job_title} at {company}

JOB DESCRIPTION:
{job_description}

---

ORIGINAL RESUME:
{base_resume}"""

COVER_LETTER_PROMPT = """\
Write a cover letter for a software engineering student applying for {job_title} at {company}. Maximum 250 words.
Structure: Hook (1 sentence) -> Why This Role (2-3 sentences) -> What I Bring (3-4 sentences citing specific projects) -> Closing (1 sentence).
No filler phrases like "I am excited to apply." Sound confident. Use first person.

Resume:
{resume}

Key requirements:
{jd_snippet}"""

QA_PROMPT = """\
Answer the following job application screening questions honestly based on the candidate's resume.
- Be concise (1-3 sentences per answer), sound human, use first person
- For "notice period" or "availability" -> answer "Immediately available" (student)
- For "years of experience" -> count from first relevant project or internship
- For "expected salary" -> "As per company standards"
- Never fabricate experience

Resume:
{resume}

Job: {job_title} at {company}

Questions:
{questions}

Answer each question numbered exactly like:
1. [answer]
2. [answer]"""


async def generate_resume_and_cover_letter(
    base_resume: str,
    job_description: str,
    job_title: str,
    company: str,
) -> dict:
    resume_prompt = RESUME_PROMPT.format(
        job_title=job_title,
        company=company,
        job_description=job_description,
        base_resume=base_resume,
    )
    cover_prompt = COVER_LETTER_PROMPT.format(
        job_title=job_title,
        company=company,
        resume=base_resume,
        jd_snippet=job_description[:600],
    )

    # Run both concurrently to save time
    raw_resume, cover_letter = await asyncio.gather(
        _ask(resume_prompt),
        _ask(cover_prompt),
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


async def answer_screening_questions(
    tailored_resume: str,
    job_title: str,
    company: str,
    questions: list[str],
) -> list[dict]:
    questions_text = "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))
    prompt = QA_PROMPT.format(
        resume=tailored_resume,
        job_title=job_title,
        company=company,
        questions=questions_text,
    )
    raw = await _ask(prompt)
    answers = []
    lines = re.split(r'\n(?=\d+\.)', raw.strip())
    for i, line in enumerate(lines):
        answer_text = re.sub(r'^\d+\.\s*', '', line).strip()
        if i < len(questions):
            answers.append({"question": questions[i], "answer": answer_text})
    if len(answers) != len(questions):
        answers = [{"question": q, "answer": raw} for q in questions]
    return answers
