from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.services.auth_service import AuthService


async def get_current_user(
    access_token: str | None = Cookie(None),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Dependency to get current authenticated user from HTTP-only cookie."""
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    auth_service = AuthService(db)
    user = await auth_service.get_current_user(access_token)

    if user is None:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

    return user


async def get_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency that requires the current user to be an admin."""
    settings = get_settings()
    if not settings.is_admin(current_user.email):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


async def require_active_subscription(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require user to have an active subscription, trial, admin status, or override."""
    settings = get_settings()
    if settings.is_admin(current_user.email):
        return current_user

    access = current_user.effective_access
    if access in ("paid", "trialing", "override"):
        return current_user

    raise HTTPException(
        status_code=403,
        detail="Subscription required. Please subscribe to access this feature.",
    )


async def require_paid_subscription(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require user to have a paid subscription (not trial). For premium features like macro."""
    settings = get_settings()
    if settings.is_admin(current_user.email):
        return current_user

    access = current_user.effective_access
    if access in ("paid", "override"):
        return current_user

    if access == "trialing":
        raise HTTPException(
            status_code=403,
            detail="This feature requires a paid subscription. Upgrade to access macro analysis.",
        )

    raise HTTPException(
        status_code=403,
        detail="Subscription required. Please subscribe to access this feature.",
    )
