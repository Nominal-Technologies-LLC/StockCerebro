import time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.validation import validate_ticker
from app.database import get_db
from app.models.user import User
from app.schemas.stock import ChartData, CompanyOverview, SymbolSearchResult
from app.services.data_aggregator import DataAggregator
from app.services.yahoo_direct import fetch_quote_via_chart, search_symbols

router = APIRouter(prefix="/api/stock", tags=["stock"])

# Simple in-memory cache for search results (query -> (results, timestamp))
_search_cache: dict[str, tuple[list, float]] = {}
_SEARCH_CACHE_TTL = 3600  # 1 hour


@router.get("/search", response_model=list[SymbolSearchResult])
async def search_tickers(
    q: str = Query(..., min_length=1, max_length=20),
    current_user: User = Depends(get_current_user),
):
    """Search for tickers by symbol or company name."""
    query = q.strip().upper()

    # Check cache
    now = time.time()
    cached = _search_cache.get(query)
    if cached and now - cached[1] < _SEARCH_CACHE_TTL:
        return cached[0]

    results = await search_symbols(query)
    _search_cache[query] = (results, now)

    # Prune old cache entries periodically
    if len(_search_cache) > 500:
        cutoff = now - _SEARCH_CACHE_TTL
        stale = [k for k, v in _search_cache.items() if v[1] < cutoff]
        for k in stale:
            del _search_cache[k]

    return results


@router.get("/{ticker}", response_model=CompanyOverview)
async def get_company_overview(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ticker = validate_ticker(ticker)
    aggregator = DataAggregator(db)
    result = await aggregator.get_company_overview(ticker)
    if not result:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not found")
    return result


@router.get("/{ticker}/validate")
async def validate_ticker_exists(
    ticker: str,
    current_user: User = Depends(get_current_user)
):
    ticker = validate_ticker(ticker)
    quote = await fetch_quote_via_chart(ticker)
    if not quote:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not found")
    return {"valid": True, "ticker": ticker}


@router.get("/{ticker}/chart", response_model=ChartData)
async def get_chart_data(
    ticker: str,
    period: str = "6mo",
    interval: str = "1d",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ticker = validate_ticker(ticker)
    aggregator = DataAggregator(db)
    result = await aggregator.get_chart_data(ticker, period, interval)
    if not result:
        raise HTTPException(status_code=404, detail=f"No chart data for '{ticker}'")
    return result
