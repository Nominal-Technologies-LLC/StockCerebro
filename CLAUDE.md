# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Start all services (frontend, backend, db)
docker compose up --build

# Stop services
docker compose down

# Full reset including database
docker compose down -v
```

All development happens inside Docker. Both frontend and backend have hot-reload — no container restarts needed for code changes. Rebuild with `--build` only after dependency changes.

- Frontend: http://localhost:5173
- Backend: http://localhost:8000 (API docs at /docs)
- Database: PostgreSQL on port 5432

No test suite or linting configuration exists yet.

## Architecture

Three Docker services: React/Vite/TypeScript frontend, FastAPI/Python backend, PostgreSQL 16.

### Backend

**Entry point**: `backend/app/main.py` — creates FastAPI app, registers routers, creates DB tables on startup (no Alembic migrations yet).

**API endpoints** (`backend/app/api/endpoints/`): auth, stock, fundamental, technical, scorecard, news, earnings, macro. All endpoints except `/health` require authentication via JWT in HTTP-only cookie. Standard pattern:

```python
@router.get("/{ticker}/endpoint", response_model=Schema)
async def endpoint(ticker, db=Depends(get_db), current_user=Depends(get_current_user)):
    aggregator = DataAggregator(db)
    return await aggregator.method(ticker)
```

**Data flow**: Endpoint → `DataAggregator` (orchestrator) → cache check → external APIs → analysis engines → response.

**External data sources** (`backend/app/services/`), in priority order:
1. Yahoo v8 Chart API (`yahoo_direct.py`) — prices, basic quote. Always works from Docker (unlike yfinance which gets 429 rate-limited via v10 endpoint).
2. Finnhub (`finnhub_service.py`) — fundamentals, company profile, news, quarterly financials. Rate-limited to 60 calls/min.
3. SEC EDGAR (`edgar_service.py`) — quarterly financials fallback.
4. yfinance (`yfinance_service.py`) — last-resort fallback.
5. OpenAI (`openai_service.py`) — macro risk analysis (GPT-5.1). Sends company profile, 6 key metrics, and up to 10 news headline+summary pairs; returns structured JSON with tailwinds, headwinds, and a summary.

**Analysis engines** (`backend/app/analysis/`):
- `fundamental_analyzer.py` — health scoring (FCF, OCF, IC, D/E, CR; banks use ROE/ROA instead), valuation (peer-relative), growth (QoQ revenue + earnings).
- `technical_analyzer.py` — RSI, MACD, moving averages, support/resistance.
- `scorecard_engine.py` — combines fundamental + technical with override rules (e.g., weak fundamentals + strong technicals caps at HOLD).
- `grading.py` — score → letter grade. Centered at 50=C (A=80+, B=65+, C=50+, D=30+, F<30).

**Caching** (`backend/app/services/cache_manager.py`): Database-backed with TTLs. Prices: 15min during market hours / 24h when closed. Fundamentals/company: 24h. News: 1h. Analysis: 30min. Macro risk: 6h for successful responses (`"macro_risk"` key), 5min for error responses (`"macro_risk_error"` key) so transient failures don't lock out retries.

**Quarterly data pitfall**: Finnhub returns cumulative YTD figures for Q2/Q3. `xbrl_mapper.py` detects this (period >120 days) and de-accumulates to standalone quarters.

### Frontend

**Entry**: `frontend/src/main.tsx` → `App.tsx`. Protected by Google OAuth2 auth. Tab navigation: overview, fundamental, earnings, technical, scorecard, macro. ETFs disable fundamental/earnings tabs.

**State management**: TanStack Query (React Query) with market-hour-aware stale times. API client in `frontend/src/api/client.ts` uses Axios with `withCredentials: true`.

**Auth flow**: Google Sign-In → credential sent to `/api/auth/google/login` → backend verifies, creates JWT in HTTP-only cookie → `AuthContext` tracks user state.

**Styling**: Tailwind CSS dark theme with custom brand colors and score signal colors (strong_buy through strong_sell).

## Environment Variables

Required in `.env` (see `.env.example`):
- `DB_PASSWORD` — PostgreSQL password
- `FINNHUB_API_KEY` — free key from finnhub.io
- `EDGAR_USER_AGENT` — your email (SEC fair access policy)
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` — Google OAuth2 credentials
- `JWT_SECRET_KEY` — session signing key
- `OPENAI_API_KEY` — OpenAI API key for macro risk analysis (GPT-5.1)
