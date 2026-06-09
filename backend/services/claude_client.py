import asyncio
import json
import os
import re
from groq import AsyncGroq

client = AsyncGroq(api_key=os.environ["GROQ_API_KEY"])
MODEL = "llama-3.3-70b-versatile"


async def _ask(system: str, user: str) -> str:
    response = await client.chat.completions.create(
        model=MODEL,
        max_tokens=4096,
        temperature=0.4,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
    )
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
            answers.append({"question": questions[i], "answer": answer_text})
    if len(answers) != len(questions):
        answers = [{"question": q, "answer": raw} for q in questions]
    return answers
