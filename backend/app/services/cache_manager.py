import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cache import (
    AnalysisCache,
    CompanyCache,
    FundamentalCache,
    NewsCache,
    PeerCache,
    PriceCache,
)

logger = logging.getLogger(__name__)


def _is_stale(fetched_at: datetime, ttl_seconds: int) -> bool:
    now = datetime.now(timezone.utc)
    age = (now - fetched_at.replace(tzinfo=timezone.utc)).total_seconds()
    return age > ttl_seconds


def _is_market_hours() -> bool:
    now = datetime.now(timezone.utc)
    # US market: 9:30-16:00 ET = 14:30-21:00 UTC (roughly, ignoring DST)
    weekday = now.weekday()
    if weekday >= 5:
        return False
    hour = now.hour
    return 14 <= hour < 21


class CacheManager:
    def __init__(self, db: AsyncSession):
        self.db = db

    # --- Company Cache ---

    async def get_company(self, ticker: str, ttl: int = 86400) -> dict | None:
        result = await self.db.execute(
            select(CompanyCache).where(CompanyCache.ticker == ticker)
        )
        cached = result.scalar_one_or_none()
        if cached and not _is_stale(cached.fetched_at, ttl):
            return cached.raw_info
        return None

    async def set_company(self, ticker: str, info: dict):
        result = await self.db.execute(
            select(CompanyCache).where(CompanyCache.ticker == ticker)
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.name = info.get("shortName") or info.get("longName")
            existing.sector = info.get("sector")
            existing.industry = info.get("industry")
            existing.market_cap = info.get("marketCap")
            existing.raw_info = info
            existing.fetched_at = datetime.now(timezone.utc)
        else:
            company = CompanyCache(
                ticker=ticker,
                name=info.get("shortName") or info.get("longName"),
                sector=info.get("sector"),
                industry=info.get("industry"),
                market_cap=info.get("marketCap"),
                raw_info=info,
                fetched_at=datetime.now(timezone.utc),
            )
            self.db.add(company)
        await self.db.commit()

    # --- Price Cache ---

    async def get_prices(self, ticker: str, interval: str, period: str) -> dict | None:
        ttl = 900 if _is_market_hours() else 86400
        result = await self.db.execute(
            select(PriceCache).where(
                PriceCache.ticker == ticker,
                PriceCache.interval == interval,
                PriceCache.period == period,
            )
        )
        cached = result.scalar_one_or_none()
        if cached and not _is_stale(cached.fetched_at, ttl):
            return cached.ohlcv_data
        return None

    async def set_prices(self, ticker: str, interval: str, period: str, data: dict):
        result = await self.db.execute(
            select(PriceCache).where(
                PriceCache.ticker == ticker,
                PriceCache.interval == interval,
                PriceCache.period == period,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.ohlcv_data = data
            existing.fetched_at = datetime.now(timezone.utc)
        else:
            entry = PriceCache(
                ticker=ticker,
                interval=interval,
                period=period,
                ohlcv_data=data,
                fetched_at=datetime.now(timezone.utc),
            )
            self.db.add(entry)
        await self.db.commit()

    # --- Fundamental Cache ---

    async def get_fundamental(self, ticker: str, data_type: str, source: str = "yfinance", ttl: int = 86400) -> dict | None:
        result = await self.db.execute(
            select(FundamentalCache).where(
                FundamentalCache.ticker == ticker,
                FundamentalCache.data_type == data_type,
                FundamentalCache.source == source,
            )
        )
        cached = result.scalar_one_or_none()
        if cached and not _is_stale(cached.fetched_at, ttl):
            return cached.data
        return None

    async def set_fundamental(self, ticker: str, data_type: str, source: str, data: dict):
        result = await self.db.execute(
            select(FundamentalCache).where(
                FundamentalCache.ticker == ticker,
                FundamentalCache.data_type == data_type,
                FundamentalCache.source == source,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.data = data
            existing.fetched_at = datetime.now(timezone.utc)
        else:
            entry = FundamentalCache(
                ticker=ticker,
                data_type=data_type,
                source=source,
                data=data,
                fetched_at=datetime.now(timezone.utc),
            )
            self.db.add(entry)
        await self.db.commit()

    # --- Analysis Cache ---

    async def get_analysis(self, ticker: str, analysis_type: str, ttl: int = 1800) -> dict | None:
        result = await self.db.execute(
            select(AnalysisCache).where(
                AnalysisCache.ticker == ticker,
                AnalysisCache.analysis_type == analysis_type,
            )
        )
        cached = result.scalar_one_or_none()
        if cached and not _is_stale(cached.fetched_at, ttl):
            return cached.data
        return None

    async def set_analysis(self, ticker: str, analysis_type: str, data: dict):
        result = await self.db.execute(
            select(AnalysisCache).where(
                AnalysisCache.ticker == ticker,
                AnalysisCache.analysis_type == analysis_type,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.data = data
            existing.fetched_at = datetime.now(timezone.utc)
        else:
            entry = AnalysisCache(
                ticker=ticker,
                analysis_type=analysis_type,
                data=data,
                fetched_at=datetime.now(timezone.utc),
            )
            self.db.add(entry)
        await self.db.commit()

    # --- News Cache ---

    async def get_news(self, ticker: str, source: str = "yfinance", ttl: int = 3600) -> list | None:
        result = await self.db.execute(
            select(NewsCache).where(
                NewsCache.ticker == ticker,
                NewsCache.source == source,
            )
        )
        cached = result.scalar_one_or_none()
        if cached and not _is_stale(cached.fetched_at, ttl):
            return cached.articles.get("articles", []) if cached.articles else []
        return None

    async def set_news(self, ticker: str, source: str, articles: list):
        result = await self.db.execute(
            select(NewsCache).where(
                NewsCache.ticker == ticker,
                NewsCache.source == source,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.articles = {"articles": articles}
            existing.fetched_at = datetime.now(timezone.utc)
        else:
            entry = NewsCache(
                ticker=ticker,
                source=source,
                articles={"articles": articles},
                fetched_at=datetime.now(timezone.utc),
            )
            self.db.add(entry)
        await self.db.commit()

    # --- Peer Cache ---

    async def get_peers(self, ticker: str, ttl: int = 86400) -> list | None:
        result = await self.db.execute(
            select(PeerCache).where(PeerCache.ticker == ticker)
        )
        cached = result.scalar_one_or_none()
        if cached and not _is_stale(cached.fetched_at, ttl):
            return cached.peers.get("peers", []) if cached.peers else []
        return None

    async def set_peers(self, ticker: str, peers: list):
        result = await self.db.execute(
            select(PeerCache).where(PeerCache.ticker == ticker)
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.peers = {"peers": peers}
            existing.fetched_at = datetime.now(timezone.utc)
        else:
            entry = PeerCache(
                ticker=ticker,
                peers={"peers": peers},
                fetched_at=datetime.now(timezone.utc),
            )
            self.db.add(entry)
        await self.db.commit()
