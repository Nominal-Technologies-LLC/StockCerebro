import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.earnings import EarningsResponse, QuarterlyEarnings
from app.schemas.fundamental import FundamentalAnalysis
from app.schemas.macro_risk import MacroRiskResponse
from app.schemas.scorecard import NewsArticle, Scorecard
from app.schemas.stock import ChartData, CompanyOverview, OHLCVBar
from app.schemas.technical import TechnicalAnalysis
from app.services.cache_manager import CacheManager
from app.services.yahoo_direct import fetch_chart, fetch_quote_via_chart
from app.services.yfinance_service import YFinanceService
from app.services.edgar_service import EdgarService
from app.services.claude_service import ClaudeService
from app.services.finnhub_service import FinnhubService

logger = logging.getLogger(__name__)


def _epoch_to_iso(epoch) -> str:
    """Convert a unix epoch timestamp to an ISO 8601 UTC string."""
    if epoch is None:
        return ""
    try:
        ts = int(epoch)
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, TypeError, OSError):
        return str(epoch)


def _pct_change(current, prior) -> float | None:
    """Compute percentage change, handling None and zero."""
    if current is None or prior is None or prior == 0:
        return None
    return ((current - prior) / abs(prior)) * 100


def _period_to_label(period_end: str) -> str:
    """Convert a period end date like '2024-12-28' to 'Q4 2024'."""
    try:
        dt = datetime.strptime(period_end, "%Y-%m-%d")
        month = dt.month
        year = dt.year
        if month <= 3:
            return f"Q1 {year}"
        elif month <= 6:
            return f"Q2 {year}"
        elif month <= 9:
            return f"Q3 {year}"
        else:
            return f"Q4 {year}"
    except (ValueError, TypeError):
        return period_end


def _find_yoy_index(periods: list[str], current_idx: int, quarterly: dict) -> int | None:
    """Find the index of the same quarter from ~1 year ago (within 30-day tolerance)."""
    if current_idx >= len(periods):
        return None
    try:
        current_date = datetime.strptime(periods[current_idx], "%Y-%m-%d")
        target_date = current_date - timedelta(days=365)

        best_idx = None
        best_diff = 40  # max tolerance in days
        for j in range(current_idx + 1, len(periods)):
            try:
                candidate = datetime.strptime(periods[j], "%Y-%m-%d")
                diff = abs((candidate - target_date).days)
                if diff < best_diff:
                    best_diff = diff
                    best_idx = j
            except (ValueError, TypeError):
                continue
        return best_idx
    except (ValueError, TypeError):
        return None


def _match_filing(period_end: str, filing_map: dict[str, dict]) -> dict | None:
    """Match a quarterly period end date to a filing, with 5-day fuzzy matching."""
    # Exact match first
    if period_end in filing_map:
        return filing_map[period_end]

    # Fuzzy match within 5 days
    try:
        target = datetime.strptime(period_end, "%Y-%m-%d")
        best_match = None
        best_diff = 6  # max 5 days
        for date_str, filing in filing_map.items():
            try:
                candidate = datetime.strptime(date_str, "%Y-%m-%d")
                diff = abs((candidate - target).days)
                if diff < best_diff:
                    best_diff = diff
                    best_match = filing
            except (ValueError, TypeError):
                continue
        return best_match
    except (ValueError, TypeError):
        return None


class DataAggregator:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.cache = CacheManager(db)
        self.yf = YFinanceService()
        self.finnhub = FinnhubService()
        self.edgar = EdgarService()
        self.claude = ClaudeService()

    async def get_company_overview(self, ticker: str) -> CompanyOverview | None:
        # Check cache first
        cached_info = await self.cache.get_company(ticker)
        if cached_info:
            return self._build_overview(ticker, cached_info)

        # Primary: Yahoo v8 chart API (reliable, no auth needed)
        quote = await fetch_quote_via_chart(ticker)
        if quote:
            # Supplement with Finnhub profile + basic financials concurrently
            finnhub_profile, finnhub_metrics = await asyncio.gather(
                self.finnhub.get_company_profile(ticker),
                self.finnhub.get_basic_financials(ticker),
                return_exceptions=True,
            )
            if isinstance(finnhub_profile, dict) and finnhub_profile:
                quote["sector"] = finnhub_profile.get("finnhubIndustry")
                quote["industry"] = finnhub_profile.get("finnhubIndustry")
                quote["marketCap"] = finnhub_profile.get("marketCapitalization")
                if quote["marketCap"]:
                    quote["marketCap"] = quote["marketCap"] * 1_000_000  # Finnhub returns in millions
                quote["website"] = finnhub_profile.get("weburl")
                quote["logo_url"] = finnhub_profile.get("logo")

            if isinstance(finnhub_metrics, dict) and finnhub_metrics:
                metric = finnhub_metrics.get("metric", {})
                if metric.get("peBasicExclExtraTTM"):
                    quote["trailingPE"] = metric["peBasicExclExtraTTM"]
                if metric.get("forwardPE"):
                    quote["forwardPE"] = metric["forwardPE"]
                if metric.get("beta"):
                    quote["beta"] = metric["beta"]
                if metric.get("dividendYieldIndicatedAnnual"):
                    quote["dividendYield"] = metric["dividendYieldIndicatedAnnual"] / 100
                if metric.get("10DayAverageTradingVolume"):
                    quote["averageVolume"] = int(metric["10DayAverageTradingVolume"] * 1_000_000)

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
            "averageVolume": quote.get("averageVolume"),
            "regularMarketDayHigh": quote.get("regularMarketDayHigh"),
            "regularMarketDayLow": quote.get("regularMarketDayLow"),
            "fiftyTwoWeekHigh": quote.get("fiftyTwoWeekHigh"),
            "fiftyTwoWeekLow": quote.get("fiftyTwoWeekLow"),
            "website": quote.get("website"),
            "logo_url": quote.get("logo_url"),
            "instrumentType": quote.get("instrumentType"),
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

        instrument_type = (info.get("instrumentType") or "").upper()
        is_etf = instrument_type in ("ETF", "MUTUALFUND")

        # Ensure volumes are integers (Finnhub can return floats with fractional parts)
        volume = info.get("volume") or info.get("regularMarketVolume")
        if volume is not None:
            volume = int(volume)

        avg_volume = info.get("averageVolume")
        if avg_volume is not None:
            avg_volume = int(avg_volume)

        return CompanyOverview(
            ticker=ticker,
            name=info.get("shortName") or info.get("longName"),
            sector=info.get("sector"),
            industry=info.get("industry"),
            is_etf=is_etf,
            market_cap=info.get("marketCap"),
            price=price,
            change=change,
            change_percent=change_pct,
            volume=volume,
            avg_volume=avg_volume,
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
            # Ensure bars are sorted by timestamp
            bars.sort(key=lambda b: b.time)
            return ChartData(ticker=ticker, period=period, interval=interval, bars=bars)

        # Primary: Yahoo v8 chart API (reliable)
        result = await fetch_chart(ticker, range_=period, interval=interval)
        if result and result.get("bars"):
            raw_bars = result["bars"]
            await self.cache.set_prices(ticker, interval, period, {"bars": raw_bars})
            bars = [OHLCVBar(**b) for b in raw_bars]
            # Ensure bars are sorted by timestamp
            bars.sort(key=lambda b: b.time)
            return ChartData(ticker=ticker, period=period, interval=interval, bars=bars)

        # Fallback: yfinance
        raw_bars = await self.yf.get_history(ticker, period, interval)
        if raw_bars:
            await self.cache.set_prices(ticker, interval, period, {"bars": raw_bars})
            bars = [OHLCVBar(**b) for b in raw_bars]
            # Ensure bars are sorted by timestamp
            bars.sort(key=lambda b: b.time)
            return ChartData(ticker=ticker, period=period, interval=interval, bars=bars)

        return None

    async def get_fundamental_analysis(self, ticker: str) -> FundamentalAnalysis | None:
        # Check analysis cache
        cached = await self.cache.get_analysis(ticker, "fundamental")
        if cached:
            return FundamentalAnalysis(**cached)

        from app.analysis.fundamental_analyzer import FundamentalAnalyzer
        analyzer = FundamentalAnalyzer(self.db, self.cache, self.yf, self.finnhub, self.edgar)
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
                    "published": _epoch_to_iso(n.get("datetime")),
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

    # ── Earnings ─────────────────────────────────────────────────────

    async def get_earnings(self, ticker: str) -> EarningsResponse | None:
        # Check analysis cache (24h TTL)
        cached = await self.cache.get_analysis(ticker, "earnings", ttl=86400)
        if cached:
            return EarningsResponse(**cached)

        # Reuse the quarterly income pipeline from FundamentalAnalyzer
        from app.analysis.fundamental_analyzer import FundamentalAnalyzer
        analyzer = FundamentalAnalyzer(self.db, self.cache, self.yf, self.finnhub, self.edgar)
        quarterly = await analyzer._get_quarterly_income(ticker)

        if not quarterly or len(quarterly) < 1:
            return None

        # Determine data source from cache
        data_source = "unknown"
        for source in ("finnhub", "edgar"):
            src_cached = await self.cache.get_fundamental(ticker, "quarterly_income", source=source)
            if src_cached and len(src_cached) >= 1:
                data_source = source
                break

        # Get SEC filing URLs (best-effort)
        filing_map = await self._get_filing_urls(ticker)

        # Build quarter list sorted most-recent-first
        periods = sorted(quarterly.keys(), reverse=True)[:8]

        quarters: list[QuarterlyEarnings] = []
        for i, period in enumerate(periods):
            q_data = quarterly[period]
            revenue = q_data.get("Total Revenue") or q_data.get("TotalRevenue")
            net_income = q_data.get("Net Income") or q_data.get("NetIncome")
            op_income = q_data.get("Operating Income") or q_data.get("OperatingIncome") or q_data.get("EBIT")

            op_margin = None
            if revenue and op_income and revenue != 0:
                op_margin = round((op_income / revenue) * 100, 2)

            # QoQ deltas (compare to next item in list, which is the prior quarter)
            rev_qoq = None
            ni_qoq = None
            if i + 1 < len(periods):
                prior = quarterly[periods[i + 1]]
                prior_rev = prior.get("Total Revenue") or prior.get("TotalRevenue")
                prior_ni = prior.get("Net Income") or prior.get("NetIncome")
                rev_qoq = _pct_change(revenue, prior_rev)
                ni_qoq = _pct_change(net_income, prior_ni)

            # YoY deltas (find same quarter from ~4 periods ago)
            rev_yoy = None
            ni_yoy = None
            yoy_idx = _find_yoy_index(periods, i, quarterly)
            if yoy_idx is not None:
                yago = quarterly[periods[yoy_idx]]
                yago_rev = yago.get("Total Revenue") or yago.get("TotalRevenue")
                yago_ni = yago.get("Net Income") or yago.get("NetIncome")
                rev_yoy = _pct_change(revenue, yago_rev)
                ni_yoy = _pct_change(net_income, yago_ni)

            # Match SEC filing
            filing_url = None
            filing_date = None
            if filing_map:
                match = _match_filing(period, filing_map)
                if match:
                    filing_url = match.get("url")
                    filing_date = match.get("filed")

            quarters.append(QuarterlyEarnings(
                period_end=period,
                period_label=_period_to_label(period),
                revenue=revenue,
                net_income=net_income,
                operating_income=op_income,
                operating_margin=op_margin,
                revenue_qoq=round(rev_qoq, 2) if rev_qoq is not None else None,
                net_income_qoq=round(ni_qoq, 2) if ni_qoq is not None else None,
                revenue_yoy=round(rev_yoy, 2) if rev_yoy is not None else None,
                net_income_yoy=round(ni_yoy, 2) if ni_yoy is not None else None,
                filing_url=filing_url,
                filing_date=filing_date,
            ))

        result = EarningsResponse(ticker=ticker, quarters=quarters, data_source=data_source)
        await self.cache.set_analysis(ticker, "earnings", result.model_dump())
        return result

    async def _get_filing_urls(self, ticker: str) -> dict[str, dict] | None:
        """
        Get SEC 10-Q/10-K filing URLs mapped by report date.
        Returns dict like {"2024-12-28": {"url": "...", "filed": "2025-01-30"}}
        """
        # Check cache
        cached = await self.cache.get_fundamental(ticker, "filing_urls", source="edgar", ttl=86400)
        if cached:
            return cached

        try:
            # Get CIK (reuses existing cache)
            cik_cache = await self.cache.get_fundamental(ticker, "cik_mapping", source="edgar", ttl=604800)
            cik = cik_cache.get("cik") if cik_cache else None

            if not cik:
                cik = await self.edgar.lookup_cik(ticker)
                if cik:
                    await self.cache.set_fundamental(ticker, "cik_mapping", "edgar", {"cik": cik})

            if not cik:
                return None

            submissions = await self.edgar.get_company_submissions(cik)
            if not submissions:
                return None

            recent = submissions.get("filings", {}).get("recent", {})
            forms = recent.get("form", [])
            report_dates = recent.get("reportDate", [])
            filing_dates = recent.get("filingDate", [])
            accession_numbers = recent.get("accessionNumber", [])
            primary_docs = recent.get("primaryDocument", [])

            filing_map = {}
            for i, form in enumerate(forms):
                if form not in ("10-Q", "10-K"):
                    continue
                if i >= len(report_dates) or i >= len(accession_numbers) or i >= len(primary_docs):
                    continue

                report_date = report_dates[i]
                accession_no = accession_numbers[i]
                primary_doc = primary_docs[i]
                filed = filing_dates[i] if i < len(filing_dates) else None

                # Build SEC URL: remove hyphens from accession number for path
                accession_no_dashes = accession_no.replace("-", "")
                url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_no_dashes}/{primary_doc}"

                filing_map[report_date] = {
                    "url": url,
                    "filed": filed,
                    "form": form,
                }

            if filing_map:
                await self.cache.set_fundamental(ticker, "filing_urls", "edgar", filing_map)

            return filing_map if filing_map else None

        except Exception as e:
            logger.warning(f"Failed to get filing URLs for {ticker}: {e}")
            return None

    # ── Macro Risk ────────────────────────────────────────────────────

    async def get_macro_risk(self, ticker: str) -> MacroRiskResponse | None:
        from app.config import get_settings

        settings = get_settings()

        # Check cache (6h TTL)
        cached = await self.cache.get_analysis(ticker, "macro_risk", ttl=settings.macro_risk_cache_ttl)
        if cached:
            return MacroRiskResponse(**cached)

        # If Claude not configured, return error response
        if not self.claude.is_configured:
            error_resp = MacroRiskResponse(
                ticker=ticker,
                error="Macro analysis unavailable: ANTHROPIC_API_KEY not configured",
            )
            # Cache briefly (5 min) so we don't spam logs
            await self.cache.set_analysis(ticker, "macro_risk", error_resp.model_dump())
            return error_resp

        # Gather company context concurrently
        profile_task = self.finnhub.get_company_profile(ticker)
        metrics_task = self.finnhub.get_basic_financials(ticker)
        news_task = self.finnhub.get_news(ticker)

        profile, metrics, news = await asyncio.gather(
            profile_task, metrics_task, news_task,
            return_exceptions=True,
        )

        # Extract context
        company_name = None
        sector = None
        market_cap = None
        if isinstance(profile, dict) and profile:
            company_name = profile.get("name")
            sector = profile.get("finnhubIndustry")
            mc = profile.get("marketCapitalization")
            if mc:
                market_cap = mc * 1_000_000

        key_metrics = {}
        if isinstance(metrics, dict) and metrics:
            m = metrics.get("metric", {})
            for key in ("peBasicExclExtraTTM", "revenueGrowthTTMYoy", "epsGrowth5Y",
                         "dividendYieldIndicatedAnnual", "beta", "netMarginTTM"):
                if m.get(key) is not None:
                    key_metrics[key] = m[key]

        news_headlines = []
        if isinstance(news, list):
            news_headlines = [n.get("headline", "") for n in news[:10] if n.get("headline")]

        result = await self.claude.get_macro_risk(
            ticker=ticker,
            company_name=company_name,
            sector=sector,
            market_cap=market_cap,
            news_headlines=news_headlines,
            metrics=key_metrics,
        )

        if result is None:
            result = MacroRiskResponse(
                ticker=ticker,
                company_name=company_name,
                sector=sector,
                error="Macro analysis failed: Claude API call unsuccessful",
            )

        await self.cache.set_analysis(ticker, "macro_risk", result.model_dump())
        return result
