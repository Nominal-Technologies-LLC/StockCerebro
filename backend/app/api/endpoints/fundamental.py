from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.validation import validate_ticker
from app.database import get_db
from app.models.user import User
from app.schemas.fundamental import FundamentalAnalysis
from app.services.data_aggregator import DataAggregator

router = APIRouter(prefix="/api/stock", tags=["fundamental"])


@router.get("/{ticker}/fundamental", response_model=FundamentalAnalysis)
async def get_fundamental_analysis(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ticker = validate_ticker(ticker)
    aggregator = DataAggregator(db)
    result = await aggregator.get_fundamental_analysis(ticker)
    if not result:
        raise HTTPException(status_code=404, detail=f"No fundamental data for '{ticker}'")
    return result
