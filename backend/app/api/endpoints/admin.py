from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_admin_user
from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.schemas.auth import AdminUserResponse

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users", response_model=list[AdminUserResponse])
async def list_users(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List all users. Admin only."""
    settings = get_settings()
    result = await db.execute(select(User).order_by(User.last_login.desc()))
    users = result.scalars().all()
    return [
        AdminUserResponse(
            id=u.id,
            email=u.email,
            name=u.name,
            picture=u.picture,
            created_at=u.created_at,
            last_login=u.last_login,
            subscription_status=u.effective_access if not settings.is_admin(u.email) else "admin",
            subscription_override=u.subscription_override,
            trial_ends_at=u.trial_ends_at,
        )
        for u in users
    ]


@router.post("/users/{user_id}/override-subscription")
async def override_subscription(
    user_id: int,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Grant a user free access by overriding subscription requirement. Admin only."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.subscription_override = True
    await db.commit()
    return {"message": f"Subscription override granted to {user.email}"}


@router.post("/users/{user_id}/remove-override")
async def remove_override(
    user_id: int,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove subscription override for a user. Admin only."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.subscription_override = False
    await db.commit()
    return {"message": f"Subscription override removed for {user.email}"}
