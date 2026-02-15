from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.validation import validate_ticker
from app.database import get_db
from app.models.user import User
from app.schemas.scorecard import Scorecard
from app.services.data_aggregator import DataAggregator

router = APIRouter(prefix="/api/stock", tags=["scorecard"])


@router.get("/{ticker}/scorecard", response_model=Scorecard)
async def get_scorecard(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ticker = validate_ticker(ticker)
    aggregator = DataAggregator(db)
    result = await aggregator.get_scorecard(ticker)
    if not result:
        raise HTTPException(status_code=404, detail=f"No scorecard data for '{ticker}'")
    return result
