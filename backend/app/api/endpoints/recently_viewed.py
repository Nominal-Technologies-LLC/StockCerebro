from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.database import get_db
from app.models.recently_viewed import RecentlyViewed
from app.models.user import User
from app.schemas.recently_viewed import RecentlyViewedRecord, RecordViewRequest

router = APIRouter(prefix="/api/recently-viewed", tags=["recently-viewed"])

MAX_RECENT_ITEMS = 15


@router.get("", response_model=list[RecentlyViewedRecord])
async def get_recently_viewed(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's recently viewed stocks, most recent first."""
    result = await db.execute(
        select(RecentlyViewed)
        .where(RecentlyViewed.user_id == current_user.id)
        .order_by(desc(RecentlyViewed.viewed_at))
        .limit(MAX_RECENT_ITEMS)
    )
    rows = result.scalars().all()
    return [
        RecentlyViewedRecord(
            ticker=r.ticker,
            company_name=r.company_name,
            grade=r.grade,
            signal=r.signal,
            score=r.score,
            viewed_at=r.viewed_at,
        )
        for r in rows
    ]


@router.post("", response_model=RecentlyViewedRecord)
async def record_view(
    body: RecordViewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record or update a recently viewed stock for the current user."""
    # Check if this ticker already exists for this user
    result = await db.execute(
        select(RecentlyViewed).where(
            RecentlyViewed.user_id == current_user.id,
            RecentlyViewed.ticker == body.ticker.upper(),
        )
    )
    existing = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if existing:
        # Update existing record
        existing.company_name = body.company_name
        existing.grade = body.grade
        existing.signal = body.signal
        existing.score = body.score
        existing.viewed_at = now
        record = existing
    else:
        # Create new record
        record = RecentlyViewed(
            user_id=current_user.id,
            ticker=body.ticker.upper(),
            company_name=body.company_name,
            grade=body.grade,
            signal=body.signal,
            score=body.score,
            viewed_at=now,
        )
        db.add(record)

    await db.commit()
    await db.refresh(record)

    # Prune old entries beyond MAX_RECENT_ITEMS
    all_result = await db.execute(
        select(RecentlyViewed.id)
        .where(RecentlyViewed.user_id == current_user.id)
        .order_by(desc(RecentlyViewed.viewed_at))
        .offset(MAX_RECENT_ITEMS)
    )
    old_ids = [row[0] for row in all_result.all()]
    if old_ids:
        await db.execute(
            delete(RecentlyViewed).where(RecentlyViewed.id.in_(old_ids))
        )
        await db.commit()

    return RecentlyViewedRecord(
        ticker=record.ticker,
        company_name=record.company_name,
        grade=record.grade,
        signal=record.signal,
        score=record.score,
        viewed_at=record.viewed_at,
    )
