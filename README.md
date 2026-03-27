# Scraper + Data Analytics + Application Server

This repository contains a dockerized multi-service prototype for:

- opening JavaScript-rendered retail pages in a real browser
- switching to a cleaner offer view when available
- capturing flyer screenshots and sending them to OpenAI Vision
- translating user intent into structured scraper jobs
- storing extracted records in an MCP-oriented storage layer
- serving a user-facing application for supermarket offers and fuel price comparison

## Stack

- `scraper-service`: FastAPI + Playwright + OpenAI Python SDK
- `data-analytics-server`: FastAPI + Jinja + OpenAI Python SDK
- `application-server`: Next.js App Router
- `orchestration`: Docker Compose

## Services

### 1. Scraper Service

- Receives structured scraping jobs from the Data-Analytics Server
- Loads pages with Playwright to support JavaScript-rendered content
- Tries to accept cookie dialogs, close blocking overlays, and switch to the `Angebote` view
- Scrolls through long offer pages before screenshot capture so lazy-loaded flyer content is included
- Captures stitched screenshots and splits them into segments
- Sends screenshot segments to OpenAI Vision for structured offer extraction
- Returns structured scrape matches plus detailed debug diagnostics

### 2. Data-Analytics Server

- Provides a web GUI for submitting scraping requests
- Converts natural-language requests into structured scraper jobs
- Uses OpenAI when `OPENAI_API_KEY` is configured
- Falls back to deterministic keyword extraction for job generation if no API key is present
- Stores results in a JSON-backed MCP-style storage layer
- Exposes aggregated application data APIs
- Serves scraper debug screenshots and shows diagnostics in the web UI

### 3. Application Server

- Queries the Data-Analytics Server for processed data
- Shows a modern responsive UI for:
  - supermarket offers
  - fuel price comparisons

## Repository structure

```text
.
├── application-server
├── data-analytics-server
├── data
├── scraper-service
├── shared
│   └── schemas
├── docker-compose.yml
└── .env.example
```

## Environment

Docker Compose reads `.env`, so create it from the example first:

```bash
cp .env.example .env
```

Important variables:

- `OPENAI_API_KEY`: required for screenshot-to-text scraping and optional for analytics-side job generation
- `OPENAI_VISION_MODEL`: model used by the scraper for image understanding
- `SCRAPER_SERVICE_URL`: internal URL used by the Data-Analytics Server
- `MCP_STORE_PATH`: JSON storage file used by the MCP-style store
- `SCRAPER_DEBUG_DIR`: shared directory for debug screenshots
- `DATA_ANALYTICS_URL`: internal URL used by the Application Server
- `NEXT_PUBLIC_DATA_ANALYTICS_URL`: browser-facing URL for frontend references

## Run with Docker

```bash
docker compose up --build
```

If you want to force a clean rebuild after scraper changes:

```bash
docker compose build --no-cache scraper-service data-analytics-server
docker compose up scraper-service data-analytics-server application-server
```

Available services after startup:

- Data-Analytics Server UI: [http://localhost:8000](http://localhost:8000)
- Scraper Service API: [http://localhost:8001/docs](http://localhost:8001/docs)
- Application Server UI: [http://localhost:3000](http://localhost:3000)

## Example workflow

1. Open the Data-Analytics Server at `http://localhost:8000`
2. Enter a target URL such as:

```text
https://www.kaufda.de/contentViewer/static/example
```

3. Describe the information you want, for example:

```text
Find supermarket promotions, product names, prices, discounts, and validity hints.
```

4. Submit the request
5. Check the debug panels in the Data-Analytics UI:
   - `Scraper Debug`
   - `OpenAI Vision Debug`
6. Open the Application Server at `http://localhost:3000` to see stored supermarket offers and fuel-price comparison data

## Current scraper workflow

The scraper currently follows this flow:

1. Open the target page in Playwright
2. Try to accept cookie dialogs and close blocking overlays
3. Try to switch into a clearer offers view such as `Angebote`
4. Preload long pages by scrolling until the document height stabilizes
5. Capture a stitched full-page screenshot
6. Split the stitched image into overlapping segments
7. Send the segment images to OpenAI Vision
8. Parse the returned offer objects into the MCP-oriented store format

This repository is currently optimized for flyer-style retail pages rather than generic DOM scraping.

## API overview

### Data-Analytics Server

- `GET /health`
- `GET /`
- `POST /api/jobs/submit`
- `GET /api/records`
- `GET /api/application-data`

### Scraper Service

- `GET /health`
- `POST /scrape`

## Notes and assumptions

- The MCP server is implemented here as a pragmatic JSON-backed MCP-oriented storage layer to keep the prototype runnable and easy to understand.
- Fuel station prices are currently seeded sample data so the Application Server can demonstrate comparisons immediately.
- The scraper currently relies on screenshot-based extraction through OpenAI Vision rather than DOM/OCR/JSON-LD parsing.
- Keywords are used as hints, not as hard filters.
- Debug screenshots are written to `./data/scraper-debug` and surfaced in the Data-Analytics UI.
- The Data-Analytics Server intentionally translates user intent into a structured internal job instead of sending the raw user prompt to the scraper.

## Next recommended improvements

- Replace the JSON store with PostgreSQL or another persistent datastore
- Add an actual MCP transport layer if full MCP interoperability is needed
- Add async job queues and background workers
- Add authentication and tenant separation
- Add stronger domain-specific logic for retailer tabs, cookie managers, and flyer segmentation
