from __future__ import annotations

import json
from urllib.parse import urlparse

from openai import OpenAI

from app.config import settings
from app.models import ExpectedOutput, ScraperJob


KEYWORD_ALIASES = {
    "price": ["preis", "preise", "price", "prices"],
    "offer": ["angebot", "angebote", "offer", "offers", "prospekt", "flyer"],
    "discount": ["rabatt", "aktion", "discount", "sale", "deal"],
    "validity": ["gueltig", "gültig", "validity", "valid", "bis", "ab"],
    "product": ["produkt", "produkte", "product", "products", "artikel"],
    "supermarket": ["supermarkt", "markt", "supermarket", "grocery"],
    "promotion": ["werbung", "promotion", "promo", "aktion"],
}


def _heuristic_job(target_url: str, user_prompt: str) -> ScraperJob:
    prompt_words = [word.strip(".,:;!?").lower() for word in user_prompt.split()]
    stop_words = {"the", "and", "for", "with", "from", "that", "this", "into", "what", "find"}
    keywords = [word for word in prompt_words if len(word) > 2 and word not in stop_words]
    domain = urlparse(target_url).netloc.replace("www.", "")
    expanded_keywords: set[str] = set(keywords[:10] or ["price", "offer", "discount"])
    for keyword in list(expanded_keywords):
        for alias_group in KEYWORD_ALIASES.values():
            if keyword in alias_group:
                expanded_keywords.update(alias_group)
    expanded_keywords.update(["preis", "angebot", "rabatt", "gültig", "product", "price", domain])
    return ScraperJob(
        target_url=target_url,
        user_intent=user_prompt.strip(),
        keywords=sorted(expanded_keywords),
        extraction_instructions=[
            "Use keywords only as hints, not as strict filters.",
            "Prefer product names, prices, discount labels, validity dates, and retailer names visible in the flyer.",
            "Expect that the website language may differ from the user's language.",
        ],
        expected_output=ExpectedOutput(
            format="json",
            fields=["product_name", "price", "discount", "validity", "retailer", "source_text"],
        ),
    )


def generate_scraper_job(target_url: str, user_prompt: str) -> ScraperJob:
    if not settings.openai_api_key:
        return _heuristic_job(target_url, user_prompt)

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.responses.create(
        model=settings.openai_model,
        input=[
            {
                "role": "system",
                "content": (
                    "You translate user scraping requests into structured internal jobs. "
                    "Respond with JSON only using keys: user_intent, keywords, "
                    "extraction_instructions, expected_output. "
                    "Keywords should be multilingual hints when appropriate, including the likely website language."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Target URL: {target_url}\n"
                    f"User request: {user_prompt}\n"
                    "Create a concise scraping job for a web scraper."
                ),
            },
        ],
        text={"format": {"type": "json_object"}},
    )
    payload = json.loads(response.output_text)
    return ScraperJob(
        target_url=target_url,
        user_intent=payload.get("user_intent", user_prompt),
        keywords=payload.get("keywords", []),
        extraction_instructions=payload.get("extraction_instructions", []),
        expected_output=ExpectedOutput(**payload.get("expected_output", {})),
    )
