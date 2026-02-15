from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://stockcerebro:stockcerebro_dev_password@db:5432/stockcerebro"
    finnhub_api_key: str = ""
    edgar_user_agent: str = "stockcerebro@example.com"

    # Cache TTLs in seconds
    price_cache_ttl_market: int = 900  # 15 min during market hours
    price_cache_ttl_closed: int = 86400  # 24h when market closed
    fundamental_cache_ttl: int = 86400  # 24h
    news_cache_ttl: int = 3600  # 1h
    analysis_cache_ttl: int = 1800  # 30 min

    # Google OAuth2
    google_client_id: str = ""
    google_client_secret: str = ""

    # JWT Settings
    jwt_secret_key: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24  # 24 hours

    # Cookie settings
    cookie_domain: str | None = None  # None for localhost, set for production
    cookie_secure: bool = False  # True in production (HTTPS only)
    cookie_samesite: str = "lax"  # "strict" in production

    model_config = {"env_file": ".env"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
