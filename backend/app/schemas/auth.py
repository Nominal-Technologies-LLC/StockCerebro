from datetime import datetime

from pydantic import BaseModel


class GoogleLoginRequest(BaseModel):
    credential: str  # JWT token from Google Sign-In


class SubscriptionInfo(BaseModel):
    status: str  # 'admin', 'override', 'paid', 'trialing', 'expired'
    has_access: bool
    has_macro_access: bool
    trial_ends_at: datetime | None


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    picture: str | None
    is_admin: bool = False
    subscription: SubscriptionInfo | None = None


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
    subscription_status: str | None = None
    subscription_override: bool = False
    trial_ends_at: datetime | None = None
