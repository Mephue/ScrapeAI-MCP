from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class ExpectedOutput(BaseModel):
    format: str = "json"
    fields: list[str] = Field(default_factory=list)


class ScraperJob(BaseModel):
    job_id: str
    target_url: HttpUrl
    user_intent: str
    keywords: list[str] = Field(default_factory=list)
    extraction_instructions: list[str] = Field(default_factory=list)
    expected_output: ExpectedOutput


class ScrapeMatch(BaseModel):
    text: str
    matched_keywords: list[str] = Field(default_factory=list)
    relevance_score: float


class ScrapeResult(BaseModel):
    job_id: str
    source_url: HttpUrl
    scraped_at: datetime
    page_title: str
    matches: list[ScrapeMatch] = Field(default_factory=list)
    diagnostics: dict[str, Any] = Field(default_factory=dict)

