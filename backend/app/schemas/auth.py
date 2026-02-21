from datetime import datetime

from pydantic import BaseModel, EmailStr


class GoogleLoginRequest(BaseModel):
    credential: str  # JWT token from Google Sign-In


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    picture: str | None
    is_admin: bool = False


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class AdminUserResponse(BaseModel):
    id: int
    email: str
    name: str
    picture: str | None
    created_at: datetime
    last_login: datetime
