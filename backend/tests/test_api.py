"""Offline tests for the API surface and the screening-answer safety guard.

Groq is stubbed throughout, so the suite runs with no key, no network and no
cost. The Playwright apply flow is covered separately, against local mock
forms, in test_apply_flow.py.
"""

import io

import pytest
from fastapi.testclient import TestClient

from services import llm_client


@pytest.fixture
def client(monkeypatch):
    """A TestClient with every Groq call replaced by a canned reply."""

    async def fake_ask(system: str, user: str) -> str:
        if "screening questions" in system.lower() or "1. [answer]" in system:
            # Deliberately answers the eligibility questions, so the tests prove
            # the guard catches a non-compliant model rather than a compliant one.
            return (
                "1. I admire the company's engineering culture.\n"
                "2. Yes, I am authorized to work in the UK.\n"
                "3. No, I do not require sponsorship.\n"
                "4. I used SQL throughout my internship."
            )
        if "cover letter" in system.lower():
            return "Dear Hiring Manager,\n\nI am writing to apply.\n\nAnita"
        return (
            "ANITA RAO\nBSc Computer Science, Riverbank University, 2024\n"
            "Built REST APIs with FastAPI.\n"
            'CHANGES_JSON: [{"type": "added", "phrase": "REST API"}]'
        )

    monkeypatch.setattr(llm_client, "_ask", fake_ask)

    import main

    return TestClient(main.app)


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"


# --- generation --------------------------------------------------------------


def test_generate_returns_resume_cover_letter_and_diff(client):
    response = client.post(
        "/api/generate",
        json={
            "base_resume": "ANITA RAO\nBSc Computer Science, Riverbank University, 2024",
            "job_description": "Backend engineer. FastAPI, PostgreSQL, Docker.",
            "job_title": "Backend Engineer",
            "company": "Northwind Data",
        },
    )
    assert response.status_code == 200
    body = response.json()

    assert "Riverbank" in body["tailored_resume"], "factual detail was dropped"
    # The CHANGES_JSON trailer is parsed out, not left in the resume text.
    assert "CHANGES_JSON" not in body["tailored_resume"]
    assert body["keywords_added"] == ["REST API"]
    assert body["cover_letter"].startswith("Dear Hiring Manager")


# --- the screening-answer guard ---------------------------------------------


@pytest.mark.parametrize(
    "question",
    [
        "Are you authorised to work in the UK?",
        "Will you now or in the future require visa sponsorship?",
        "What is your citizenship?",
        "Do you have a disability?",
        "What is your date of birth?",
        "Have you ever been convicted of a felony?",
        "Do you hold a valid driving licence?",
        "Do you have the right to work in this country?",
    ],
)
def test_eligibility_questions_are_never_answered_for_the_candidate(question):
    """A guessed answer here is a misrepresentation on a job application.

    This is checked on the classifier directly, so it holds regardless of what
    the model returned -- including the compliant-sounding "Yes" the stub gives.
    """
    result = llm_client._finalise(question, "Yes, absolutely.")
    assert result["needs_review"] is True
    assert "Yes, absolutely." not in result["answer"]
    assert "yourself" in result["answer"]


@pytest.mark.parametrize(
    "question",
    [
        "Why do you want to work here?",
        "Describe your experience with SQL.",
        "What is your expected salary?",
        "When can you start?",
    ],
)
def test_ordinary_questions_keep_their_answer(question):
    result = llm_client._finalise(question, "A normal answer.")
    assert result["needs_review"] is False
    assert result["answer"] == "A normal answer."


def test_answers_endpoint_flags_eligibility_questions_end_to_end(client):
    response = client.post(
        "/api/answers",
        json={
            "job_description": "Backend engineer.",
            "job_title": "Backend Engineer",
            "company": "Northwind Data",
            "tailored_resume": "ANITA RAO, BSc Computer Science.",
            "questions": [
                "Why do you want to work here?",
                "Are you authorised to work in the UK?",
                "Will you require sponsorship?",
                "Describe your experience with SQL.",
            ],
        },
    )
    assert response.status_code == 200
    answers = response.json()["answers"]
    assert len(answers) == 4

    flagged = {a["question"]: a["needs_review"] for a in answers}
    assert flagged["Are you authorised to work in the UK?"] is True
    assert flagged["Will you require sponsorship?"] is True
    assert flagged["Why do you want to work here?"] is False
    assert flagged["Describe your experience with SQL."] is False

    # The model's fabricated "Yes, I am authorized" must not survive to the API.
    for answer in answers:
        if answer["needs_review"]:
            assert "authorized to work" not in answer["answer"].lower()


def test_unparseable_model_reply_flags_everything_rather_than_mispairing(monkeypatch):
    """If the numbered format doesn't parse, nothing is silently mis-attributed."""

    async def unnumbered(system: str, user: str) -> str:
        return "I think all of these are fine honestly"

    monkeypatch.setattr(llm_client, "_ask", unnumbered)

    import asyncio

    answers = asyncio.run(
        llm_client.answer_screening_questions(
            "resume", "Backend Engineer", "Northwind", ["Q one?", "Q two?"]
        )
    )
    assert len(answers) == 2
    assert all(a["needs_review"] for a in answers)


# --- resume parsing ----------------------------------------------------------


def _one_page_pdf(text: str) -> bytes:
    """A minimal text PDF, built by hand so the tests need no extra dependency."""
    content = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + obj + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objs) + 1,
        xref,
    )
    return bytes(out)


def test_parse_resume_extracts_text_from_a_pdf(client):
    pdf = _one_page_pdf("ANITA RAO - Backend Engineer")
    response = client.post(
        "/api/parse-resume", files={"file": ("cv.pdf", io.BytesIO(pdf), "application/pdf")}
    )
    assert response.status_code == 200
    assert "ANITA RAO" in response.json()["text"]


def test_parse_resume_rejects_non_pdf(client):
    response = client.post(
        "/api/parse-resume",
        files={"file": ("cv.txt", io.BytesIO(b"plain text"), "text/plain")},
    )
    assert response.status_code == 400
    assert "PDF" in response.json()["detail"]


def test_parse_resume_rejects_an_image_only_pdf(client):
    """A scanned CV extracts no text -- say so rather than returning empty."""
    pdf = _one_page_pdf("")
    response = client.post(
        "/api/parse-resume",
        files={"file": ("scan.pdf", io.BytesIO(pdf), "application/pdf")},
    )
    assert response.status_code == 422
    assert "scanned" in response.json()["detail"].lower()


# --- configuration failure ---------------------------------------------------


def test_missing_api_key_is_a_503_with_instructions(monkeypatch):
    """A missing key is a config problem: 503 and how to fix it, not a 500."""
    monkeypatch.setattr(llm_client, "_client", None)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    import main

    with TestClient(main.app, raise_server_exceptions=False) as c:
        response = c.post(
            "/api/generate",
            json={"base_resume": "CV", "job_description": "JD"},
        )

    assert response.status_code == 503
    assert "GROQ_API_KEY" in response.json()["detail"]


def test_tracker_export_returns_a_spreadsheet(client):
    response = client.get("/api/tracker/export")
    assert response.status_code == 200
    assert "spreadsheet" in response.headers["content-type"]
    assert response.content[:2] == b"PK", "xlsx files are zip archives"
