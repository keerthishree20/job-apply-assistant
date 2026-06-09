from fastapi import APIRouter
from schemas.models import ScrapeRequest, ScrapeResponse, ScrapeError
from services.scraper import scrape_job

router = APIRouter()


@router.post("/api/scrape")
async def scrape(req: ScrapeRequest):
    result = await scrape_job(req.url)
    if "error" in result:
        return ScrapeError(**result)
    return ScrapeResponse(**result)
