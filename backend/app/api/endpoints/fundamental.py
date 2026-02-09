from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.fundamental import FundamentalAnalysis
from app.services.data_aggregator import DataAggregator

router = APIRouter(prefix="/api/stock", tags=["fundamental"])


@router.get("/{ticker}/fundamental", response_model=FundamentalAnalysis)
async def get_fundamental_analysis(ticker: str, db: AsyncSession = Depends(get_db)):
    aggregator = DataAggregator(db)
    result = await aggregator.get_fundamental_analysis(ticker.upper())
    if not result:
        raise HTTPException(status_code=404, detail=f"No fundamental data for '{ticker}'")
    return result
