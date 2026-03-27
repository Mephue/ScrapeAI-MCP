from __future__ import annotations

import asyncio
import base64
import json
import os
import re
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from openai import OpenAI
from PIL import Image
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from app.models import ScrapeMatch, ScrapeResult, ScraperJob

KEYWORD_ALIASES = {
    "price": {"preis", "preise", "price", "prices"},
    "offer": {"angebot", "angebote", "offer", "offers", "prospekt", "flyer"},
    "discount": {"rabatt", "aktion", "discount", "sale", "deal"},
    "validity": {"gueltig", "gültig", "validity", "valid", "ab", "bis"},
    "product": {"produkt", "produkte", "product", "products", "artikel"},
}
PRICE_REGEX = re.compile(r"(?:€\s?\d{1,3}[.,]\d{2}|\d{1,3}[.,]\d{2}\s?(?:€|eur)?)", re.IGNORECASE)


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


async def _accept_cookie_modal(page) -> bool:
    selectors = (
        'button#accept[data-action="consent"][data-action-type="accept"]',
        'button.uc-accept-button#accept',
        '#uc-center-container button:has-text("Akzeptiere alle")',
        '#uc-center-container button:has-text("Alle akzeptieren")',
        '#uc-center-container button[data-testid*="accept"]',
        '[data-testid="uc-accept-all-button"]',
        '[id^="uc-"] button:has-text("Akzeptiere alle")',
        '[class*="uc-"] button:has-text("Akzeptiere alle")',
        'button:has-text("Akzeptiere alle")',
        'button:has-text("Alle akzeptieren")',
        'button:has-text("Accept all")',
        'button:has-text("Akzeptieren")',
        'button:has-text("Zustimmen")',
        '[data-testid*="consent"] button',
        '[id*="consent"] button',
        '[class*="consent"] button',
        '[aria-label*="consent" i] button',
    )
    for frame in page.frames:
        for selector in selectors:
            try:
                button = frame.locator(selector).first
                if await button.count() and await button.is_visible(timeout=1000):
                    await button.scroll_into_view_if_needed(timeout=1000)
                    await button.click(timeout=3000, force=True)
                    await page.wait_for_timeout(1500)
                    return True
            except Exception:
                continue

        try:
            clicked = await frame.evaluate(
                """
                () => {
                  const exactButton = document.querySelector('button#accept[data-action="consent"][data-action-type="accept"]');
                  if (!exactButton) return false;
                  exactButton.click();
                  return true;
                }
                """
            )
            if clicked:
                await page.wait_for_timeout(1500)
                return True
        except Exception:
            continue

        try:
            clicked = await frame.evaluate(
                """
                () => {
                  const candidates = Array.from(document.querySelectorAll('button, [role="button"], a, div, span'));
                  const target = candidates.find((element) => {
                    const text = element.textContent?.trim().toLowerCase() || '';
                    return ['akzeptiere alle', 'alle akzeptieren', 'accept all', 'akzeptieren', 'zustimmen']
                      .some((label) => text === label || text.includes(label));
                  });
                  if (!target) return false;
                  target.click();
                  return true;
                }
                """
            )
            if clicked:
                await page.wait_for_timeout(1500)
                return True
        except Exception:
            continue

        try:
            clicked = await frame.evaluate(
                """
                () => {
                  const labels = ['akzeptiere alle', 'alle akzeptieren', 'accept all', 'akzeptieren', 'zustimmen'];
                  const candidates = Array.from(document.querySelectorAll('button, [role="button"], input[type="button"], input[type="submit"]'));
                  const visible = candidates.filter((element) => {
                    const style = window.getComputedStyle(element);
                    const rect = element.getBoundingClientRect();
                    return style.visibility !== 'hidden' && style.display !== 'none' && rect.width > 40 && rect.height > 20;
                  });

                  const exactTextMatch = visible.find((element) => {
                    const text = (element.textContent || element.value || '').trim().toLowerCase();
                    return labels.some((label) => text === label || text.includes(label));
                  });
                  if (exactTextMatch) {
                    exactTextMatch.click();
                    return true;
                  }

                  const greenButton = visible.find((element) => {
                    const style = window.getComputedStyle(element);
                    const bg = style.backgroundColor || '';
                    return /rgb\\((?:\\d+,\\s*){2}\\d+\\)/.test(bg) && /0,\\s*175|34,\\s*197|46,\\s*204|63,\\s*186/i.test(bg);
                  });
                  if (greenButton) {
                    greenButton.click();
                    return true;
                  }

                  return false;
                }
                """
            )
            if clicked:
                await page.wait_for_timeout(1500)
                return True
        except Exception:
            continue
    return False


async def _close_blocking_overlays(page) -> bool:
    closed = False
    selectors = (
        'button[aria-label*="close" i]',
        'button[aria-label*="schließen" i]',
        '[role="dialog"] button:has-text("×")',
        '[role="dialog"] button:has-text("✕")',
        '[role="dialog"] button:has-text("Schließen")',
        '[role="dialog"] button:has-text("Close")',
        'button:has-text("Später")',
        'button:has-text("Nein danke")',
        '[data-testid*="close"]',
        '[class*="close"]',
    )
    for frame in page.frames:
        for selector in selectors:
            try:
                button = frame.locator(selector).first
                if await button.count() and await button.is_visible(timeout=800):
                    await button.click(timeout=2000, force=True)
                    await page.wait_for_timeout(500)
                    closed = True
            except Exception:
                continue

        try:
            clicked = await frame.evaluate(
                """
                () => {
                  const candidates = Array.from(document.querySelectorAll('button, [role="button"], div, span'));
                  const target = candidates.find((element) => {
                    const text = element.textContent?.trim() || '';
                    const aria = element.getAttribute('aria-label') || '';
                    return text === '×' || text === '✕' || /close|schließen/i.test(text) || /close|schließen/i.test(aria);
                  });
                  if (!target) return false;
                  target.click();
                  return true;
                }
                """
            )
            if clicked:
                await page.wait_for_timeout(500)
                closed = True
            continue
        except Exception:
            continue
    return closed


async def _open_angebote_view(page) -> bool:
    selectors = (
        '[data-testid="tabs"] button:has-text("Angebote")',
        '[data-testid="tabs"] *:has-text("Angebote")',
        'button:has-text("Angebote")',
        '[role="tab"]:has-text("Angebote")',
        'a:has-text("Angebote")',
        'text="Angebote"',
    )
    for selector in selectors:
        try:
            target = page.locator(selector).first
            if await target.count() and await target.is_visible(timeout=1500):
                await target.click(timeout=3000, force=True)
                await page.wait_for_timeout(1600)
                return True
        except Exception:
            continue

    try:
        clicked = await page.evaluate(
            """
            () => {
              const elements = Array.from(document.querySelectorAll('button, a, [role="tab"], div, span'));
              const match = elements.find((element) => element.textContent?.trim() === 'Angebote');
              if (!match) return false;
              const clickable = match.closest('button, a, [role="tab"], [tabindex]') || match;
              clickable.click();
              return true;
            }
            """
        )
        if clicked:
            await page.wait_for_timeout(1600)
            return True
    except Exception:
        pass

    return False


async def _prepare_offer_view(page) -> dict[str, object]:
    diagnostics: dict[str, object] = {
        "cookie_accepted": False,
        "overlay_closed": False,
        "angebote_clicked": False,
    }

    diagnostics["cookie_accepted"] = await _accept_cookie_modal(page)
    diagnostics["overlay_closed"] = await _close_blocking_overlays(page)
    diagnostics["angebote_clicked"] = await _open_angebote_view(page)
    if not diagnostics["angebote_clicked"]:
        diagnostics["overlay_closed"] = await _close_blocking_overlays(page) or bool(diagnostics["overlay_closed"])
        diagnostics["angebote_clicked"] = await _open_angebote_view(page)

    if diagnostics["angebote_clicked"]:
        for selector in (
            '[data-testid="premium-panel-offers"]',
            '[href*="productId"]',
            'text="UVP"',
        ):
            try:
                await page.locator(selector).first.wait_for(state="visible", timeout=8000)
                diagnostics["matched_offer_selector"] = selector
                break
            except Exception:
                continue

    await page.wait_for_timeout(1200)
    return diagnostics


async def _load_full_offer_listing(page) -> dict[str, object]:
    diagnostics: dict[str, object] = {"preload_scroll_steps": 0, "scroll_growth_iterations": 0}
    try:
        total_height = await page.evaluate("() => document.body.scrollHeight")
    except Exception:
        return diagnostics

    viewport_height = 1400
    current = 0
    stabilized_iterations = 0
    max_iterations = 120
    previous_total_height = total_height

    while diagnostics["preload_scroll_steps"] < max_iterations:
        try:
            await page.evaluate("(y) => window.scrollTo(0, y)", current)
            await page.wait_for_timeout(700)
            current += viewport_height
            diagnostics["preload_scroll_steps"] = int(diagnostics["preload_scroll_steps"]) + 1
            total_height = await page.evaluate(
                "() => Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)"
            )
            if total_height > previous_total_height:
                diagnostics["scroll_growth_iterations"] = int(diagnostics["scroll_growth_iterations"]) + 1
                previous_total_height = total_height
                stabilized_iterations = 0
            else:
                stabilized_iterations += 1

            if current >= total_height:
                if stabilized_iterations >= 4:
                    break
                current = max(0, total_height - viewport_height)
        except Exception:
            break

    try:
        await page.evaluate("(y) => window.scrollTo(0, y)", max(0, total_height - viewport_height))
        await page.wait_for_timeout(1200)
        await page.evaluate("() => window.scrollTo(0, 0)")
        await page.wait_for_timeout(900)
    except Exception:
        pass

    diagnostics["final_scroll_height"] = total_height
    return diagnostics


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
    full_page_path = base_dir / f"{job_id}-stitched-source.png"
    await page.screenshot(path=str(full_page_path), full_page=True)
    full_page_bytes = _crop_blank_space(full_page_path.read_bytes())
    full_page_path.write_bytes(full_page_bytes)
    return _split_cropped_image(full_page_bytes, base_dir, job_id)


def _crop_blank_space(image_bytes: bytes) -> bytes:
    try:
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
    except Exception:
        return image_bytes

    width, height = image.size
    pixels = image.load()
    top, bottom = height, 0

    for y in range(height):
        row_has_content = False
        for x in range(width):
            red, green, blue = pixels[x, y]
            if red < 245 or green < 245 or blue < 245:
                row_has_content = True
                break
        if row_has_content:
            top = min(top, y)
            bottom = max(bottom, y)

    if bottom <= top:
        return image_bytes

    padding = 8
    cropped = image.crop(
        (
            0,
            max(0, top - padding),
            width,
            min(height, bottom + padding),
        )
    )
    buffer = BytesIO()
    cropped.save(buffer, format="PNG")
    return buffer.getvalue()


def _split_cropped_image(image_bytes: bytes, base_dir: Path, job_id: str) -> tuple[list[bytes], list[str]]:
    try:
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
    except Exception:
        return [image_bytes], []

    width, height = image.size
    segment_height = 1700
    overlap = 220
    top = 0
    index = 1
    image_paths: list[str] = []
    image_bytes_list: list[bytes] = []

    while top < height:
        bottom = _find_segment_break(image, top, segment_height, overlap)
        segment = image.crop((0, top, width, bottom))
        buffer = BytesIO()
        segment.save(buffer, format="PNG")
        segment_bytes = buffer.getvalue()
        path = base_dir / f"{job_id}-segment-{index}.png"
        path.write_bytes(segment_bytes)
        image_paths.append(str(path))
        image_bytes_list.append(segment_bytes)
        if bottom >= height:
            break
        top = bottom - overlap
        index += 1

    return image_bytes_list, image_paths


def _find_segment_break(image: Image.Image, top: int, segment_height: int, overlap: int) -> int:
    width, height = image.size
    target_bottom = min(height, top + segment_height)
    if target_bottom >= height:
        return height

    pixels = image.load()
    search_start = max(top + 900, target_bottom - 260)
    search_end = min(height - 1, target_bottom + 260)

    best_y = target_bottom
    best_score = float("inf")

    for y in range(search_start, search_end):
        non_light_pixels = 0
        sample_step = max(1, width // 120)
        for x in range(0, width, sample_step):
            red, green, blue = pixels[x, y]
            if red < 240 or green < 240 or blue < 240:
                non_light_pixels += 1
        if non_light_pixels < best_score:
            best_score = non_light_pixels
            best_y = y

    if best_y <= top + overlap:
        return min(height, target_bottom)
    return best_y


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
                "Read all screenshots and translate the flyer into structured text. "
                "If you can clearly see a product and a price or discount badge, include it even if some fine print is unreadable."
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

    system_prompt = (
        "You are extracting offer data from supermarket flyer screenshots. "
        "The flyer language may be German even if the user request is English. "
        "Read the screenshots carefully and extract visible offers aggressively. "
        "Do not return an empty list if any product/price pair or discount badge is visible. "
        "Partial offers are acceptable. "
        "Prices and discount labels are especially important. "
        "Return JSON only with a top-level key named offers. "
        "Each offer must be an object with keys: "
        "product_name, price, discount, validity, retailer, source_text. "
        "Use empty strings for missing fields. "
        "German retail words to pay attention to include: Angebot, Angebote, Preis, Rabatt, Gültig, Ab, Bis, XXL, kg-Preis, Stück. "
        "Examples of good outputs: "
        "{\"product_name\":\"Erdbeeren\",\"price\":\"1.49\",\"discount\":\"-50%\",\"validity\":\"Ab Mo. 23.3. bis Sa. 28.3.\",\"retailer\":\"Lidl\",\"source_text\":\"Erdbeeren ... -50% 1.49\"} "
        "{\"product_name\":\"Deutsche rote Äpfel\",\"price\":\"2.22\",\"discount\":\"3-kg-Netz\",\"validity\":\"Ab Mo. 23.3. bis Sa. 28.3.\",\"retailer\":\"Lidl\",\"source_text\":\"Deutsche rote Äpfel 3-kg-Netz 2.22\"} "
        "Every returned offer should include a visible price. If you cannot find a price, skip that offer. "
        "Ignore only pure branding, navigation, legal footer text, and app UI text."
    )

    def call_openai(extra_user_text: str) -> str:
        response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": system_prompt,
                    }
                ],
            },
            {
                "role": "user",
                "content": user_content
                + [
                    {
                        "type": "input_text",
                        "text": extra_user_text,
                    }
                ],
            },
        ],
        text={"format": {"type": "json_object"}},
    )
        return response.output_text

    raw_response_full = call_openai(
        "Extract all visible offers. Prefer returning partial structured offers over returning an empty list."
    )

    try:
        payload = json.loads(raw_response_full)
    except json.JSONDecodeError as exc:
        raise ScrapeEmptyError(
            "OpenAI Vision returned a non-JSON response for the flyer screenshots.",
            diagnostics={"vision_raw_response": raw_response_full[:12000], "exception_type": exc.__class__.__name__},
        ) from exc

    offers = payload.get("offers", [])
    if isinstance(offers, list) and len(offers) == 0:
        retry_response = call_openai(
            "Your previous answer was empty. Retry more aggressively. "
            "Return every visible offer candidate. "
            "If exact prices are hard to read, still extract product_name plus approximate visible price or discount text. "
            "Look especially for large red or yellow price badges and percent discount labels. "
            "Only include offers where a price is visible. "
            "Do not return an empty list unless there are truly no visible products."
        )
        raw_response_full = retry_response
        try:
            payload = json.loads(retry_response)
            offers = payload.get("offers", [])
        except json.JSONDecodeError:
            offers = []
    if not isinstance(offers, list):
        raise ScrapeEmptyError(
            "OpenAI Vision did not return an offers list.",
            diagnostics={"vision_raw_response": raw_response_full[:12000]},
        )

    normalized_offers: list[dict[str, str]] = []
    for offer in offers:
        if not isinstance(offer, dict):
            continue
        source_text = _normalize_whitespace(str(offer.get("source_text", "")))
        recovered_price_match = PRICE_REGEX.search(source_text)
        recovered_price = _normalize_whitespace(recovered_price_match.group(0)) if recovered_price_match else ""
        normalized_offer = {
            "product_name": _normalize_whitespace(str(offer.get("product_name", ""))),
            "price": _normalize_whitespace(str(offer.get("price", ""))) or recovered_price,
            "discount": _normalize_whitespace(str(offer.get("discount", ""))),
            "validity": _normalize_whitespace(str(offer.get("validity", ""))),
            "retailer": _normalize_whitespace(str(offer.get("retailer", retailer_focus or ""))),
            "source_text": source_text,
        }
        if normalized_offer["price"] and (normalized_offer["product_name"] or normalized_offer["source_text"]):
            normalized_offers.append(normalized_offer)

    return normalized_offers, raw_response_full[:12000]


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
            interaction_diagnostics = await _prepare_offer_view(page)
            preload_diagnostics = await _load_full_offer_listing(page)
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
        **interaction_diagnostics,
        **preload_diagnostics,
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
