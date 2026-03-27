# Scraper + Data Analytics + Application Server

This repository contains a dockerized multi-service prototype for:

- scraping static and JavaScript-rendered websites
- translating user intent into structured scraper jobs with the OpenAI API
- storing results in an MCP-oriented storage layer
- serving a user-facing application for supermarket offers and fuel price comparison

## Stack

- `scraper-service`: FastAPI + Playwright + BeautifulSoup
- `data-analytics-server`: FastAPI + Jinja + OpenAI Python SDK
- `application-server`: Next.js App Router
- `orchestration`: Docker Compose

## Services

### 1. Scraper Service

- Receives structured scraping jobs from the Data-Analytics Server
- Loads pages with Playwright to support JavaScript-rendered content
- Filters extracted text blocks using provided keywords
- Returns structured scrape matches with relevance scores

### 2. Data-Analytics Server

- Provides a web GUI for submitting scraping requests
- Converts natural-language requests into structured scraper jobs
- Uses OpenAI when `OPENAI_API_KEY` is configured
- Falls back to deterministic keyword extraction if no API key is present
- Stores results in a JSON-backed MCP-style storage layer
- Exposes aggregated application data APIs

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
├── scraper-service
├── shared
│   └── schemas
├── docker-compose.yml
└── .env.example
```

## Environment

Copy the example environment file if you want local changes:

```bash
cp .env.example .env
```

Important variables:

- `OPENAI_API_KEY`: optional, enables OpenAI-based job generation
- `SCRAPER_SERVICE_URL`: internal URL used by the Data-Analytics Server
- `MCP_STORE_PATH`: JSON storage file used by the MCP-style store
- `DATA_ANALYTICS_URL`: internal URL used by the Application Server
- `NEXT_PUBLIC_DATA_ANALYTICS_URL`: browser-facing URL for frontend references

## Run with Docker

```bash
docker compose up --build
```

Available services after startup:

- Data-Analytics Server UI: [http://localhost:8000](http://localhost:8000)
- Scraper Service API: [http://localhost:8001/docs](http://localhost:8001/docs)
- Application Server UI: [http://localhost:3000](http://localhost:3000)

## Example workflow

1. Open the Data-Analytics Server at `http://localhost:8000`
2. Enter a target URL such as:

```text
https://example.com/offers
```

3. Describe the information you want, for example:

```text
Find supermarket promotions, product names, prices, discounts, and validity hints.
```

4. Submit the request
5. Open the Application Server at `http://localhost:3000` to see stored supermarket offers and fuel-price comparison data

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
- The scraper currently uses keyword scoring over extracted text blocks. This is designed to be extendable with domain-specific parsers later.
- The Data-Analytics Server intentionally translates user intent into a structured internal job instead of sending the raw user prompt to the scraper.

## Next recommended improvements

- Replace the JSON store with PostgreSQL or another persistent datastore
- Add an actual MCP transport layer if full MCP interoperability is needed
- Add async job queues and background workers
- Add authentication and tenant separation
- Add domain-specific parsers for supermarket and fuel data
