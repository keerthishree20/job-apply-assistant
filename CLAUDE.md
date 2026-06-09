# Job Apply Assistant — CLAUDE.md

## Project Overview
AI-powered job application automation tool for KeerthiShree TS (CS student, SNS College of Technology).
Paste a job URL → AI tailors resume + cover letter → Playwright bot auto-applies on LinkedIn / company portals → Excel tracker logs every application.

## Stack
- **Backend**: Python 3.11 + FastAPI + Playwright + Google Gemini 1.5 Flash (free tier)
- **Frontend**: Next.js 14 + TypeScript + Tailwind CSS v4
- **Storage**: localStorage (browser) + openpyxl Excel file (server)
- **Deploy**: Railway (backend) + Vercel (frontend)

## Key Rules
- AI model is **Gemini 1.5 Flash** via `google-generativeai` — NOT Claude/Anthropic (student, free tier only)
- Never commit `.env`, `backend/sessions/`, or `jobs_applied.xlsx` — all in `.gitignore`
- All Claude API calls in `services/claude_client.py` despite the filename — uses Gemini internally
- Bot fills form and shows screenshot preview — user must confirm before submitting
- Excel tracker appends one row per confirmed application in `jobs_applied.xlsx`

## Folder Structure
```
backend/
  main.py                    # FastAPI app entry point
  requirements.txt           # google-generativeai, playwright, fastapi, openpyxl
  .env.example               # GOOGLE_API_KEY, ALLOWED_ORIGINS, PORT
  routers/
    health.py                # GET /api/health
    scrape.py                # POST /api/scrape
    generate.py              # POST /api/generate
    answers.py               # POST /api/answers
    apply.py                 # POST /api/apply + POST /api/apply/confirm
    tracker.py               # GET /api/tracker/export
  services/
    scraper.py               # Per-site CSS selectors + ATS detection + fallback heuristic
    claude_client.py         # All Gemini API calls (resume, cover letter, Q&A)
    linkedin_bot.py          # Playwright LinkedIn Easy Apply bot
    ats_bot.py               # Playwright bot for Workday/Greenhouse/Lever/SmartRecruiters
    excel_tracker.py         # openpyxl: append row, create workbook, export
  schemas/
    models.py                # All Pydantic request/response models
  utils/
    text_cleaner.py          # Strip nav/footer boilerplate from scraped HTML

frontend/
  app/
    page.tsx                 # Main apply flow (step machine)
    profile/page.tsx         # Profile setup (fill once)
    tracker/page.tsx         # Application tracker Kanban board
    layout.tsx               # Sidebar nav
    globals.css              # Tailwind v4
    api/                     # Next.js route handlers proxying to FastAPI
  components/                # StepIndicator, ResumeEditor, DiffHighlight, etc.
  lib/
    api.ts                   # Typed fetch wrappers
    localStorage.ts          # jaa_resume, jaa_profile, jaa_applications
    types.ts                 # Shared TypeScript interfaces
```

## Running Locally
```bash
# Backend
cd backend
pip install -r requirements.txt
playwright install chromium
cp .env.example .env        # add your GOOGLE_API_KEY
python main.py

# Frontend
cd frontend
npm install
npm run dev
```

## API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | /api/health | Health check |
| POST | /api/scrape | Scrape job description from URL |
| POST | /api/generate | Tailor resume + generate cover letter |
| POST | /api/answers | Answer screening questions |
| POST | /api/apply | Fill form + screenshot preview |
| POST | /api/apply/confirm | Submit application + log to Excel |
| GET | /api/tracker/export | Download jobs_applied.xlsx |

## ATS Portal Support
Workday (`myworkdayjobs.com`), Greenhouse (`greenhouse.io`), Lever (`jobs.lever.co`), SmartRecruiters (`smartrecruiters.com`), iCIMS (`icims.com`), Taleo (`taleo.net`)

## Environment Variables
```
GOOGLE_API_KEY=AIza...        # Free from aistudio.google.com
ALLOWED_ORIGINS=http://localhost:3000
PORT=8000
```
