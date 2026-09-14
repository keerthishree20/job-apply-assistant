"""The apply flow, driven headless against local mock forms.

These open a real Chromium and fill real HTML forms served from tests/mock_forms
on 127.0.0.1. No request goes to a job site, and nothing is ever submitted to an
employer. The LinkedIn-specific selectors are not covered: they need a live,
logged-in LinkedIn session.
"""

import asyncio
import functools
import io
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from services.form_filler import match_answer, plan_field
from services.resume_pdf import render_resume_pdf, resume_html

MOCK_DIR = Path(__file__).parent / "mock_forms"

PROFILE = {
    "name": "Anita Rao",
    "email": "anita@example.com",
    "phone": "+91 90000 00000",
    "linkedin_url": "https://linkedin.com/in/anita-example",
    "github_url": "",
    "portfolio_url": "",
    "college": "Riverbank University",
    "graduation_year": "2024",
}

RESUME_TEXT = """ANITA RAO
anita@example.com

EXPERIENCE
Backend intern, Example Corp
- Built REST APIs with FastAPI
- Cut p95 latency from 400 ms to 120 ms

EDUCATION
BSc Computer Science, Riverbank University, 2024
"""

ANSWERS = [
    {"question": "Why do you want to work here?", "answer": "Acme's API platform matches my FastAPI work.", "needs_review": False},
    {"question": "What is your expected salary?", "answer": "Open to discussion.", "needs_review": False},
    {"question": "What is your notice period?", "answer": "Immediately", "needs_review": False},
    {"question": "Can you work from the Bengaluru office?", "answer": "Yes", "needs_review": False},
    # Already flagged by the answers endpoint; must never reach the form.
    {"question": "Are you authorized to work in India?", "answer": "Yes", "needs_review": True},
]


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def mock_site():
    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    handler = functools.partial(Quiet, directory=str(MOCK_DIR))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


@pytest.fixture
def api(monkeypatch):
    """A TestClient on one event loop, so a browser opened in preview survives to confirm."""
    monkeypatch.setenv("APPLY_HEADLESS", "true")
    monkeypatch.setenv("APPLY_CONFIRM_TIMEOUT", "3")

    import main
    from routers import apply

    logged: list[dict] = []
    monkeypatch.setattr(apply, "append_application", lambda **kw: logged.append(kw))

    with TestClient(main.app) as client:
        client.logged = logged
        client.sessions = apply._sessions
        yield client
    assert not apply._sessions, "every browser should be closed when the app shuts down"


def _preview(api, url, **overrides):
    body = {
        "job_url": url,
        "resume_text": RESUME_TEXT,
        "cover_letter": "Dear Hiring Manager,\n\nI would like to apply.\n\nAnita",
        "profile": PROFILE,
        "screening_answers": ANSWERS,
        "company": "Acme",
        "role": "Backend Engineer",
    }
    body.update(overrides)
    res = api.post("/api/apply", json=body)
    assert res.status_code == 200, res.text
    return res.json()


def _on_page(api, session_id, fn):
    """Run `fn(page)` on the session's browser, on the app's event loop."""
    page = api.sessions[session_id].bot._page
    return api.portal.call(fn, page)


# --------------------------------------------------------------------------- #
# Deciding what to fill (no browser)
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("label", [
    "Are you legally authorized to work in the US?",
    "Will you now or in the future require visa sponsorship?",
    "Gender",
    "Do you have a disability?",
    "Veteran status",
])
def test_eligibility_labels_are_left_for_the_candidate_even_with_an_answer(label):
    # The prepared answer claims to answer it and is not flagged. The label still wins.
    answers = [{"question": label, "answer": "Yes", "needs_review": False}]
    for kind in ("text", "select", "radio"):
        field = {"kind": kind, "label": label, "required": False, "value": "", "options": ["Yes", "No"]}
        assert plan_field(field, PROFILE, answers, "").kind == "needs_input"


def test_a_prefilled_eligibility_answer_is_still_listed_for_review():
    field = {"kind": "select", "label": "Do you require sponsorship?", "required": True, "value": "No", "options": ["Yes", "No"]}
    assert plan_field(field, PROFILE, [], "").kind == "needs_input"


def test_profile_fields_fill_only_with_data_the_candidate_gave():
    def plan(label, kind="text", required=False):
        return plan_field({"kind": kind, "label": label, "required": required, "value": "", "options": []}, PROFILE, [], "")

    assert (plan("First Name *").kind, plan("First Name *").value) == ("fill", "Anita")
    assert plan("Last name").value == "Rao"
    assert plan("Email address", "email").value == "anita@example.com"
    assert plan("GitHub URL").kind == "skip"  # empty in the profile, optional
    assert plan("GitHub URL", required=True).kind == "needs_input"  # empty and required
    assert plan("Current city", required=True).kind == "needs_input"  # never "Coimbatore"
    assert plan("Years of experience", "number", required=True).kind == "needs_input"  # never "1"


def test_consent_checkboxes_are_never_ticked():
    field = {"kind": "checkbox", "label": "I certify the above is true", "required": True, "value": "", "options": []}
    assert plan_field(field, PROFILE, [], "").kind == "needs_input"


def test_choices_are_made_only_when_an_option_matches_the_answer_exactly():
    answers = [{"question": "What is your notice period?", "answer": "Immediately", "needs_review": False}]
    field = {"kind": "select", "label": "Notice period", "required": True, "value": "", "options": ["Immediately", "30 days"]}
    assert plan_field(field, PROFILE, answers, "").value == "Immediately"
    field["options"] = ["15 days", "30 days"]  # no first-option guess
    assert plan_field(field, PROFILE, answers, "").kind == "needs_input"


def test_answers_match_by_meaning_words_and_not_by_a_single_shared_word():
    qs = [
        {"question": "Why do you want to work here?", "answer": "a"},
        {"question": "Describe your experience with the primary tech stack.", "answer": "b"},
        {"question": "What is your expected salary?", "answer": "c"},
    ]
    assert match_answer("Why do you want to work at Acme?", qs)["answer"] == "a"
    assert match_answer("Salary expectations", qs)["answer"] == "c"
    assert match_answer("Years of experience", qs) is None
    assert match_answer("Where do you want to relocate?", qs) is None


def test_the_resume_is_a_real_pdf_with_the_candidate_text():
    pdf = asyncio.run(render_resume_pdf(RESUME_TEXT))
    assert pdf.startswith(b"%PDF")
    # pypdf splits some kerned pairs ("ANIT A"), so compare without whitespace.
    text = "".join(PdfReader(io.BytesIO(pdf)).pages[0].extract_text().split())
    assert "ANITARAO" in text and "Cutp95latencyfrom400msto120ms" in text


def test_resume_html_escapes_the_text():
    assert "<script>" not in resume_html("Name\n<script>alert(1)</script>")


# --------------------------------------------------------------------------- #
# End to end against the mock forms
# --------------------------------------------------------------------------- #

def test_preview_reports_exactly_what_was_filled_and_what_was_left(api, mock_site):
    prev = _preview(api, f"{mock_site}/single_page.html")

    assert set(prev["fields_filled"]) == {
        "First Name", "Last Name", "Email", "Phone", "LinkedIn Profile", "Resume (PDF)",
        "Cover Letter", "Why do you want to work at Acme?", "What are your salary expectations?",
        "What is your notice period?", "Can you work from the Bengaluru office?",
    }
    assert set(prev["needs_input"]) == {
        "City", "Years of experience", "Are you legally authorized to work in India?",
        "Do you require visa sponsorship?", "I agree to the privacy policy",
    }

    async def form_state(page):
        return await page.evaluate("""() => ({
            first: first_name.value, why: why.value, city: city.value, years: years.value,
            auth: auth.value, sponsor: !!document.querySelector('input[name=sponsor]:checked'),
            consent: consent.checked, notice: notice.value,
            office: (document.querySelector('input[name=office]:checked') || {}).value,
            resume: resume.files[0] && resume.files[0].name,
            submissions: window.__submissions,
        })""")

    state = _on_page(api, prev["session_id"], form_state)
    assert state["first"] == "Anita"
    assert state["why"] == ANSWERS[0]["answer"]
    # The option's markup has whitespace around "Immediately"; it must still be chosen.
    assert (state["notice"], state["office"]) == ("now", "y")
    assert (state["city"], state["years"], state["auth"]) == ("", "", "")
    assert not state["sponsor"] and not state["consent"]
    assert state["resume"].endswith(".pdf")
    assert state["submissions"] == 0, "preview must never submit"


@pytest.mark.parametrize("query", ["", "?novalidate"], ids=["browser-validation", "script-validation"])
def test_confirm_with_required_questions_unanswered_fails_and_logs_nothing(api, mock_site, query):
    prev = _preview(api, f"{mock_site}/single_page.html{query}")

    res = api.post("/api/apply/confirm", json={"session_id": prev["session_id"]}).json()

    assert res["status"] == "failed"
    assert res["session_open"] is True
    message = res["message"].lower()
    assert "city" in message and ("consent" in message or "privacy" in message)
    if not query:  # the browser path names radio groups by their question, not "Yes"
        assert "visa sponsorship" in message and "yes," not in message
    assert api.logged == []
    assert prev["session_id"] in api.sessions  # kept open to fix and retry
    assert _on_page(api, prev["session_id"], _submissions) == 0


async def _submissions(page):
    return await page.evaluate("window.__submissions")


@pytest.mark.parametrize("query", ["", "?novalidate"], ids=["browser-validation", "script-validation"])
def test_candidate_answers_in_the_browser_then_confirm_is_verified_and_logged(api, mock_site, query):
    prev = _preview(api, f"{mock_site}/single_page.html{query}")
    sid = prev["session_id"]

    # First attempt fails; the candidate then answers their own questions, as they
    # would in the visible browser window, and confirms again.
    assert api.post("/api/apply/confirm", json={"session_id": sid}).json()["status"] == "failed"

    async def candidate_answers(page):
        await page.fill("#city", "Chennai")
        await page.fill("#years", "0")
        await page.select_option("#auth", "Yes")
        await page.check("input[name=sponsor][value=no]")
        await page.check("#consent")

    _on_page(api, sid, candidate_answers)
    res = api.post("/api/apply/confirm", json={"session_id": sid}).json()

    assert res["status"] == "submitted"
    assert sid not in api.sessions
    assert len(api.logged) == 1
    assert api.logged[0]["company"] == "Acme" and api.logged[0]["role"] == "Backend Engineer"
    assert api.logged[0]["cover_letter"] is True
    assert api.post("/api/apply/confirm", json={"session_id": sid}).status_code == 404


def test_no_confirmation_means_unconfirmed_and_not_logged(api, mock_site):
    prev = _preview(api, f"{mock_site}/silent.html")
    assert prev["fields_filled"] == ["Email"]

    res = api.post("/api/apply/confirm", json={"session_id": prev["session_id"]}).json()

    assert res["status"] == "unconfirmed"
    assert api.logged == []
    assert prev["session_id"] not in api.sessions  # closed: a retry could submit twice


def test_multi_step_paging_stops_before_a_button_that_would_submit(monkeypatch, mock_site):
    monkeypatch.setenv("APPLY_HEADLESS", "true")
    from services.ats_bot import ATSBot

    async def run():
        bot = ATSBot(ats_type="myworkdayjobs.com")  # next and submit share one selector
        try:
            pdf = await render_resume_pdf(RESUME_TEXT)
            prev = await bot.fill_form(f"{mock_site}/multi_step.html", pdf, PROFILE, [], "")
            submitted = await bot._page.evaluate("window.__submitted")
            button = await bot._page.inner_text("#nav")
            return prev, submitted, button
        finally:
            await bot.close()

    prev, submitted, button = asyncio.run(run())
    assert submitted is False
    assert button == "Submit"
    assert prev["fields_filled"] == ["First Name", "Email Address", "Resume (PDF)"]


def test_cancel_closes_the_session(api, mock_site):
    prev = _preview(api, f"{mock_site}/silent.html")
    assert api.post("/api/apply/cancel", json={"session_id": prev["session_id"]}).status_code == 200
    assert prev["session_id"] not in api.sessions


def test_expired_sessions_are_closed(api, mock_site, monkeypatch):
    prev = _preview(api, f"{mock_site}/silent.html")
    monkeypatch.setenv("APPLY_SESSION_TTL", "0")
    res = api.post("/api/apply/confirm", json={"session_id": prev["session_id"]})
    assert res.status_code == 404
    assert not api.sessions


def test_a_non_pdf_upload_is_rejected_before_any_browser_opens(api):
    import base64
    res = api.post("/api/apply", json={
        "job_url": "http://127.0.0.1:9/never-opened",
        "resume_pdf_base64": base64.b64encode(b"plain text resume").decode(),
        "profile": PROFILE,
    })
    assert res.status_code == 400
    assert not api.sessions
