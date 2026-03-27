from __future__ import annotations

import json
from urllib.parse import urlparse

from openai import OpenAI

from app.config import settings
from app.models import ExpectedOutput, ScraperJob


def _heuristic_job(target_url: str, user_prompt: str) -> ScraperJob:
    prompt_words = [word.strip(".,:;!?").lower() for word in user_prompt.split()]
    stop_words = {"the", "and", "for", "with", "from", "that", "this", "into", "what"}
    keywords = [word for word in prompt_words if len(word) > 3 and word not in stop_words]
    domain = urlparse(target_url).netloc.replace("www.", "")
    default_keywords = keywords[:8] or ["price", "offer", "discount", domain]
    return ScraperJob(
        target_url=target_url,
        user_intent=user_prompt.strip(),
        keywords=sorted(set(default_keywords)),
        extraction_instructions=[
            "Focus on user-requested entities, prices, dates, and promotional labels.",
            "Ignore navigation, footers, cookie prompts, and unrelated generic text.",
            "Return the most relevant text blocks for downstream processing.",
        ],
        expected_output=ExpectedOutput(
            format="json",
            fields=["headline", "price", "validity", "description", "matched_keywords"],
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
                    "extraction_instructions, expected_output."
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

