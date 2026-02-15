from datetime import datetime, timedelta, timezone

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.user import User


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    async def verify_google_token(self, credential: str) -> dict:
        """Verify Google JWT token and extract user info."""
        try:
            idinfo = id_token.verify_oauth2_token(
                credential,
                google_requests.Request(),
                self.settings.google_client_id
            )

            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Invalid issuer')

            return idinfo
        except ValueError as e:
            raise ValueError(f"Invalid Google token: {e}")

    async def get_or_create_user(self, google_id: str, email: str, name: str, picture: str | None) -> User:
        """Get existing user or create new one."""
        # Try to find existing user
        result = await self.db.execute(
            select(User).where(User.google_id == google_id)
        )
        user = result.scalar_one_or_none()

        if user:
            # Update last login and profile info
            user.last_login = datetime.now(timezone.utc)
            user.name = name
            user.picture = picture
            await self.db.commit()
            await self.db.refresh(user)
            return user

        # Create new user
        user = User(
            google_id=google_id,
            email=email,
            name=name,
            picture=picture
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    def create_access_token(self, user_id: int) -> str:
        """Generate JWT access token."""
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=self.settings.jwt_access_token_expire_minutes
        )
        to_encode = {
            "sub": str(user_id),
            "exp": expire
        }
        return jwt.encode(
            to_encode,
            self.settings.jwt_secret_key,
            algorithm=self.settings.jwt_algorithm
        )

    async def get_current_user(self, token: str) -> User | None:
        """Validate JWT and return current user."""
        try:
            payload = jwt.decode(
                token,
                self.settings.jwt_secret_key,
                algorithms=[self.settings.jwt_algorithm]
            )
            user_id: str = payload.get("sub")
            if user_id is None:
                return None
        except JWTError:
            return None

        result = await self.db.execute(
            select(User).where(User.id == int(user_id))
        )
        return result.scalar_one_or_none()
