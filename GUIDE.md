# Job Apply Assistant — Complete Project Guide

## Table of Contents
1. [What is Job Apply Assistant?](#what-is-job-apply-assistant)
2. [Quick Start](#quick-start)
3. [The Safety Rules](#the-safety-rules)
4. [Architecture](#architecture)
5. [Backend Deep Dive](#backend-deep-dive)
6. [Frontend Deep Dive](#frontend-deep-dive)
7. [Feature Walkthrough](#feature-walkthrough)
8. [API Reference](#api-reference)
9. [Configuration](#configuration)
10. [Testing Strategy](#testing-strategy)
11. [What Is and Is Not Verified](#what-is-and-is-not-verified)
12. [Troubleshooting](#troubleshooting)

---

## What is Job Apply Assistant?

A tool that takes one job posting and does the repetitive part of applying:

1. reads the job description from a URL,
2. rewrites your resume to match it and drafts a cover letter,
3. answers the screening questions, flagging the ones only you may answer,
4. optionally fills the application form in a real browser and shows you a screenshot,
5. submits only after you confirm, and logs confirmed applications to a spreadsheet.

The language model is Groq, `openai/gpt-oss-120b` by default. Form filling uses Playwright. The
tracker is an `.xlsx` file written with openpyxl.

---

## Quick Start

The system `python3` is 3.6, so use Python 3.12 for the backend.

### Backend
```bash
cd backend
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium     # only needed for the apply flow
cp .env.example .env                      # add GROQ_API_KEY
.venv/bin/uvicorn main:app --port 8000 --reload
```

Get a free key at https://console.groq.com/keys.

### Frontend
```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev                               # http://localhost:3000
```

---

## The Safety Rules

These rules are the point of the design. Do not loosen them.

### 1. Nothing is submitted without your confirmation
`POST /api/apply` fills the form and returns a screenshot. The browser stays open in memory. Only
`POST /api/apply/confirm` presses submit.

### 2. Legal and eligibility questions are never answered for you
Questions about work authorisation, sponsorship, visas, citizenship, protected characteristics,
criminal record, security clearance or a driving licence come back as `needs_review` with no answer.
This is enforced twice:
- the prompt tells the model to defer,
- `ELIGIBILITY_PATTERN` in `services/llm_client.py` catches them anyway.

The second layer matters. In testing the model ignored the instruction and answered "Yes, I am
authorized to work in the UK". The classifier over-flags on purpose. A false flag costs five seconds.
A missed one puts a false legal claim on your application.

### 3. The form filler fills only what you gave it
`services/form_filler.py` reads each visible field by its label and either fills it from your
profile, cover letter or a closely matching screening answer, or leaves it for you. It never ticks a
consent box, never guesses a dropdown or radio option, and never invents a city or years of
experience.

### 4. "Submitted" means the site said so
After submit, the page is watched for a confirmation or an error:

| status | meaning | tracker | browser |
|---|---|---|---|
| `submitted` | the page confirmed it | logged | closed |
| `failed` | the form was rejected, with the fields named | not logged | kept open to fix and retry |
| `unconfirmed` | neither appeared | not logged | closed, since a retry could apply twice |

### 5. Paging stops before submit
Multi-step forms are paged through during preview, but never past a button that reads as submit.
Workday uses one selector for Next and Submit.

---

## Architecture

```
  Browser  (Next.js 16, :3000)
  resume + profile + application history in localStorage
        │ fetch  (lib/api.ts)
        ▼
  FastAPI  (:8000)  backend/main.py
   ├─ routers/scrape.py    ── services/scraper.py      httpx + BeautifulSoup
   ├─ routers/generate.py  ── services/llm_client.py   Groq
   ├─ routers/answers.py   ── services/llm_client.py   + ELIGIBILITY_PATTERN
   ├─ routers/resume.py    ── pypdf
   ├─ routers/apply.py     ── services/linkedin_bot.py or services/ats_bot.py
   │                          └─ services/form_filler.py   Playwright + Chromium
   │                          └─ services/resume_pdf.py    tailored resume to PDF
   ├─ routers/tracker.py   ── services/excel_tracker.py    jobs_applied.xlsx
   └─ routers/health.py
```

---

## Backend Deep Dive

### `services/scraper.py`
`detect_site(url)` recognises LinkedIn, Indeed, Naukri, Internshala, Greenhouse, Lever, Workday,
SmartRecruiters and iCIMS, each with its own selectors. `scrape_job(url)` returns title, company and
description.

### `services/llm_client.py`
- `generate_resume_and_cover_letter()` tailors the resume, writes the cover letter, and returns a
  keyword diff. A `CHANGES_JSON` trailer from the model is parsed and stripped.
- `answer_screening_questions()` answers each question, then `_finalise()` applies the eligibility
  pattern. An unparseable reply flags every question rather than risk mismatching answers.
- A missing key or a retired model raises `LLMUnavailable`, which the API returns as a 503 naming
  the problem.

### `services/form_filler.py`
| function | purpose |
|---|---|
| `scan_fields()` | lists visible fields with labels, types, options and required flags |
| `match_answer()` | pairs a label with a screening answer only when enough content words overlap |
| `plan_field()` | decides fill, leave for the candidate, or leave alone |
| `fill_page()` | carries out the plan and builds a `FillReport` |
| `native_invalid_fields()` | the browser's own required-field check before submitting |
| `verify_submission()` | waits for confirmation or error after submit |

### `services/linkedin_bot.py` and `services/ats_bot.py`
Site-specific navigation. LinkedIn Easy Apply for LinkedIn URLs, `ATSBot` for everything else. Both
delegate filling to `form_filler.py`.

### `services/resume_pdf.py`
Renders the tailored resume text as HTML and prints it to a real PDF with headless Chromium.

### `services/excel_tracker.py`
Appends confirmed applications to `jobs_applied.xlsx` in the backend's working directory.

---

## Frontend Deep Dive

| route | purpose |
|---|---|
| `/` | the main flow: job URL or pasted description, generate, review, answers, apply |
| `/profile` | your details used to fill forms |
| `/tracker` | applications recorded in this browser, and the spreadsheet download |

Key components:
- `ResultTabs`, `ResumeDiff` and `DiffHighlight` show the tailored resume against the original.
- `DownloadPanel` exports the resume and cover letter.
- `ApplyConfirmModal` shows the screenshot, what was filled, and the "answer these yourself" list,
  and handles retry after a `failed` confirm.
- `StepIndicator` and `Sidebar` handle navigation.

Your resume, profile and application history live in `localStorage` under `jaa_resume`,
`jaa_profile` and `jaa_applications`. Nothing is stored on a server except the spreadsheet.

---

## Feature Walkthrough

1. **Set up your profile** on `/profile` and upload or paste your resume. PDFs are parsed with pypdf.
2. **Paste a job URL.** The scraper pulls the description. For unsupported sites, choose "Paste JD
   manually" and fill in the job title and company too, so the tracker records them.
3. **Generate.** You get a tailored resume, a cover letter and a keyword diff. Dates, GPA and company
   names are preserved.
4. **Screening answers.** Enter the questions. Flagged ones appear in amber with no answer.
5. **Apply.** A visible browser opens, fills what it safely can and pages up to the submit button.
   The modal shows a screenshot and the fields you must answer.
6. **Answer the listed questions in the browser window**, then press confirm.
7. **Check the status.** Only `submitted` goes into the tracker.

---

## API Reference

| method | path | purpose |
|---|---|---|
| `GET` | `/api/health` | liveness |
| `POST` | `/api/scrape` | title, company and description from a job URL |
| `POST` | `/api/generate` | tailored resume, cover letter, keyword diff |
| `POST` | `/api/answers` | screening answers with `needs_review` flags |
| `POST` | `/api/parse-resume` | text from a PDF resume |
| `POST` | `/api/apply` | fill the form and return a screenshot, `fields_filled` and `needs_input`. Does not submit |
| `POST` | `/api/apply/confirm` | submit and report `submitted`, `failed` or `unconfirmed` |
| `POST` | `/api/apply/cancel` | close a previewed session's browser |
| `GET` | `/api/tracker/export` | download `jobs_applied.xlsx` |

---

## Configuration

| variable | file | default | notes |
|---|---|---|---|
| `GROQ_API_KEY` | `backend/.env` | none | required |
| `GROQ_MODEL` | `backend/.env` | `openai/gpt-oss-120b` | change when Groq retires a model |
| `ALLOWED_ORIGINS` | `backend/.env` | `http://localhost:3000` | comma separated |
| `APPLY_HEADLESS` | `backend/.env` | `false` | keep `false` so you can answer flagged fields in the window |
| `APPLY_SESSION_TTL` | `backend/.env` | `900` | seconds before an unconfirmed preview is closed, checked on the next call |
| `APPLY_CONFIRM_TIMEOUT` | `backend/.env` | `15` | seconds to wait for confirmation after submit |
| `NEXT_PUBLIC_API_URL` | `frontend/.env.local` | `http://localhost:8000` | |

---

## Testing Strategy

```bash
cd backend
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

No API key and no outside network are needed. Groq is stubbed.

- `tests/test_api.py` covers the routes. The stub deliberately answers "Yes, I am authorized to work
  in the UK", so the tests prove the classifier catches a model that ignores instructions.
- `tests/test_apply_flow.py` drives headless Chromium against the HTML forms in
  `tests/mock_forms/`, served on 127.0.0.1. It never contacts a real job site. It checks the preview
  never submits, that eligibility, consent, city and experience fields stay blank, the three confirm
  statuses, Workday-style paging, the PDF resume, and session cleanup.

Disabling the eligibility check or the validation check makes eight tests fail.

**Never point tests at a real employer.**

---

## What Is and Is Not Verified

- **Verified:** resume generation and answers against live Groq, PDF parsing, spreadsheet export,
  and the whole apply flow against the local mock forms, through both the API and the UI.
- **Not verified:** any real job site. The ATS selectors and all of the LinkedIn flow have never run
  live. LinkedIn needs a logged-in account, and automating it breaches its terms. `/api/scrape` has
  not been verified against live pages either.
- **Not deployed.**

Before trusting it on a real application, use a job you genuinely want, answer every item in the
needs-input list, and if confirm says `unconfirmed`, check your email before trying again.

---

## Troubleshooting

### 503 from `/api/generate` or `/api/answers`
Either `GROQ_API_KEY` is missing, or Groq retired the model. The message says which. For a retired
model, set `GROQ_MODEL` to a current one from https://console.groq.com/docs/models.

### `Executable doesn't exist` from Playwright
Chromium is not installed:
```bash
.venv/bin/playwright install chromium
```

### The scraper returns empty fields
The site's layout changed or is not supported. Paste the description instead.

### The frontend cannot reach the backend
Check the backend is on port 8000, `NEXT_PUBLIC_API_URL` matches, and `ALLOWED_ORIGINS` includes
the frontend's address.

### Confirm returned `failed`
The listed fields still need answers. Fill them in the open browser window and confirm again.

### Confirm returned `unconfirmed`
The page showed neither success nor error. Check your email or the site before applying again.
