# Job Apply Assistant — Complete Project Guide

A complete guide from zero to a working job application assistant. Covers every feature, every safety
rule and the reason behind it, with the real code. It is self-contained: you can paste it into any AI
chat and ask questions about the project without sharing the repository.

**Repository:** https://github.com/keerthishree20/job-apply-assistant
**All projects:** https://github.com/keerthishree20

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Tech Stack & Why](#2-tech-stack--why)
3. [Project Setup from Scratch](#3-project-setup-from-scratch)
4. [The Pipeline in Plain Words](#4-the-pipeline-in-plain-words)
5. [Project Structure](#5-project-structure)
6. [Safety Rule 1: Nothing Is Submitted Without You](#6-safety-rule-1-nothing-is-submitted-without-you)
7. [Safety Rule 2: Legal Questions Are Never Answered](#7-safety-rule-2-legal-questions-are-never-answered)
8. [Safety Rule 3: Fill Only What You Gave It](#8-safety-rule-3-fill-only-what-you-gave-it)
9. [Safety Rule 4: "Submitted" Means the Site Said So](#9-safety-rule-4-submitted-means-the-site-said-so)
10. [Scraping a Job Posting](#10-scraping-a-job-posting)
11. [Resume Parsing](#11-resume-parsing)
12. [Tailored Resume & Cover Letter](#12-tailored-resume--cover-letter)
13. [Screening Answers](#13-screening-answers)
14. [The Groq Model and Retirements](#14-the-groq-model-and-retirements)
15. [Form Filling: Scan, Plan, Fill](#15-form-filling-scan-plan-fill)
16. [LinkedIn and ATS Bots](#16-linkedin-and-ats-bots)
17. [Multi-Step Forms (the Workday Trap)](#17-multi-step-forms-the-workday-trap)
18. [The Resume PDF](#18-the-resume-pdf)
19. [Apply Sessions](#19-apply-sessions)
20. [The Application Tracker](#20-the-application-tracker)
21. [Frontend Pages](#21-frontend-pages)
22. [API Reference](#22-api-reference)
23. [Configuration](#23-configuration)
24. [Testing](#24-testing)
25. [What Is and Is Not Verified](#25-what-is-and-is-not-verified)
26. [Troubleshooting](#26-troubleshooting)
27. [Complete Feature Summary](#27-complete-feature-summary)

---

## 1. Project Overview

Job Apply Assistant takes **one job posting** and does the repetitive part of applying:

1. reads the job description from a URL (or you paste it),
2. rewrites your resume to match it and drafts a cover letter,
3. answers the screening questions, flagging the ones only you may answer,
4. if you choose, fills the application form in a real browser and shows you a screenshot,
5. submits **only after you confirm**, and logs confirmed applications to a spreadsheet.

The design is built around one principle: **a guessed answer on a job application is a
misrepresentation by the candidate.** So the tool fills only what you actually gave it, and never
answers legal questions for you.

**Status:** backend and frontend built, 43 tests pass. The apply flow is verified against local mock
forms only, never a real job site. Not deployed.

---

## 2. Tech Stack & Why

| Technology | Role | Why We Chose It |
|---|---|---|
| **FastAPI** | Backend | async routes for browser automation, typed request models |
| **Groq** (`openai/gpt-oss-120b`) | AI writing | free tier, fast; model is a setting because Groq retires models |
| **Playwright + Chromium** | Form filling | drives a real browser you can watch and correct |
| **httpx + BeautifulSoup** | Scraping | fetch and parse job pages |
| **pypdf** | Resume parsing | extract text from your PDF |
| **openpyxl** | Tracker | writes `jobs_applied.xlsx` |
| **Next.js 16, React 19, TypeScript, Tailwind** | Frontend | step-by-step UI, diff view, confirm modal |
| **localStorage** | Your data | resume, profile and history stay in your browser |

---

## 3. Project Setup from Scratch

### Backend (Python 3.12; the system `python3` is 3.6)
```bash
git clone https://github.com/keerthishree20/job-apply-assistant.git
cd job-apply-assistant/backend
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium     # only needed for the apply flow
cp .env.example .env                      # add GROQ_API_KEY from https://console.groq.com/keys
.venv/bin/uvicorn main:app --port 8000 --reload
```

### Frontend
```bash
cd ../frontend
npm install
cp .env.example .env.local
npm run dev                               # http://localhost:3000
```

---

## 4. The Pipeline in Plain Words

```
job URL ──► scrape ──► tailor resume + cover letter ──► answer screening questions
                                                               │
                                     screenshot preview ◄── fill form
                                             │
                                    YOU confirm ──► submit ──► logged to xlsx
```

---

## 5. Project Structure

```
backend/
  main.py                  FastAPI app, CORS, routers
  routers/
    scrape.py              POST /api/scrape
    resume.py              POST /api/parse-resume
    generate.py            POST /api/generate
    answers.py             POST /api/answers
    apply.py               POST /api/apply, /api/apply/confirm, /api/apply/cancel; sessions
    tracker.py             GET /api/tracker/export
    health.py              GET /api/health
  services/
    scraper.py             detect_site(), scrape_job()
    llm_client.py          Groq calls, ELIGIBILITY_PATTERN, LLMUnavailable
    form_filler.py         scan_fields, match_answer, plan_field, fill_page, verify_submission
    linkedin_bot.py        LinkedIn Easy Apply
    ats_bot.py             Workday, Greenhouse, Lever, SmartRecruiters, iCIMS and others
    resume_pdf.py          tailored resume → real PDF via headless Chromium
    excel_tracker.py       jobs_applied.xlsx
  schemas/models.py        request and response models
  utils/text_cleaner.py    cleaning scraped text
  tests/
    test_api.py            routes, eligibility guard, parsing
    test_apply_flow.py     headless Chromium against mock forms
    mock_forms/            single_page.html, multi_step.html, silent.html
frontend/
  app/page.tsx             the main flow
  app/profile/page.tsx     your details
  app/tracker/page.tsx     your applications and Excel export
  components/              ApplyConfirmModal, ResumeDiff, DiffHighlight, ResultTabs,
                           DownloadPanel, StepIndicator, Sidebar
  lib/api.ts  lib/localStorage.ts  lib/types.ts
```

---

## 6. Safety Rule 1: Nothing Is Submitted Without You

`POST /api/apply` fills the form and returns a **screenshot**, the list of fields filled, and the list
of fields you must answer. The browser stays open in memory. **Only** `POST /api/apply/confirm` presses
submit.

That split is the whole safety design. Do not collapse it into one call.

---

## 7. Safety Rule 2: Legal Questions Are Never Answered

Screening forms mix normal questions with legal ones. A model asked "Are you authorised to work in the
UK?" will happily answer "Yes", and that is a false legal claim on an application.

Any question about **work authorisation, sponsorship, visas, citizenship, protected characteristics
(disability, age, gender, ethnicity, marital status), criminal record, security clearance or a driving
licence** comes back `needs_review` with **no answer**. The UI shows them in amber.

It is enforced **twice**:
1. the prompt tells the model to defer,
2. a keyword classifier catches it anyway:

```python
ELIGIBILITY_PATTERN = re.compile(
    r"\b("
    r"authoris\w*|authoriz\w*|sponsorship|sponsor|visa|citizen\w*|nationality"
    r"|passport|immigration|residen\w*|permanent\s+resident|green\s+card"
    r"|right\s+to\s+work|eligible\s+to\s+work|legally\s+\w+\s+to\s+work|work\s+permit"
    r"|disab\w*|veteran|gender|ethnic\w*|\brace\b|religion|marital|pregnan\w*"
    r"|sexual\s+orientation|date\s+of\s+birth|how\s+old\s+are|\bage\b"
    r"|criminal|conviction|convicted|felony|background\s+check"
    r"|security\s+clearance|drug\s+test"
    r"|driv\w*\s+licen[cs]e|licen[cs]e\s+to\s+driv\w*"
    r")\b",
    re.IGNORECASE,
)

def _finalise(question, answer):
    needs_review = bool(ELIGIBILITY_PATTERN.search(question)) or NEEDS_INPUT in answer
    return {"question": question,
            "answer": NEEDS_INPUT_TEXT if needs_review else answer,
            "needs_review": needs_review}
```

### Why the second layer matters
During testing, the model **ignored the instruction** and answered "Yes, I am authorized to work in the
UK" anyway. The classifier caught it.

### Why it over-flags on purpose
A false flag costs you five seconds. A missed one puts a false legal claim on your application. **Do not
"tidy" this into prompt-only.**

---

## 8. Safety Rule 3: Fill Only What You Gave It

`services/form_filler.py` reads every visible field by its label and does one of three things:

| Decision | When |
|---|---|
| **Fill it** | from your profile (name, email, phone, links, college, graduation year), from the cover letter, or from a screening answer whose question closely matches the label |
| **Leave it for you** (listed as "answer these yourself") | an eligibility label (even if the site pre-filled it), any consent checkbox, a required field with no data, a dropdown or radio with no exactly matching option |
| **Leave it alone** | optional and nothing matches |

Before 2026-09-14, the LinkedIn bot picked the first radio and dropdown option, typed "1" for
experience, hardcoded the city "Coimbatore", and used a canned cover letter. **None of that remains,
and it must never come back.**

---

## 9. Safety Rule 4: "Submitted" Means the Site Said So

After clicking submit, the tool watches the page for a confirmation or an error:

```python
async def verify_submission(page, before, timeout=None):
    ...
    while True:
        now = await page_state(page)
        new_errors = [e for e in now["errors"] if e not in before_errors]
        if new_errors:
            return {"status": "failed", "detail": "; ".join(new_errors[:5])}
        if not before_success and _SUCCESS.search(now["text"]):
            return {"status": "submitted", ...}          # "Thank you for applying"
        if now["url"] != before["url"] and _SUCCESS_URL.search(now["url"]):
            return {"status": "submitted", ...}          # confirmation URL
        if past deadline:
            return {"status": "unconfirmed", ...}
        await asyncio.sleep(0.25)
```

Only signals that appeared **after** the click count, so a "* required" legend or a job description
mentioning "applications" cannot be misread.

| Status | Meaning | Tracker | Browser |
|---|---|---|---|
| `submitted` | the page confirmed it | logged | closed |
| `failed` | the form was rejected; the message names the fields | not logged | kept open to fix and retry |
| `unconfirmed` | neither appeared | not logged | closed, because a retry could apply twice |

Before submitting, the browser's own required-field validation is checked too
(`native_invalid_fields`).

---

## 10. Scraping a Job Posting

`services/scraper.py`:
- `detect_site(url)` recognises LinkedIn, Indeed, Naukri, Internshala, Greenhouse, Lever, Workday
  (`myworkdayjobs.com`), SmartRecruiters and iCIMS, each with its own CSS selectors for title, company
  and description.
- `scrape_job(url)` fetches the page with httpx, parses it with BeautifulSoup, and falls back to the
  largest block of text for unknown sites.

If scraping fails, the UI opens **"Paste JD manually"**, with fields for the description, job title and
company (the title and company go into the tracker).

---

## 11. Resume Parsing

`POST /api/parse-resume` takes a PDF and extracts its text with pypdf. It rejects non-PDFs and PDFs with
no extractable text (scanned images).

---

## 12. Tailored Resume & Cover Letter

`generate_resume_and_cover_letter()` sends your resume and the job description to Groq with a detailed
system prompt ("senior technical recruiter"). It returns:
- a **tailored resume** that keeps every factual detail (dates, GPA, company names were all preserved in
  testing),
- a **cover letter**,
- a **keyword diff**: which job keywords are now covered.

The model appends a `CHANGES_JSON` trailer describing its changes; it is parsed and stripped from the
resume text. The frontend shows the original and tailored resume side by side (`ResumeDiff`).

---

## 13. Screening Answers

`answer_screening_questions()` answers each question from your tailored resume and the job, then
`_finalise()` applies the eligibility rule (section 7).

If the model's reply cannot be parsed, **every** question is flagged rather than risk pairing an answer
with the wrong question.

---

## 14. The Groq Model and Retirements

```python
MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

async def _ask(system, user):
    try:
        response = await _get_client().chat.completions.create(model=MODEL, max_tokens=4096, ...)
    except NotFoundError as exc:
        raise LLMUnavailable(f"Groq has no model named {MODEL!r} ... it was most likely retired. "
                             f"Set GROQ_MODEL in backend/.env ...")
```

The original model, `llama-3.3-70b-versatile`, was **decommissioned** by Groq and every call returned
404. Now the model is a setting, and a retired model or missing key returns a **503** that names the fix
instead of a 500 traceback. Check https://console.groq.com/docs/models when it happens again.

---

## 15. Form Filling: Scan, Plan, Fill

### Scan
`scan_fields(page)` lists every visible field: label, kind (text, email, tel, number, textarea,
select, radio, checkbox, file), options, required flag and current value.

### Match
```python
def match_answer(label, answers):
    label_stems = _stems(label)
    for item in answers:
        q = _stems(item.get("question", ""))
        shared = len(label_stems & q)
        if shared < 2:
            continue
        score = shared / min(len(label_stems), len(q))
        if score >= 0.6 and score > best_score:
            best, best_score = item, score
    return best
```
It needs **two shared content words and 60% overlap**. A near miss returns nothing, and the field is
left blank rather than filled with the answer to a different question.

### Plan
`plan_field(field, profile, answers, cover_letter)` decides per field, in this order:
1. file inputs → upload the resume (never a cover-letter slot),
2. **eligibility label → needs your input**, even if already filled,
3. already filled → skip,
4. checkbox → needs your input (consent is yours to give),
5. profile field (name, email, phone...) → fill from your profile, or needs input if missing,
6. cover letter textarea → fill with the cover letter,
7. otherwise → matching screening answer; flagged answers need input; a dropdown or radio needs an
   **exactly** matching option; a number field needs a number.

### Fill
`fill_page()` carries out the plan and returns a `FillReport`: what was filled, what needs you.

---

## 16. LinkedIn and ATS Bots

- **`LinkedInBot`** handles LinkedIn Easy Apply. It needs you to be logged in, and automating LinkedIn
  breaches its terms, so only use it yourself, on jobs you truly want.
- **`ATSBot`** handles the others (Workday, Greenhouse, Lever, SmartRecruiters, iCIMS, generic).

Both use `form_filler.py` for every filling decision, so the safety rules apply the same way.

---

## 17. Multi-Step Forms (the Workday Trap)

Multi-step forms are paged through during the preview, but paging **stops in front of any button that
reads as submit**. Workday uses one selector for "Next" and "Submit", and the old loop could click
through to a real submission before you confirmed anything.

---

## 18. The Resume PDF

`services/resume_pdf.py` turns the tailored resume text into styled HTML and prints it to a **real PDF**
with headless Chromium. Previously it uploaded the plain text, base64-encoded, with a `.pdf` name.

---

## 19. Apply Sessions

`routers/apply.py` keeps a preview's open browser in `_sessions`:

- `APPLY_SESSION_TTL` (900 s): an unconfirmed preview's browser is closed after this age, checked on the
  next apply or confirm call.
- A session is `busy` while submitting, so a double click gets a `409`.
- **failed** keeps the session (and refreshes its age) so you can fix and confirm again.
- **submitted** and **unconfirmed** end the session and close the browser.
- `POST /api/apply/cancel` closes it at any time.

---

## 20. The Application Tracker

`services/excel_tracker.py` appends **only confirmed** applications to `jobs_applied.xlsx` in the
backend folder, with columns:

`S.No, Company, Role, Job URL, Date Applied, Status, Resume Version, Cover Letter, Notes`

The notes record the page's confirmation text. `GET /api/tracker/export` downloads the file; the
Tracker page has an "Export Excel" button. The browser also keeps its own list in localStorage.

---

## 21. Frontend Pages

| Route | Purpose |
|---|---|
| `/` | the main flow: upload resume, job URL or pasted description (with title and company), generate, review, answers, apply |
| `/profile` | your details used to fill forms |
| `/tracker` | your applications and the Excel export |

| Component | Purpose |
|---|---|
| `ApplyConfirmModal` | screenshot, filled fields, "answer these yourself" list, confirm, retry after `failed` |
| `ResumeDiff`, `DiffHighlight` | original vs tailored resume |
| `ResultTabs` | resume, cover letter, answers |
| `DownloadPanel` | download the documents |
| `StepIndicator`, `Sidebar` | progress and navigation |

Your data lives in `localStorage`: `jaa_resume`, `jaa_profile`, `jaa_applications`.

---

## 22. API Reference

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | liveness |
| POST | `/api/scrape` | title, company and description from a job URL |
| POST | `/api/parse-resume` | text from a PDF resume |
| POST | `/api/generate` | tailored resume, cover letter, keyword diff |
| POST | `/api/answers` | screening answers with `needs_review` flags |
| POST | `/api/apply` | fill the form; screenshot, `fields_filled`, `needs_input`. **Does not submit** |
| POST | `/api/apply/confirm` | submit; returns `submitted` / `failed` / `unconfirmed` |
| POST | `/api/apply/cancel` | close a preview's browser |
| GET | `/api/tracker/export` | download `jobs_applied.xlsx` |

---

## 23. Configuration

| Variable | File | Default | Notes |
|---|---|---|---|
| `GROQ_API_KEY` | `backend/.env` | none | required |
| `GROQ_MODEL` | `backend/.env` | `openai/gpt-oss-120b` | change when Groq retires it |
| `ALLOWED_ORIGINS` | `backend/.env` | `http://localhost:3000` | comma separated |
| `PORT` | `backend/.env` | `8000` | |
| `APPLY_HEADLESS` | `backend/.env` | `false` | keep `false` locally so you can answer in the window |
| `APPLY_SESSION_TTL` | `backend/.env` | `900` | seconds before an unconfirmed preview closes |
| `APPLY_CONFIRM_TIMEOUT` | `backend/.env` | `15` | seconds to wait for confirmation |
| `NEXT_PUBLIC_API_URL` | `frontend/.env.local` | `http://localhost:8000` | |

---

## 24. Testing

```bash
cd backend
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest          # 43 tests; apply tests need Chromium, about 45 s
```

No key and no outside network: Groq is stubbed.

- **The stub deliberately answers "Yes, I am authorized to work in the UK"**, so the tests prove the
  classifier catches a model that ignores instructions.
- Also: resume tailoring keeps facts, the `CHANGES_JSON` trailer is stripped, an unparseable reply flags
  everything, PDF rejection paths, and a missing key returning 503.
- `tests/test_apply_flow.py` drives headless Chromium against the HTML forms in `tests/mock_forms/`,
  served on 127.0.0.1. It never contacts a real site. It checks that the preview never submits,
  eligibility/consent/city/experience stay blank, the three statuses, Workday-style paging stops at
  Submit, the resume is a readable PDF, and cancel and expiry close the browser.

**Disabling the eligibility check or the validation check makes eight tests fail.** Never point tests
at a real employer.

---

## 25. What Is and Is Not Verified

- **Verified:** generation and answers against live Groq (every date, GPA and company name preserved),
  PDF parsing, the spreadsheet, and the full apply flow against local mock forms through the API and
  through the UI.
- **Not verified:** any real job site. The ATS selectors and all of LinkedIn have never run live.
  `/api/scrape` against live pages is unverified too.
- **Not deployed.**

Before trusting it on a real application: use a job you genuinely want, answer every item in the
needs-input list, and if confirm says `unconfirmed`, check your email before trying again.

---

## 26. Troubleshooting

| Problem | Fix |
|---|---|
| 503 from generate or answers | missing `GROQ_API_KEY`, or the model was retired; set `GROQ_MODEL` |
| `Executable doesn't exist` | `.venv/bin/playwright install chromium` |
| scraper returns empty fields | site changed or unsupported; paste the description, title and company |
| frontend cannot reach backend | backend on 8000? `NEXT_PUBLIC_API_URL` and `ALLOWED_ORIGINS` match? |
| confirm returned `failed` | fill the listed fields in the open browser and confirm again |
| confirm returned `unconfirmed` | check your email or the site before applying again |

---

## 27. Complete Feature Summary

### All Features Built

| # | Feature | Type | Key Files |
|---|---|---|---|
| 1 | Job page scraping for 9 sites | Backend | `scraper.py` |
| 2 | Manual description with title and company | Frontend | `app/page.tsx` |
| 3 | PDF resume parsing | Backend | `routers/resume.py` |
| 4 | Tailored resume, cover letter, keyword diff | AI | `llm_client.py` |
| 5 | Screening answers | AI | `llm_client.py` |
| 6 | Two-layer eligibility guard | Safety | `llm_client.py`, `form_filler.py` |
| 7 | Retired-model handling (`GROQ_MODEL`, 503) | AI | `llm_client.py` |
| 8 | Field scanning, matching and planning | Automation | `form_filler.py` |
| 9 | LinkedIn and ATS bots | Automation | `linkedin_bot.py`, `ats_bot.py` |
| 10 | Stop before submit when paging | Safety | bots |
| 11 | Preview → confirm split with sessions | Safety | `routers/apply.py` |
| 12 | Submission verification with 3 statuses | Safety | `form_filler.py` |
| 13 | Real PDF resume | Backend | `resume_pdf.py` |
| 14 | Excel tracker of confirmed applications | Backend | `excel_tracker.py` |
| 15 | Resume diff and confirm modal | Frontend | `components/` |
| 16 | Profile and tracker pages | Frontend | `app/profile`, `app/tracker` |
| 17 | Mock-form browser tests | Testing | `tests/test_apply_flow.py` |

### Data Flow Architecture

```
Browser (Next.js :3000, data in localStorage)
  ├── upload PDF ──► POST /api/parse-resume ──► pypdf text
  ├── job URL ──► POST /api/scrape ──► httpx + BeautifulSoup (or paste manually)
  ├── Generate ──► POST /api/generate + /api/answers ──► Groq ──► ELIGIBILITY_PATTERN
  └── Apply ──► POST /api/apply
        └── Playwright Chromium (visible)
              scan_fields ──► plan_field ──► fill_page ──► page up to Submit ──► screenshot
              session kept open ──► ApplyConfirmModal shows fields + "answer these yourself"
        └── you answer in the window ──► POST /api/apply/confirm
              native validation ──► click submit ──► verify_submission
                ├── submitted   ──► jobs_applied.xlsx, close browser
                ├── failed      ──► keep browser, show fields
                └── unconfirmed ──► close browser, nothing logged
```

### Tech Stack at a Glance

```
Backend:   FastAPI, Groq (openai/gpt-oss-120b), Playwright + Chromium, httpx, BeautifulSoup, pypdf, openpyxl
Frontend:  Next.js 16 + React 19 + TypeScript + Tailwind
Storage:   localStorage (profile, resume, history), jobs_applied.xlsx (confirmed applications)
Testing:   pytest, headless Chromium against local mock forms, stubbed Groq
```
