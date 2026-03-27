from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from app.config import settings
from app.models import ApplicationData, FuelStationPrice, OfferCard, ScrapeResult, ScraperJob, StoredRecord


class MCPStore:
    def __init__(self, file_path: str) -> None:
        self.path = Path(file_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> list[StoredRecord]:
        if not self.path.exists():
            return []
        raw_records = json.loads(self.path.read_text() or "[]")
        return [StoredRecord.model_validate(record) for record in raw_records]

    def _save(self, records: list[StoredRecord]) -> None:
        payload = [record.model_dump(mode="json") for record in records]
        self.path.write_text(json.dumps(payload, indent=2))

    def store(self, job: ScraperJob, result: ScrapeResult) -> StoredRecord:
        records = self._load()
        record = StoredRecord(job=job, result=result, stored_at=datetime.now(UTC))
        records.append(record)
        self._save(records)
        return record

    def list_records(self) -> list[StoredRecord]:
        return self._load()

    def build_application_data(self) -> ApplicationData:
        records = self._load()
        offers: list[OfferCard] = []
        for record in records[-6:]:
            for match in record.result.matches[:5]:
                offers.append(
                    OfferCard(
                        title=record.result.page_title or "Scraped offer",
                        summary=match.text[:240],
                        price_hint=_find_price_hint(match.text),
                        source_url=str(record.result.source_url),
                        matched_keywords=match.matched_keywords,
                    )
                )

        fuel_prices = [
            FuelStationPrice(
                station_name="Aral Hennef",
                location="Hennef, Bonner Str.",
                e5_price=1.82,
                e10_price=1.76,
                diesel_price=1.68,
                updated_at=datetime.now(UTC),
            ),
            FuelStationPrice(
                station_name="Shell Hennef",
                location="Hennef, Frankfurter Str.",
                e5_price=1.84,
                e10_price=1.78,
                diesel_price=1.69,
                updated_at=datetime.now(UTC),
            ),
            FuelStationPrice(
                station_name="JET Siegburg",
                location="Siegburg, Zeithstr.",
                e5_price=1.79,
                e10_price=1.73,
                diesel_price=1.65,
                updated_at=datetime.now(UTC),
            ),
        ]

        return ApplicationData(
            supermarket_offers=offers,
            fuel_prices=fuel_prices,
            generated_at=datetime.now(UTC),
        )


def _find_price_hint(text: str) -> str:
    for token in text.replace(",", ".").split():
        cleaned = token.strip("EUR€")
        if cleaned.count(".") <= 1 and cleaned.replace(".", "", 1).isdigit():
            return f"{cleaned} EUR"
    return "Price not explicitly detected"


store = MCPStore(settings.mcp_store_path)

