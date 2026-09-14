import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

BACKEND_DIR = Path(__file__).resolve().parent

# Anchored to this file rather than the working directory, so the .env is found
# no matter where uvicorn is launched from.
load_dotenv(BACKEND_DIR / ".env")

from routers import health, scrape, generate, answers, apply, tracker, resume
from services.llm_client import LLMUnavailable


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # Open apply sessions each hold a Chromium process; don't leak them on shutdown.
    await apply.close_all_sessions()


app = FastAPI(title="Job Apply Assistant API", version="1.0.0", lifespan=lifespan)


@app.exception_handler(LLMUnavailable)
async def _llm_unavailable(request: Request, exc: LLMUnavailable) -> JSONResponse:
    """A missing key or a retired model is a configuration problem, not a crash.

    503 with the message, rather than a 500 and a traceback the user can't act on.
    """
    return JSONResponse(status_code=503, content={"detail": str(exc)})

origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(scrape.router)
app.include_router(generate.router)
app.include_router(answers.router)
app.include_router(apply.router)
app.include_router(tracker.router)
app.include_router(resume.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)
