from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_paid_subscription
from app.api.validation import validate_ticker
from app.database import get_db
from app.models.user import User
from app.schemas.macro_risk import MacroRiskResponse
from app.services.data_aggregator import DataAggregator

router = APIRouter(prefix="/api/stock", tags=["macro"])


@router.get("/{ticker}/macro", response_model=MacroRiskResponse)
async def get_macro_risk(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_paid_subscription),
):
    ticker = validate_ticker(ticker)
    aggregator = DataAggregator(db)
    return await aggregator.get_macro_risk(ticker)
