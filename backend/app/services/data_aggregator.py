import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.fundamental import FundamentalAnalysis
from app.schemas.scorecard import NewsArticle, Scorecard
from app.schemas.stock import ChartData, CompanyOverview, OHLCVBar
from app.schemas.technical import TechnicalAnalysis
from app.services.cache_manager import CacheManager
from app.services.yahoo_direct import fetch_chart, fetch_quote_via_chart
from app.services.yfinance_service import YFinanceService
from app.services.finnhub_service import FinnhubService

logger = logging.getLogger(__name__)


class DataAggregator:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.cache = CacheManager(db)
        self.yf = YFinanceService()
        self.finnhub = FinnhubService()

    async def get_company_overview(self, ticker: str) -> CompanyOverview | None:
        # Check cache first
        cached_info = await self.cache.get_company(ticker)
        if cached_info:
            return self._build_overview(ticker, cached_info)

        # Primary: Yahoo v8 chart API (reliable, no auth needed)
        quote = await fetch_quote_via_chart(ticker)
        if quote:
            # Supplement with Finnhub for sector/industry/description
            finnhub_profile = await self.finnhub.get_company_profile(ticker)
            if finnhub_profile:
                quote["sector"] = finnhub_profile.get("finnhubIndustry")
                quote["industry"] = finnhub_profile.get("finnhubIndustry")
                quote["marketCap"] = finnhub_profile.get("marketCapitalization")
                if quote["marketCap"]:
                    quote["marketCap"] = quote["marketCap"] * 1_000_000  # Finnhub returns in millions
                quote["website"] = finnhub_profile.get("weburl")
                quote["logo_url"] = finnhub_profile.get("logo")

            # Map to standard keys for _build_overview
            info = self._normalize_yahoo_direct(quote)
            await self.cache.set_company(ticker, info)
            return self._build_overview(ticker, info)

        # Fallback: yfinance library
        info = await self.yf.get_info(ticker)
        if info:
            await self.cache.set_company(ticker, info)
            return self._build_overview(ticker, info)

        return None

    def _normalize_yahoo_direct(self, quote: dict) -> dict:
        """Normalize Yahoo v8 chart meta to match yfinance info keys."""
        return {
            "shortName": quote.get("shortName") or quote.get("longName"),
            "longName": quote.get("longName"),
            "sector": quote.get("sector"),
            "industry": quote.get("industry"),
            "marketCap": quote.get("marketCap"),
            "currentPrice": quote.get("regularMarketPrice"),
            "regularMarketPrice": quote.get("regularMarketPrice"),
            "previousClose": quote.get("chartPreviousClose"),
            "regularMarketVolume": quote.get("regularMarketVolume"),
            "regularMarketDayHigh": quote.get("regularMarketDayHigh"),
            "regularMarketDayLow": quote.get("regularMarketDayLow"),
            "fiftyTwoWeekHigh": quote.get("fiftyTwoWeekHigh"),
            "fiftyTwoWeekLow": quote.get("fiftyTwoWeekLow"),
            "website": quote.get("website"),
            "logo_url": quote.get("logo_url"),
            # These need Finnhub or yfinance for full data
            "trailingPE": quote.get("trailingPE"),
            "forwardPE": quote.get("forwardPE"),
            "dividendYield": quote.get("dividendYield"),
            "beta": quote.get("beta"),
        }

    def _build_overview(self, ticker: str, info: dict) -> CompanyOverview:
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose") or info.get("chartPreviousClose")
        change = None
        change_pct = None
        if price and prev_close:
            change = round(price - prev_close, 2)
            change_pct = round((change / prev_close) * 100, 2)

        return CompanyOverview(
            ticker=ticker,
            name=info.get("shortName") or info.get("longName"),
            sector=info.get("sector"),
            industry=info.get("industry"),
            market_cap=info.get("marketCap"),
            price=price,
            change=change,
            change_percent=change_pct,
            volume=info.get("volume") or info.get("regularMarketVolume"),
            avg_volume=info.get("averageVolume"),
            day_high=info.get("dayHigh") or info.get("regularMarketDayHigh"),
            day_low=info.get("dayLow") or info.get("regularMarketDayLow"),
            fifty_two_week_high=info.get("fiftyTwoWeekHigh"),
            fifty_two_week_low=info.get("fiftyTwoWeekLow"),
            pe_ratio=info.get("trailingPE"),
            forward_pe=info.get("forwardPE"),
            dividend_yield=info.get("dividendYield"),
            beta=info.get("beta"),
            description=info.get("longBusinessSummary"),
            website=info.get("website"),
            logo_url=info.get("logo_url"),
        )

    async def get_chart_data(self, ticker: str, period: str, interval: str) -> ChartData | None:
        # Check cache
        cached = await self.cache.get_prices(ticker, interval, period)
        if cached:
            bars = [OHLCVBar(**b) for b in cached.get("bars", [])]
            return ChartData(ticker=ticker, period=period, interval=interval, bars=bars)

        # Primary: Yahoo v8 chart API (reliable)
        result = await fetch_chart(ticker, range_=period, interval=interval)
        if result and result.get("bars"):
            raw_bars = result["bars"]
            await self.cache.set_prices(ticker, interval, period, {"bars": raw_bars})
            bars = [OHLCVBar(**b) for b in raw_bars]
            return ChartData(ticker=ticker, period=period, interval=interval, bars=bars)

        # Fallback: yfinance
        raw_bars = await self.yf.get_history(ticker, period, interval)
        if raw_bars:
            await self.cache.set_prices(ticker, interval, period, {"bars": raw_bars})
            bars = [OHLCVBar(**b) for b in raw_bars]
            return ChartData(ticker=ticker, period=period, interval=interval, bars=bars)

        return None

    async def get_fundamental_analysis(self, ticker: str) -> FundamentalAnalysis | None:
        # Check analysis cache
        cached = await self.cache.get_analysis(ticker, "fundamental")
        if cached:
            return FundamentalAnalysis(**cached)

        from app.analysis.fundamental_analyzer import FundamentalAnalyzer
        analyzer = FundamentalAnalyzer(self.db, self.cache, self.yf, self.finnhub)
        result = await analyzer.analyze(ticker)
        if result:
            await self.cache.set_analysis(ticker, "fundamental", result.model_dump())
        return result

    async def get_technical_analysis(self, ticker: str, timeframe: str) -> TechnicalAnalysis | None:
        cache_key = f"technical_{timeframe}"
        cached = await self.cache.get_analysis(ticker, cache_key)
        if cached:
            return TechnicalAnalysis(**cached)

        from app.analysis.technical_analyzer import TechnicalAnalyzer
        analyzer = TechnicalAnalyzer()

        # Determine period/interval based on timeframe
        params = {
            "hourly": ("5d", "1h"),
            "daily": ("6mo", "1d"),
            "weekly": ("2y", "1wk"),
        }
        period, interval = params.get(timeframe, ("6mo", "1d"))

        # Primary: Yahoo v8 chart API
        result_data = await fetch_chart(ticker, range_=period, interval=interval)
        bars = result_data["bars"] if result_data else None

        # Fallback: yfinance
        if not bars:
            bars = await self.yf.get_history(ticker, period, interval)

        if not bars:
            return None

        result = analyzer.analyze(ticker, bars, timeframe)
        if result:
            await self.cache.set_analysis(ticker, cache_key, result.model_dump())
        return result

    async def get_scorecard(self, ticker: str) -> Scorecard | None:
        cached = await self.cache.get_analysis(ticker, "scorecard")
        if cached:
            return Scorecard(**cached)

        from app.analysis.scorecard_engine import ScorecardEngine
        engine = ScorecardEngine(self)
        result = await engine.generate(ticker)
        if result:
            await self.cache.set_analysis(ticker, "scorecard", result.model_dump())
        return result

    async def get_news(self, ticker: str) -> list[NewsArticle]:
        cached = await self.cache.get_news(ticker)
        if cached:
            return [NewsArticle(**a) for a in cached]

        # Try Finnhub first (more reliable from Docker)
        finnhub_news = await self.finnhub.get_news(ticker)
        if finnhub_news:
            articles = [
                {
                    "title": n.get("headline", ""),
                    "url": n.get("url", ""),
                    "source": n.get("source", ""),
                    "published": str(n.get("datetime", "")),
                    "summary": n.get("summary", ""),
                }
                for n in finnhub_news
            ]
            await self.cache.set_news(ticker, "finnhub", articles)
            return [NewsArticle(**a) for a in articles]

        # Fallback: yfinance
        articles = await self.yf.get_news(ticker)
        if articles:
            await self.cache.set_news(ticker, "yfinance", articles)
            return [NewsArticle(**a) for a in articles]

        return []
