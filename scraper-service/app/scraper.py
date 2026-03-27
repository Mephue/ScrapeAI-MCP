from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Iterable

from bs4 import BeautifulSoup
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from app.models import ScrapeMatch, ScrapeResult, ScraperJob


def _normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def _extract_candidate_blocks(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    blocks: list[str] = []
    selectors = [
        "article",
        "section",
        "main",
        "li",
        "div",
        "p",
        "span",
    ]
    for selector in selectors:
        for node in soup.select(selector):
            text = _normalize_whitespace(node.get_text(" ", strip=True))
            if len(text) >= 30:
                blocks.append(text)
    seen: set[str] = set()
    unique_blocks: list[str] = []
    for block in blocks:
        if block not in seen:
            seen.add(block)
            unique_blocks.append(block)
    return unique_blocks


def _score_block(text: str, keywords: Iterable[str]) -> ScrapeMatch | None:
    lowered_text = text.lower()
    matched_keywords = [keyword for keyword in keywords if keyword.lower() in lowered_text]
    if not matched_keywords:
        return None
    keyword_counts = Counter(keyword.lower() for keyword in matched_keywords)
    score = min(1.0, 0.35 + (sum(keyword_counts.values()) * 0.12))
    return ScrapeMatch(
        text=text,
        matched_keywords=sorted(set(matched_keywords)),
        relevance_score=round(score, 2),
    )


async def run_scrape(job: ScraperJob) -> ScrapeResult:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 1600})
        await page.goto(str(job.target_url), wait_until="domcontentloaded", timeout=90000)
        try:
            await page.wait_for_load_state("networkidle", timeout=15000)
        except PlaywrightTimeoutError:
            pass
        page_title = await page.title()
        await page.mouse.wheel(0, 2000)
        await page.wait_for_timeout(500)
        html = await page.content()
        visible_text = _normalize_whitespace(await page.locator("body").inner_text())
        await browser.close()

    blocks = _extract_candidate_blocks(html)
    if visible_text:
        blocks.append(visible_text)

    scored_matches = [_score_block(block, job.keywords) for block in blocks]
    matches = [match for match in scored_matches if match is not None]
    matches.sort(key=lambda item: item.relevance_score, reverse=True)

    return ScrapeResult(
        job_id=job.job_id,
        source_url=job.target_url,
        scraped_at=datetime.now(UTC),
        page_title=page_title,
        matches=matches[:20],
        diagnostics={
            "candidate_block_count": len(blocks),
            "keyword_count": len(job.keywords),
            "instructions": job.extraction_instructions,
        },
    )

