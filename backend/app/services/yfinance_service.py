import logging
import time
from concurrent.futures import ThreadPoolExecutor
from functools import partial

import yfinance as yf

logger = logging.getLogger(__name__)

# Thread pool for running yfinance (synchronous) calls
_executor = ThreadPoolExecutor(max_workers=2)

# Simple rate limiting: track last call time
_last_call_time = 0.0
_min_interval = 1.0  # seconds between yfinance calls


def _rate_limit():
    global _last_call_time
    now = time.monotonic()
    elapsed = now - _last_call_time
    if elapsed < _min_interval:
        time.sleep(_min_interval - elapsed)
    _last_call_time = time.monotonic()


def _retry(func, max_retries=3, base_delay=2.0):
    """Retry wrapper with exponential backoff for rate-limit errors."""
    for attempt in range(max_retries):
        try:
            _rate_limit()
            result = func()
            return result
        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "too many requests" in err_str or "expecting value" in err_str:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Rate limited (attempt {attempt + 1}/{max_retries}), waiting {delay}s...")
                time.sleep(delay)
                if attempt == max_retries - 1:
                    logger.error(f"Failed after {max_retries} retries: {e}")
                    raise
            else:
                raise


async def _run_sync(func, *args, **kwargs):
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, partial(func, *args, **kwargs))


def _get_ticker_info(ticker_str: str) -> dict:
    try:
        ticker = yf.Ticker(ticker_str)

        def fetch():
            info = ticker.info
            if not info or not info.get("shortName"):
                return {}
            return info

        info = _retry(fetch)
        return info or {}
    except Exception as e:
        logger.error(f"yfinance info error for {ticker_str}: {e}")
        return {}


def _get_history(ticker_str: str, period: str, interval: str) -> list[dict]:
    try:
        ticker = yf.Ticker(ticker_str)

        def fetch():
            return ticker.history(period=period, interval=interval)

        df = _retry(fetch)
        if df is None or df.empty:
            return []
        bars = []
        for idx, row in df.iterrows():
            ts = idx.isoformat() if hasattr(idx, 'isoformat') else str(idx)
            bars.append({
                "time": ts,
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"]),
            })
        return bars
    except Exception as e:
        logger.error(f"yfinance history error for {ticker_str}: {e}")
        return []


def _get_financials(ticker_str: str) -> dict:
    try:
        ticker = yf.Ticker(ticker_str)
        result = {}

        # Income statement
        def fetch_inc():
            return ticker.income_stmt
        inc = _retry(fetch_inc)
        if inc is not None and not inc.empty:
            result["income_statement"] = {
                str(col): {str(k): _safe_float(v) for k, v in inc[col].items()}
                for col in inc.columns
            }

        # Balance sheet
        def fetch_bs():
            return ticker.balance_sheet
        bs = _retry(fetch_bs)
        if bs is not None and not bs.empty:
            result["balance_sheet"] = {
                str(col): {str(k): _safe_float(v) for k, v in bs[col].items()}
                for col in bs.columns
            }

        # Cash flow
        def fetch_cf():
            return ticker.cashflow
        cf = _retry(fetch_cf)
        if cf is not None and not cf.empty:
            result["cash_flow"] = {
                str(col): {str(k): _safe_float(v) for k, v in cf[col].items()}
                for col in cf.columns
            }

        # Quarterly income statement
        def fetch_q_inc():
            return ticker.quarterly_income_stmt
        q_inc = _retry(fetch_q_inc)
        if q_inc is not None and not q_inc.empty:
            result["quarterly_income"] = {
                str(col): {str(k): _safe_float(v) for k, v in q_inc[col].items()}
                for col in q_inc.columns
            }

        # Quarterly balance sheet
        def fetch_q_bs():
            return ticker.quarterly_balance_sheet
        q_bs = _retry(fetch_q_bs)
        if q_bs is not None and not q_bs.empty:
            result["quarterly_balance_sheet"] = {
                str(col): {str(k): _safe_float(v) for k, v in q_bs[col].items()}
                for col in q_bs.columns
            }

        return result
    except Exception as e:
        logger.error(f"yfinance financials error for {ticker_str}: {e}")
        return {}


def _get_news(ticker_str: str) -> list[dict]:
    try:
        ticker = yf.Ticker(ticker_str)

        def fetch():
            return ticker.news

        news = _retry(fetch)
        if not news:
            return []
        articles = []
        for item in news[:20]:
            content = item.get("content", {}) if isinstance(item, dict) else {}
            articles.append({
                "title": content.get("title", item.get("title", "")),
                "url": content.get("canonicalUrl", {}).get("url", item.get("link", "")),
                "source": content.get("provider", {}).get("displayName", ""),
                "published": content.get("pubDate", item.get("providerPublishTime", "")),
                "summary": content.get("summary", ""),
            })
        return articles
    except Exception as e:
        logger.error(f"yfinance news error for {ticker_str}: {e}")
        return []


def _safe_float(val) -> float | None:
    if val is None:
        return None
    try:
        import math
        f = float(val)
        return None if math.isnan(f) or math.isinf(f) else f
    except (ValueError, TypeError):
        return None


class YFinanceService:
    async def get_info(self, ticker: str) -> dict:
        return await _run_sync(_get_ticker_info, ticker)

    async def get_history(self, ticker: str, period: str = "6mo", interval: str = "1d") -> list[dict]:
        return await _run_sync(_get_history, ticker, period, interval)

    async def get_financials(self, ticker: str) -> dict:
        return await _run_sync(_get_financials, ticker)

    async def get_news(self, ticker: str) -> list[dict]:
        return await _run_sync(_get_news, ticker)
