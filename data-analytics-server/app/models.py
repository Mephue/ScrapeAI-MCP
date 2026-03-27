from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, HttpUrl


class SubmissionRequest(BaseModel):
    target_url: HttpUrl
    user_prompt: str = Field(min_length=10)


class ExpectedOutput(BaseModel):
    format: str = "json"
    fields: list[str] = Field(default_factory=list)


class ScraperJob(BaseModel):
    job_id: str = Field(default_factory=lambda: f"job-{uuid4().hex[:12]}")
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


class StoredRecord(BaseModel):
    job: ScraperJob
    result: ScrapeResult
    stored_at: datetime


class OfferCard(BaseModel):
    title: str
    summary: str
    price_hint: str
    source_url: str
    matched_keywords: list[str]


class FuelStationPrice(BaseModel):
    station_name: str
    location: str
    e5_price: float
    e10_price: float
    diesel_price: float
    updated_at: datetime


class ApplicationData(BaseModel):
    supermarket_offers: list[OfferCard]
    fuel_prices: list[FuelStationPrice]
    generated_at: datetime

