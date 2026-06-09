# Job Apply Assistant

An AI-powered tool that automates the entire job application process — from reading the job description to submitting the application.

## What it does

1. **Paste a job URL** (LinkedIn, Naukri, Indeed, Internshala, or any company portal)
2. **AI reads the JD** and tailors your resume to match it with keyword highlights
3. **AI writes a cover letter** (250 words, no fluff)
4. **AI answers screening questions** based on your resume
5. **Bot auto-applies** — fills the form, uploads your resume, submits
6. **Excel tracker** logs every application automatically

## Tech Stack

| Layer | Tech |
|-------|------|
| Backend | Python · FastAPI · Playwright |
| AI | Google Gemini 1.5 Flash (free) |
| Frontend | Next.js 14 · TypeScript · Tailwind CSS |
| Automation | Playwright (LinkedIn Easy Apply + ATS portals) |
| Tracking | openpyxl Excel file |

## Supported Job Portals

- **Job Boards**: LinkedIn, Naukri, Indeed, Internshala
- **ATS Portals**: Workday, Greenhouse, Lever, SmartRecruiters, iCIMS, Taleo
- **Any company website** — fallback heuristic scraping

## Setup

### 1. Get a free Gemini API key
Go to [aistudio.google.com](https://aistudio.google.com) → Sign in → Get API key → Copy it.

### 2. Backend
```bash
cd backend
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
# Add your GOOGLE_API_KEY in .env
python main.py
```

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## How to Use

1. Go to **Profile** tab → fill your name, email, phone, LinkedIn, GitHub once
2. Paste your base resume in the text area (saved automatically)
3. Paste a job URL → click **Generate**
4. Review the tailored resume with green diff highlights
5. Click **Easy Apply** → bot opens browser, fills form, shows preview
6. Click **Confirm** → application submitted + logged to Excel

## Cost

**100% free** — Gemini 1.5 Flash gives 1 million tokens/day free. That's ~300+ job applications per day at zero cost.

## Project Structure

```
job-apply-assistant/
  backend/
    main.py              # FastAPI entry point
    requirements.txt
    routers/             # scrape, generate, answers, apply, tracker
    services/            # Gemini AI client, Playwright bots, Excel tracker
    schemas/             # Pydantic models
    utils/               # HTML text cleaner
  frontend/
    app/                 # Next.js pages
    components/          # UI components
    lib/                 # API helpers, localStorage, types
```

## GitHub
[github.com/keerthishree20/job-apply-assistant](https://github.com/keerthishree20/job-apply-assistant)
