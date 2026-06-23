<p align="center">
  <h1 align="center">💼 Job Apply Assistant</h1>
  <p align="center">AI-powered job application automation — tailors your resume, writes cover letters, answers screening questions, and auto-applies via browser bots.</p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Next.js-16-black?style=for-the-badge&logo=next.js" />
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Groq_Llama_3.3-FF6B35?style=for-the-badge&logo=meta&logoColor=white" />
  <img src="https://img.shields.io/badge/Playwright-2EAD33?style=for-the-badge&logo=playwright&logoColor=white" />
  <img src="https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white" />
  <img src="https://img.shields.io/badge/Tailwind_CSS-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white" />
</p>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📄 **Resume Tailoring** | AI rewrites your resume with ATS-optimized keywords matching the job description |
| ✉️ **Cover Letter Generation** | Generates concise, no-fluff cover letters (220 words max) |
| ❓ **Screening Q&A** | Auto-answers common screening questions (notice period, salary, experience) |
| 🔍 **Job Scraping** | Scrapes job descriptions from 10+ portals with site-specific selectors |
| 🤖 **LinkedIn Easy Apply Bot** | Playwright bot handles multi-page LinkedIn application forms |
| 🏢 **ATS Portal Bot** | Auto-fills Workday, Greenhouse, Lever, SmartRecruiters, iCIMS, Taleo |
| 📸 **Screenshot Preview** | See a preview of the filled form before confirming submission |
| 📊 **Application Tracker** | Kanban board + downloadable Excel tracker for all applications |
| 🔄 **Resume Diff View** | Side-by-side comparison with green highlights showing AI changes |
| 📥 **PDF Export** | Download tailored resume and cover letter as PDF |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Next.js 16, React 19, TypeScript, Tailwind CSS v4 |
| **Backend** | Python, FastAPI, Uvicorn |
| **AI Model** | Groq API — Llama 3.3 70B Versatile (free tier) |
| **Browser Automation** | Playwright (Chromium) |
| **PDF Parsing** | pypdf |
| **Job Scraping** | httpx + BeautifulSoup4 |
| **Tracking** | openpyxl (Excel) + localStorage (Kanban) |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- Node.js 18+
- Free Groq API key from [console.groq.com](https://console.groq.com)

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
# Add your GROQ_API_KEY in .env
python main.py
# Runs on http://localhost:8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:3000
```

---

## 🔑 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes | Free from [console.groq.com](https://console.groq.com) |
| `ALLOWED_ORIGINS` | No | CORS origins (defaults to localhost) |
| `PORT` | No | Backend port (defaults to 8000) |
| `NEXT_PUBLIC_API_URL` | No | Backend URL (defaults to http://localhost:8000) |

---

## 📋 How It Works

```
1. Profile Setup  →  Fill name, email, phone, LinkedIn, GitHub (saved locally)
2. Upload Resume  →  Drag & drop your PDF resume
3. Paste Job URL  →  LinkedIn, Naukri, Indeed, Internshala, or any company portal
4. AI Generate    →  Tailored resume + cover letter + screening answers (~10 sec)
5. Review         →  Check diff view, download PDFs if needed
6. Easy Apply     →  Bot opens browser, fills the actual application form
7. Preview        →  Screenshot of filled form for your approval
8. Confirm        →  Submit & auto-log to Excel tracker + Kanban board
```

---

## 🌐 Supported Job Portals

**Job Boards:** LinkedIn, Naukri, Indeed, Internshala

**ATS Portals:** Workday, Greenhouse, Lever, SmartRecruiters, iCIMS, Taleo

**Any other URL:** Fallback heuristic scraping extracts the job description automatically.

---

## 📁 Project Structure

```
job-apply-assistant/
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── routers/             # API route handlers
│   │   ├── scrape.py        # Job description scraping
│   │   ├── generate.py      # AI resume + cover letter
│   │   ├── answers.py       # AI screening answers
│   │   ├── apply.py         # Browser bot apply + confirm
│   │   ├── tracker.py       # Excel export
│   │   └── resume.py        # PDF parsing
│   ├── services/
│   │   ├── claude_client.py # AI client (Groq Llama 3.3)
│   │   ├── scraper.py       # Per-site job scraping
│   │   ├── linkedin_bot.py  # LinkedIn Easy Apply bot
│   │   ├── ats_bot.py       # ATS portal bot
│   │   └── excel_tracker.py # Application logging
│   └── schemas/
│       └── models.py        # Pydantic models
├── frontend/
│   ├── app/
│   │   ├── page.tsx         # Main apply flow (step wizard)
│   │   ├── profile/         # Profile setup
│   │   └── tracker/         # Kanban board
│   ├── components/          # UI components
│   └── lib/                 # API client + types
└── README.md
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/parse-resume` | Extract text from PDF |
| POST | `/api/scrape` | Scrape job description from URL |
| POST | `/api/generate` | AI-tailor resume + cover letter |
| POST | `/api/answers` | AI-answer screening questions |
| POST | `/api/apply` | Bot fills form, returns screenshot |
| POST | `/api/apply/confirm` | Confirm & submit application |
| GET | `/api/tracker/export` | Download Excel tracker |

---

## 📝 Notes

- Bot runs in **visible mode** (non-headless) so you can watch the automation
- LinkedIn login requires manual sign-in on first use — session is saved for reuse
- Groq API free tier is sufficient for personal use
- All applications are logged to `jobs_applied.xlsx` on the server

---

<p align="center">
  Built with ❤️ by <a href="https://github.com/keerthishree20">KeerthiShree TS</a>
</p>
