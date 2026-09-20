# Job Apply Assistant

[![tests](https://github.com/keerthishree20/job-apply-assistant/actions/workflows/tests.yml/badge.svg)](https://github.com/keerthishree20/job-apply-assistant/actions/workflows/tests.yml)

Takes one job posting and does the repetitive part of applying: reads the
description, rewrites your resume against it, drafts a cover letter, answers the
screening questions, and — if you let it — fills the application form and shows
you a screenshot before anything is submitted.

## The pipeline

```
job URL ──► scrape ──► tailor resume + cover letter ──► answer screening Qs
                                                              │
                                    screenshot preview ◄── fill form
                                            │
                                   YOU confirm ──► submit ──► logged to xlsx
```

**Nothing is submitted without an explicit confirmation.** `POST /api/apply`
fills the form and returns a screenshot; the browser session is held open in
memory and only `POST /api/apply/confirm` presses submit. That split is the
whole safety design — don't collapse it.

## What it will not answer for you

Screening forms mix ordinary questions with legal ones. A model asked "are you
authorised to work in the UK?" will cheerfully answer "Yes" — and that is a
misrepresentation on a job application, not a rough draft.

So any question about **work authorisation, sponsorship, visa or citizenship,
protected characteristics (disability, age, gender, ethnicity, marital status),
criminal record, security clearance, or a driving licence** comes back flagged
`needs_review`, with no answer filled in. The UI shows those in amber and tells
you to answer them yourself.

This is enforced twice: the prompt tells the model to defer, and a keyword
classifier in `services/llm_client.py` catches the cases where it doesn't. The
second layer is the one that matters — during testing the model ignored the
instruction and answered "Yes, I am authorized to work in the UK" anyway.

The classifier deliberately over-flags. A false flag costs you five seconds; a
false negative puts a false legal claim on your application.

## What the form filler will and will not fill

The same rule applies on the application form itself: **fill only what you
actually gave it, never guess.** `services/form_filler.py` reads every visible
field by its label and does one of three things:

- **Fills it** from your profile (name, email, phone, links, college, graduation
  year), from the cover letter, or from a screening answer whose question shares
  enough content words with the label. A near miss is left blank rather than
  filled with the answer to a different question.
- **Leaves it for you** and lists it in the preview under "You need to answer
  these yourself". That covers:
  - a label matching the eligibility classifier, even when an answer exists and even when the site pre-filled one
  - any consent checkbox
  - a required field with no data behind it
  - a dropdown or radio group where no option matches the prepared answer exactly
- **Leaves it alone** if it is optional and nothing matches.

Earlier versions picked the first radio button and first dropdown option on
every question, typed "1" into any experience field, a fixed city into any
location field, and a canned cover letter into any textarea. None of that
remains.

The bot opens a visible browser by default, so you answer the listed questions
in that window before confirming.

### What "submitted" means

`/api/apply/confirm` does not assume the click worked. It first checks the
browser's own required-field validation, then waits for the page to show a
confirmation or an error, and returns one of three statuses:

| Status | Meaning | Tracker | Browser |
|---|---|---|---|
| `submitted` | The page confirmed it ("Thank you for applying", a confirmation URL) | logged | closed |
| `failed` | The form was rejected; the message names the fields | not logged | kept open to fix and retry |
| `unconfirmed` | No confirmation and no error appeared | not logged | closed, because a retry could apply twice |

Multi-step forms are paged through during preview, but paging stops in front of
any button that reads as a submit. Workday uses one selector for "Next" and
"Submit", and the old loop could click through to a real submission before you
had confirmed anything.

The resume is uploaded as a real PDF, rendered from the tailored text with
headless Chromium. Previously it was the plain text, base64-encoded, with a `.pdf`
name.

## Tech stack

- **Backend** — FastAPI, Playwright (LinkedIn Easy Apply + generic ATS),
  openpyxl for the tracker, pypdf for resume parsing
- **Frontend** — Next.js 16, React 19, TypeScript, Tailwind
- **LLM** — **Groq**, `openai/gpt-oss-120b` by default

> Earlier docs here said Gemini. That was never true of this code — it has
> always called Groq, via `services/llm_client.py`.

### On the model ID

Groq retires models on a rolling schedule. The original pick,
`llama-3.3-70b-versatile`, has been decommissioned — every generate call was
returning a 404 until this was fixed. The model is now read from `GROQ_MODEL`,
so the next retirement is an `.env` edit rather than a code change, and a
retired model returns a 503 that names the problem instead of a 500 traceback.

Check <https://console.groq.com/docs/models> for what is current.

## Running it

**Backend** — Python 3.12, run from `backend/`:

```bash
cd backend
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium     # only needed for the apply flow
cp .env.example .env                      # add your GROQ_API_KEY
.venv/bin/uvicorn main:app --port 8000 --reload
```

**Frontend:**

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev                               # http://localhost:3000
```

## Configuration

| Variable | Where | Default | Notes |
|---|---|---|---|
| `GROQ_API_KEY` | `backend/.env` | *(none)* | Required. <https://console.groq.com/keys> |
| `GROQ_MODEL` | `backend/.env` | `openai/gpt-oss-120b` | Change when Groq retires one |
| `ALLOWED_ORIGINS` | `backend/.env` | `http://localhost:3000` | Comma-separated |
| `PORT` | `backend/.env` | `8000` | |
| `APPLY_HEADLESS` | `backend/.env` | `false` | Keep `false` locally: you answer flagged questions in the bot's window |
| `APPLY_SESSION_TTL` | `backend/.env` | `900` | Age in seconds after which an unconfirmed preview's browser is closed. Checked on the next apply or confirm call, not on a timer |
| `APPLY_CONFIRM_TIMEOUT` | `backend/.env` | `15` | Seconds to wait for a confirmation or error after submit |
| `NEXT_PUBLIC_API_URL` | `frontend/.env.local` | `http://localhost:8000` | |

## API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Liveness |
| `POST` | `/api/scrape` | Pull title, company and description from a job URL |
| `POST` | `/api/generate` | Tailored resume + cover letter + keyword diff |
| `POST` | `/api/answers` | Screening answers, with `needs_review` flags |
| `POST` | `/api/parse-resume` | Extract text from a PDF resume |
| `POST` | `/api/apply` | Fill the form; return a screenshot, `fields_filled` and `needs_input`. **Does not submit** |
| `POST` | `/api/apply/confirm` | Submit the previewed application and report `submitted` / `failed` / `unconfirmed` |
| `POST` | `/api/apply/cancel` | Close a previewed session's browser |
| `GET` | `/api/tracker/export` | Download the application log as .xlsx |

## Tests

```bash
cd backend
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

43 tests, no key and no outside network — Groq is stubbed throughout. The apply
tests need Chromium (`playwright install chromium`) and take about 45 seconds.

The substantive ones cover the eligibility guard: the stub deliberately returns
"Yes, I am authorized to work in the UK" so the tests prove the classifier
catches a *non-compliant* model rather than a well-behaved one. Also covered:
resume tailoring keeps factual details, the `CHANGES_JSON` trailer is stripped,
an unparseable model reply flags everything rather than mis-pairing answers to
questions, PDF parsing and its rejection paths, and a missing key returning 503
with instructions.

`tests/test_apply_flow.py` drives headless Chromium against HTML forms in
`tests/mock_forms/`, served on 127.0.0.1. It never contacts a job site. It checks:

- the preview lists exactly what was filled and what was left, and never submits
- eligibility labels, consent boxes, city and years of experience stay blank
- confirming with required answers missing returns `failed` and logs nothing, under both browser-side and script-side validation
- once the candidate answers in the browser, a retry returns `submitted` and logs exactly once
- a page that never confirms returns `unconfirmed` and logs nothing
- Workday-style paging stops at the Submit button
- the resume is a PDF whose text reads back
- cancel and expiry close the browser

Disabling the eligibility check or the validation check makes eight of these
tests fail.

## Status

Verified on 2026-09-07: the app runs under Python 3.12, all 8 routes serve,
`/api/generate` and `/api/answers` produce good output against the live Groq API
(resume tailoring preserved every date, GPA, and company name in the test
input), PDF parsing works, the tracker exports a real spreadsheet, and the
frontend builds under TypeScript.

**Apply flow, verified on 2026-09-14 against local mock forms only.** Two runs,
both against mock forms served on 127.0.0.1:

- **API run:** live Groq generated the resume, cover letter and screening answers, then `/api/apply` and `/api/apply/confirm` ran against the mock forms.
  - The simple form came back `submitted`, with one tracker row noting the page's confirmation text.
  - The full form came back `failed`, naming the five fields left for the candidate.
- **UI run:** the production frontend build was driven in a browser through upload, generate, Easy Apply and confirm. The modal showed the needs-input list and the retry error, and the browser tracker was updated only after the confirmed submission.

Still **not verified against any real job site.** The ATS navigation selectors
(Workday, Greenhouse, Lever, SmartRecruiters) and everything LinkedIn-specific
have never run against the live sites. LinkedIn needs a logged-in account, and
automating it breaches its terms. Before trusting either on a real application:

- Run against a job posting you are genuinely willing to apply to.
- Read the preview's "needs input" list and answer every item in the browser window.
- If confirm returns `unconfirmed`, check your email or the site before applying again.

Also outstanding: `/api/scrape` is unverified (it fetches live job pages), and
there is no deployment — Railway and Vercel both need a browser login.
