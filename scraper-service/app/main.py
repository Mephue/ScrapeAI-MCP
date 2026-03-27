from fastapi import FastAPI, HTTPException

from app.models import ScrapeResult, ScraperJob
from app.scraper import run_scrape

app = FastAPI(
    title="Scraper Service",
    description="Executes structured scraping jobs, including JavaScript-rendered pages.",
    version="0.1.0",
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/scrape", response_model=ScrapeResult)
async def scrape(job: ScraperJob) -> ScrapeResult:
    if not job.keywords:
        raise HTTPException(status_code=400, detail="At least one keyword is required.")
    return await run_scrape(job)
