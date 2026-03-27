from fastapi import FastAPI, HTTPException

from app.models import ScrapeResult, ScraperJob
from app.scraper import ScrapeEmptyError, run_scrape

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
    try:
        return await run_scrape(job)
    except ScrapeEmptyError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "no_relevant_content",
                "message": str(exc),
                "diagnostics": exc.diagnostics,
            },
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "scraper_internal_error",
                "message": str(exc) or exc.__class__.__name__,
                "exception_type": exc.__class__.__name__,
            },
        ) from exc
