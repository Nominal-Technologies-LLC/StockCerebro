from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.validation import validate_ticker
from app.database import get_db
from app.models.user import User
from app.schemas.stock import ChartData, CompanyOverview
from app.services.data_aggregator import DataAggregator
from app.services.yahoo_direct import fetch_quote_via_chart

router = APIRouter(prefix="/api/stock", tags=["stock"])


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
