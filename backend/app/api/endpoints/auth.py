from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.schemas.auth import GoogleLoginRequest, TokenResponse, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/google/login", response_model=TokenResponse)
async def google_login(
    request: GoogleLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate with Google OAuth2 and set HTTP-only cookie."""
    auth_service = AuthService(db)
    settings = get_settings()

    try:
        # Verify Google token
        idinfo = await auth_service.verify_google_token(request.credential)

        # Get or create user
        user = await auth_service.get_or_create_user(
            google_id=idinfo['sub'],
            email=idinfo['email'],
            name=idinfo.get('name', idinfo['email']),
            picture=idinfo.get('picture')
        )

        # Create JWT
        access_token = auth_service.create_access_token(user.id)

        # Set HTTP-only cookie
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=settings.cookie_secure,
            samesite=settings.cookie_samesite,
            domain=settings.cookie_domain,
            max_age=settings.jwt_access_token_expire_minutes * 60
        )

        return TokenResponse(
            access_token=access_token,
            user=UserResponse(
                id=user.id,
                email=user.email,
                name=user.name,
                picture=user.picture
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/logout")
async def logout(response: Response):
    """Clear authentication cookie."""
    response.delete_cookie(key="access_token")
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        picture=current_user.picture
    )
