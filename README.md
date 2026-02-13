# StockCerebro

A stock analysis dashboard that scores companies across fundamental, technical, and financial health dimensions using data from Yahoo Finance, Finnhub, and SEC EDGAR.

**Stack:** React / Vite / TypeScript / Tailwind (frontend) + FastAPI / SQLAlchemy / PostgreSQL (backend), all running in Docker.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- A free [Finnhub API key](https://finnhub.io/register)

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/your-username/StockCerebro.git
cd StockCerebro
```

### 2. Configure environment variables

Copy the example env file and fill in your API key:

```bash
cp .env.example .env
```

Edit `.env`:

```
DB_PASSWORD=stockcerebro_dev_password
FINNHUB_API_KEY=your_finnhub_api_key_here
EDGAR_USER_AGENT=your_email@example.com
```

| Variable | Required | Description |
|----------|----------|-------------|
| `DB_PASSWORD` | Yes | PostgreSQL password (default works for local dev) |
| `FINNHUB_API_KEY` | Yes | Free API key from [finnhub.io](https://finnhub.io/) |
| `EDGAR_USER_AGENT` | Yes | Your email — required by SEC EDGAR's fair access policy |

### 3. Start the application

```bash
docker compose up --build
```

This starts three services:

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | [http://localhost:5173](http://localhost:5173) | React dashboard |
| Backend | [http://localhost:8000](http://localhost:8000) | FastAPI server ([docs](http://localhost:8000/docs)) |
| Database | `localhost:5432` | PostgreSQL 16 |

The first build will take a few minutes to install dependencies. Subsequent starts are much faster.

### 4. Use the app

Open [http://localhost:5173](http://localhost:5173) and search for a stock ticker (e.g. AAPL, MSFT, NVDA).

## Development

Both frontend and backend have hot-reload enabled — code changes are picked up automatically without restarting containers.

To rebuild after dependency changes:

```bash
docker compose up --build
```

To stop everything:

```bash
docker compose down
```

To stop and remove the database volume (full reset):

```bash
docker compose down -v
```

## Project Structure

```
StockCerebro/
├── frontend/          React + Vite + TypeScript + Tailwind
│   ├── src/
│   │   ├── api/           HTTP client
│   │   ├── components/    UI components (fundamental, technical, scorecard, etc.)
│   │   ├── hooks/         React Query data hooks
│   │   ├── types/         TypeScript types
│   │   └── utils/         Formatting, grading, market hours
│   └── Dockerfile
├── backend/           FastAPI + SQLAlchemy + asyncpg
│   ├── app/
│   │   ├── api/           REST endpoints
│   │   ├── analysis/      Scoring engines (fundamental, technical, scorecard)
│   │   ├── services/      Data sources (Yahoo, Finnhub, EDGAR, cache)
│   │   ├── models/        Database models
│   │   └── schemas/       Pydantic response schemas
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```