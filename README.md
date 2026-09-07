# Job Apply Assistant

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
| `NEXT_PUBLIC_API_URL` | `frontend/.env.local` | `http://localhost:8000` | |

## API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Liveness |
| `POST` | `/api/scrape` | Pull title, company and description from a job URL |
| `POST` | `/api/generate` | Tailored resume + cover letter + keyword diff |
| `POST` | `/api/answers` | Screening answers, with `needs_review` flags |
| `POST` | `/api/parse-resume` | Extract text from a PDF resume |
| `POST` | `/api/apply` | Fill the form, return a screenshot — **does not submit** |
| `POST` | `/api/apply/confirm` | Submit the application you just previewed |
| `GET` | `/api/tracker/export` | Download the application log as .xlsx |

## Tests

```bash
cd backend
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

21 tests, no key and no network — Groq is stubbed throughout.

The substantive ones cover the eligibility guard: the stub deliberately returns
"Yes, I am authorized to work in the UK" so the tests prove the classifier
catches a *non-compliant* model rather than a well-behaved one. Also covered:
resume tailoring keeps factual details, the `CHANGES_JSON` trailer is stripped,
an unparseable model reply flags everything rather than mis-pairing answers to
questions, PDF parsing and its rejection paths, and a missing key returning 503
with instructions.

## Status

Verified on 2026-09-07: the app runs under Python 3.12, all 8 routes serve,
`/api/generate` and `/api/answers` produce good output against the live Groq API
(resume tailoring preserved every date, GPA, and company name in the test
input), PDF parsing works, the tracker exports a real spreadsheet, and the
frontend builds under TypeScript.

**Not verified — the Playwright apply flow.** `services/ats_bot.py` and
`linkedin_bot.py` drive real job sites and submit real applications to real
employers. They were deliberately not exercised. Before trusting them:

- Run against a job posting you are genuinely willing to apply to.
- Watch the screenshot preview carefully — it is the last checkpoint.
- Check that every `needs_review` answer has been filled in by you.

Also outstanding: `/api/scrape` is unverified (it fetches live job pages), and
there is no deployment — Railway and Vercel both need a browser login.
