import asyncio
import logging
import time

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple rate limiter for Finnhub: 60 calls/min."""

    def __init__(self, max_calls: int = 60, period: float = 60.0):
        self.max_calls = max_calls
        self.period = period
        self.calls: list[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._lock:
            now = time.monotonic()
            self.calls = [t for t in self.calls if now - t < self.period]
            if len(self.calls) >= self.max_calls:
                sleep_time = self.period - (now - self.calls[0])
                await asyncio.sleep(sleep_time)
            self.calls.append(time.monotonic())


class FinnhubService:
    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.finnhub_api_key
        self.rate_limiter = RateLimiter()
        self.enabled = bool(self.api_key)

    async def _get(self, endpoint: str, params: dict = None) -> dict | None:
        if not self.enabled:
            return None
        await self.rate_limiter.acquire()
        params = params or {}
        params["token"] = self.api_key
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.BASE_URL}{endpoint}", params=params)
                if resp.status_code == 200:
                    return resp.json()
                logger.warning(f"Finnhub {endpoint} returned {resp.status_code}")
                return None
        except Exception as e:
            logger.error(f"Finnhub error for {endpoint}: {e}")
            return None

    async def get_company_profile(self, ticker: str) -> dict | None:
        return await self._get("/stock/profile2", {"symbol": ticker})

    async def get_peers(self, ticker: str) -> list | None:
        result = await self._get("/stock/peers", {"symbol": ticker})
        if isinstance(result, list):
            return [p for p in result if p != ticker][:10]
        return None

    async def get_basic_financials(self, ticker: str) -> dict | None:
        return await self._get("/stock/metric", {"symbol": ticker, "metric": "all"})

    async def get_recommendation_trends(self, ticker: str) -> list | None:
        result = await self._get("/stock/recommendation", {"symbol": ticker})
        return result if isinstance(result, list) else None

    async def get_financials_reported(self, ticker: str) -> list[dict] | None:
        result = await self._get("/stock/financials-reported", {"symbol": ticker, "freq": "quarterly"})
        if result and isinstance(result.get("data"), list):
            return result["data"]
        return None

    async def get_earnings_surprises(self, ticker: str) -> list | None:
        """Get quarterly EPS actual vs estimate (surprise data)."""
        result = await self._get("/stock/earnings", {"symbol": ticker, "limit": 12})
        return result if isinstance(result, list) else None

    async def get_news(self, ticker: str) -> list | None:
        from datetime import datetime, timedelta
        today = datetime.now().strftime("%Y-%m-%d")
        month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        result = await self._get("/company-news", {
            "symbol": ticker,
            "from": month_ago,
            "to": today,
        })
        if isinstance(result, list):
            return result[:20]
        return None
