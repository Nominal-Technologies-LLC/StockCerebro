from pydantic import BaseModel, EmailStr


class GoogleLoginRequest(BaseModel):
    credential: str  # JWT token from Google Sign-In


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    picture: str | None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
