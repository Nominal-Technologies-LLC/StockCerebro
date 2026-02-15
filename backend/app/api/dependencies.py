from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

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
