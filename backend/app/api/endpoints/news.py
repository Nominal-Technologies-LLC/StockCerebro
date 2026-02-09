from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.scorecard import NewsArticle
from app.services.data_aggregator import DataAggregator

router = APIRouter(prefix="/api/stock", tags=["news"])


@router.get("/{ticker}/news", response_model=list[NewsArticle])
async def get_news(ticker: str, db: AsyncSession = Depends(get_db)):
    aggregator = DataAggregator(db)
    result = await aggregator.get_news(ticker.upper())
    if result is None:
        raise HTTPException(status_code=404, detail=f"No news for '{ticker}'")
    return result
