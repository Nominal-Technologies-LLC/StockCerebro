from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.validation import validate_ticker
from app.database import get_db
from app.models.user import User
from app.schemas.scorecard import NewsArticle
from app.services.data_aggregator import DataAggregator

router = APIRouter(prefix="/api/stock", tags=["news"])


@router.get("/{ticker}/news", response_model=list[NewsArticle])
async def get_news(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ticker = validate_ticker(ticker)
    aggregator = DataAggregator(db)
    result = await aggregator.get_news(ticker)
    # DataAggregator.get_news() always returns a list (empty if no news found)
    return result
