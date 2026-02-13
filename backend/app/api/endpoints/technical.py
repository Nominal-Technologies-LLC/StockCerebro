from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.validation import validate_ticker
from app.database import get_db
from app.schemas.technical import TechnicalAnalysis
from app.services.data_aggregator import DataAggregator

router = APIRouter(prefix="/api/stock", tags=["technical"])


@router.get("/{ticker}/technical", response_model=TechnicalAnalysis)
async def get_technical_analysis(
    ticker: str,
    timeframe: str = "d",
    db: AsyncSession = Depends(get_db),
):
    ticker = validate_ticker(ticker)
    valid_timeframes = {"h": "hourly", "d": "daily", "w": "weekly"}
    if timeframe not in valid_timeframes:
        raise HTTPException(status_code=400, detail="Timeframe must be 'h', 'd', or 'w'")

    aggregator = DataAggregator(db)
    result = await aggregator.get_technical_analysis(ticker, valid_timeframes[timeframe])
    if not result:
        raise HTTPException(status_code=404, detail=f"No technical data for '{ticker}'")
    return result
