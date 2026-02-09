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

    model_config = {"env_file": ".env"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
