from __future__ import annotations

import os
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
DEBUG_DIR = Path(os.getenv("SCRAPER_DEBUG_DIR", "/data/scraper-debug"))
DEBUG_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Data Analytics Server",
    description="Creates structured scraping jobs, stores results, and serves downstream application data.",
    version="0.1.0",
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.mount("/debug-assets", StaticFiles(directory=DEBUG_DIR), name="debug-assets")
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
    async with httpx.AsyncClient(timeout=300) as client:
        try:
            response = await client.post(f"{settings.scraper_service_url}/scrape", json=job.model_dump(mode="json"))
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail: object
            try:
                detail = exc.response.json()
            except ValueError:
                detail = exc.response.text
            diagnostics = None
            if isinstance(detail, dict):
                nested_detail = detail.get("detail")
                if isinstance(nested_detail, dict):
                    diagnostics = nested_detail.get("diagnostics")
                    screenshot_path = nested_detail.get("diagnostics", {}).get("debug_screenshot") if isinstance(nested_detail.get("diagnostics"), dict) else None
                    screenshot_files = nested_detail.get("diagnostics", {}).get("debug_screenshot_files") if isinstance(nested_detail.get("diagnostics"), dict) else []
                    if isinstance(screenshot_path, str) and screenshot_path:
                        nested_detail["diagnostics"]["debug_screenshot_url"] = f"/debug-assets/{Path(screenshot_path).name}"
                    if isinstance(screenshot_files, list):
                        nested_detail["diagnostics"]["debug_screenshot_file_urls"] = [
                            f"/debug-assets/{Path(path).name}" for path in screenshot_files if isinstance(path, str) and path
                        ]
            raise HTTPException(
                status_code=exc.response.status_code,
                detail={
                    "error": "scraper_failed",
                    "message": "The scraper could not extract usable content from the target page.",
                    "scraper_detail": detail,
                },
            ) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "error": "scraper_transport_error",
                    "message": str(exc) or exc.__class__.__name__,
                    "exception_type": exc.__class__.__name__,
                },
            ) from exc

    scrape_result = ScrapeResult.model_validate(response.json())
    screenshot_path = scrape_result.diagnostics.get("debug_screenshot")
    if isinstance(screenshot_path, str) and screenshot_path:
        scrape_result.diagnostics["debug_screenshot_url"] = f"/debug-assets/{Path(screenshot_path).name}"
    screenshot_files = scrape_result.diagnostics.get("debug_screenshot_files", [])
    if isinstance(screenshot_files, list):
        scrape_result.diagnostics["debug_screenshot_file_urls"] = [
            f"/debug-assets/{Path(path).name}" for path in screenshot_files if isinstance(path, str) and path
        ]
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
