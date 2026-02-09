from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.stock import ChartData, CompanyOverview
from app.services.data_aggregator import DataAggregator

router = APIRouter(prefix="/api/stock", tags=["stock"])


@router.get("/{ticker}", response_model=CompanyOverview)
async def get_company_overview(ticker: str, db: AsyncSession = Depends(get_db)):
    aggregator = DataAggregator(db)
    result = await aggregator.get_company_overview(ticker.upper())
    if not result:
        raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not found")
    return result


@router.get("/{ticker}/chart", response_model=ChartData)
async def get_chart_data(
    ticker: str,
    period: str = "6mo",
    interval: str = "1d",
    db: AsyncSession = Depends(get_db),
):
    aggregator = DataAggregator(db)
    result = await aggregator.get_chart_data(ticker.upper(), period, interval)
    if not result:
        raise HTTPException(status_code=404, detail=f"No chart data for '{ticker}'")
    return result
