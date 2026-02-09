import asyncio
import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class EdgarService:
    """SEC EDGAR fallback for financial statements. 10 req/sec limit."""

    BASE_URL = "https://data.sec.gov"
    SUBMISSIONS_URL = "https://data.sec.gov/submissions"

    def __init__(self):
        settings = get_settings()
        self.user_agent = settings.edgar_user_agent
        self._semaphore = asyncio.Semaphore(5)

    async def _get(self, url: str) -> dict | None:
        async with self._semaphore:
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.get(
                        url,
                        headers={
                            "User-Agent": self.user_agent,
                            "Accept": "application/json",
                        },
                    )
                    if resp.status_code == 200:
                        return resp.json()
                    logger.warning(f"EDGAR {url} returned {resp.status_code}")
                    return None
            except Exception as e:
                logger.error(f"EDGAR error for {url}: {e}")
                return None
            finally:
                await asyncio.sleep(0.1)  # respect rate limit

    async def get_company_facts(self, cik: str) -> dict | None:
        cik_padded = cik.zfill(10)
        return await self._get(f"{self.BASE_URL}/api/xbrl/companyfacts/CIK{cik_padded}.json")

    async def get_company_submissions(self, cik: str) -> dict | None:
        cik_padded = cik.zfill(10)
        return await self._get(f"{self.SUBMISSIONS_URL}/CIK{cik_padded}.json")

    async def lookup_cik(self, ticker: str) -> str | None:
        data = await self._get(f"{self.BASE_URL}/files/company_tickers.json")
        if not data:
            return None
        for entry in data.values():
            if entry.get("ticker", "").upper() == ticker.upper():
                return str(entry.get("cik_str", ""))
        return None
