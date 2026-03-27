from __future__ import annotations

from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.mcp_store import store
from app.models import ApplicationData, ScrapeResult, SubmissionRequest
from app.openai_client import generate_scraper_job

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Data Analytics Server",
    description="Creates structured scraping jobs, stores results, and serves downstream application data.",
    version="0.1.0",
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"sample_url": "https://example.com/offers"},
    )


@app.post("/api/jobs/submit")
async def submit_job(submission: SubmissionRequest) -> dict[str, object]:
    job = generate_scraper_job(str(submission.target_url), submission.user_prompt)
    async with httpx.AsyncClient(timeout=120) as client:
        try:
            response = await client.post(f"{settings.scraper_service_url}/scrape", json=job.model_dump(mode="json"))
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Scraper service failed: {exc}") from exc

    scrape_result = ScrapeResult.model_validate(response.json())
    stored_record = store.store(job, scrape_result)
    return {
        "job": job.model_dump(mode="json"),
        "result": scrape_result.model_dump(mode="json"),
        "stored_at": stored_record.stored_at,
    }


@app.get("/api/records")
async def list_records() -> dict[str, object]:
    records = store.list_records()
    return {"records": [record.model_dump(mode="json") for record in records]}


@app.get("/api/application-data", response_model=ApplicationData)
async def application_data() -> ApplicationData:
    return store.build_application_data()
