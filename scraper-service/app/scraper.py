from __future__ import annotations

import asyncio
import base64
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from openai import OpenAI
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from app.models import ScrapeMatch, ScrapeResult, ScraperJob


class ScrapeEmptyError(Exception):
    def __init__(self, message: str, diagnostics: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.diagnostics = diagnostics or {}


def _normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def _retailer_focus(target_url: str) -> str | None:
    query = parse_qs(urlparse(target_url).query)
    for key in ("retailerName", "sourceValue", "retailer", "merchant"):
        value = query.get(key, [])
        if value and value[0].strip():
            return value[0].strip()
    return None


async def _dismiss_common_banners(page) -> None:
    for pattern in (
        re.compile(r"akzeptieren|zustimmen|accept|agree", re.IGNORECASE),
        re.compile(r"alle akzeptieren|accept all", re.IGNORECASE),
    ):
        try:
            button = page.get_by_role("button", name=pattern).first
            if await button.count():
                await button.click(timeout=2000)
                await page.wait_for_timeout(400)
        except Exception:
            continue


async def _capture_debug_screenshot(page, job_id: str) -> str | None:
    try:
        base_dir = Path(os.getenv("SCRAPER_DEBUG_DIR", "/data/scraper-debug"))
        base_dir.mkdir(parents=True, exist_ok=True)
        destination = base_dir / f"{job_id}-full-page.png"
        await page.screenshot(path=str(destination), full_page=True)
        return str(destination)
    except Exception:
        return None


async def _capture_segment_screenshots(page, job_id: str) -> tuple[list[bytes], list[str]]:
    base_dir = Path(os.getenv("SCRAPER_DEBUG_DIR", "/data/scraper-debug"))
    base_dir.mkdir(parents=True, exist_ok=True)

    viewport_height = page.viewport_size["height"] if page.viewport_size else 1600
    scroll_height = await page.evaluate(
        "() => Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)"
    )
    screenshot_positions: list[int] = []
    step = max(int(viewport_height * 0.85), 900)
    current = 0
    while current < scroll_height and len(screenshot_positions) < 5:
        screenshot_positions.append(current)
        current += step
    if not screenshot_positions:
        screenshot_positions = [0]

    image_bytes: list[bytes] = []
    image_paths: list[str] = []
    for index, position in enumerate(screenshot_positions, start=1):
        await page.evaluate("position => window.scrollTo(0, position)", position)
        await page.wait_for_timeout(900)
        path = base_dir / f"{job_id}-segment-{index}.png"
        await page.screenshot(path=str(path), full_page=False)
        image_paths.append(str(path))
        image_bytes.append(path.read_bytes())
    return image_bytes, image_paths


def _keyword_hits(text: str, keywords: list[str]) -> list[str]:
    lowered = text.lower()
    hits: list[str] = []
    for keyword in keywords:
        lowered_keyword = keyword.lower()
        alias_group = next((aliases for aliases in KEYWORD_ALIASES.values() if lowered_keyword in aliases), {lowered_keyword})
        if any(alias in lowered for alias in alias_group):
            hits.append(keyword)
    return sorted(set(hits))


def _score_offer(offer: dict[str, str], keywords: list[str]) -> float:
    score = 0.45
    if offer.get("product_name"):
        score += 0.2
    if offer.get("price"):
        score += 0.2
    if offer.get("discount"):
        score += 0.08
    if offer.get("validity"):
        score += 0.05
    if _keyword_hits(" ".join(str(value) for value in offer.values()), keywords):
        score += 0.04
    return round(min(score, 1.0), 2)


def _offer_to_text(offer: dict[str, str]) -> str:
    parts = [
        offer.get("product_name", ""),
        offer.get("price", ""),
        offer.get("discount", ""),
        offer.get("validity", ""),
        f"retailer: {offer['retailer']}" if offer.get("retailer") else "",
    ]
    return _normalize_whitespace(" | ".join(part for part in parts if part))


def _extract_offers_from_openai(
    image_bytes_list: list[bytes],
    user_intent: str,
    keywords: list[str],
    retailer_focus: str | None,
) -> tuple[list[dict[str, str]], str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ScrapeEmptyError("OPENAI_API_KEY is not configured for screenshot-to-text extraction.")

    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_VISION_MODEL", "gpt-4.1-mini")

    user_content: list[dict[str, str]] = [
        {
            "type": "input_text",
            "text": (
                f"User intent: {user_intent}\n"
                f"Retailer hint: {retailer_focus or 'unknown'}\n"
                f"Keywords: {', '.join(keywords)}\n"
                "Read all screenshots and translate the flyer into structured text."
            ),
        }
    ]
    for image_bytes in image_bytes_list:
        encoded = base64.b64encode(image_bytes).decode("utf-8")
        user_content.append(
            {
                "type": "input_image",
                "image_url": f"data:image/png;base64,{encoded}",
            }
        )

    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "You are extracting data from flyer screenshots. "
                            "Return JSON only with a top-level key named offers. "
                            "Each offer must be an object with keys: "
                            "product_name, price, discount, validity, retailer, source_text. "
                            "Use empty strings for missing fields. "
                            "Only include real visible offers from the flyer."
                        ),
                    }
                ],
            },
            {
                "role": "user",
                "content": user_content,
            },
        ],
        text={"format": {"type": "json_object"}},
    )

    raw_response = response.output_text[:12000]
    try:
        payload = json.loads(response.output_text)
    except json.JSONDecodeError as exc:
        raise ScrapeEmptyError(
            "OpenAI Vision returned a non-JSON response for the flyer screenshots.",
            diagnostics={"vision_raw_response": raw_response, "exception_type": exc.__class__.__name__},
        ) from exc

    offers = payload.get("offers", [])
    if not isinstance(offers, list):
        raise ScrapeEmptyError(
            "OpenAI Vision did not return an offers list.",
            diagnostics={"vision_raw_response": raw_response},
        )

    normalized_offers: list[dict[str, str]] = []
    for offer in offers:
        if not isinstance(offer, dict):
            continue
        normalized_offer = {
            "product_name": _normalize_whitespace(str(offer.get("product_name", ""))),
            "price": _normalize_whitespace(str(offer.get("price", ""))),
            "discount": _normalize_whitespace(str(offer.get("discount", ""))),
            "validity": _normalize_whitespace(str(offer.get("validity", ""))),
            "retailer": _normalize_whitespace(str(offer.get("retailer", retailer_focus or ""))),
            "source_text": _normalize_whitespace(str(offer.get("source_text", ""))),
        }
        if normalized_offer["product_name"] or normalized_offer["price"] or normalized_offer["source_text"]:
            normalized_offers.append(normalized_offer)

    return normalized_offers, raw_response


async def run_scrape(job: ScraperJob) -> ScrapeResult:
    retailer_focus = _retailer_focus(str(job.target_url))
    keywords = sorted(set(job.keywords + [keyword for keyword in job.user_intent.split() if len(keyword) > 2]))

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 1800},
            locale="de-DE",
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/135.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()
        await page.set_extra_http_headers({"Accept-Language": "de-DE,de;q=0.9,en;q=0.8"})

        try:
            await page.goto(str(job.target_url), wait_until="domcontentloaded", timeout=90000)
            await _dismiss_common_banners(page)
            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
            except PlaywrightTimeoutError:
                pass
            await page.wait_for_timeout(1800)
            page_title = await page.title()
            debug_screenshot = await _capture_debug_screenshot(page, job.job_id)
            screenshot_bytes, screenshot_paths = await _capture_segment_screenshots(page, job.job_id)
        finally:
            await context.close()
            await browser.close()

    offers, raw_response = await asyncio.to_thread(
        _extract_offers_from_openai,
        screenshot_bytes,
        job.user_intent,
        keywords,
        retailer_focus,
    )

    matches = [
        ScrapeMatch(
            text=_offer_to_text(offer),
            matched_keywords=_keyword_hits(" ".join(offer.values()), keywords),
            relevance_score=_score_offer(offer, keywords),
        )
        for offer in offers
        if _offer_to_text(offer)
    ]
    matches.sort(key=lambda item: item.relevance_score, reverse=True)

    diagnostics = {
        "workflow": "render -> screenshots -> openai vision -> structured offers",
        "retailer_focus": retailer_focus,
        "screenshot_count": len(screenshot_paths),
        "debug_screenshot": debug_screenshot,
        "debug_screenshot_files": screenshot_paths,
        "page_vision_offer_count": len(offers),
        "vision_raw_response": raw_response,
        "vision_parsed_offers": offers[:20],
    }

    if not matches:
        raise ScrapeEmptyError(
            "OpenAI Vision could not extract any offers from the captured screenshots.",
            diagnostics=diagnostics,
        )

    return ScrapeResult(
        job_id=job.job_id,
        source_url=job.target_url,
        scraped_at=datetime.now(UTC),
        page_title=page_title,
        matches=matches[:20],
        diagnostics=diagnostics,
    )
KEYWORD_ALIASES = {
    "price": {"preis", "preise", "price", "prices"},
    "offer": {"angebot", "angebote", "offer", "offers", "prospekt", "flyer"},
    "discount": {"rabatt", "aktion", "discount", "sale", "deal"},
    "validity": {"gueltig", "gültig", "validity", "valid", "ab", "bis"},
    "product": {"produkt", "produkte", "product", "products", "artikel"},
}
