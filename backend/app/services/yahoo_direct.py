"""
Direct Yahoo Finance client using the v8 chart API.
Bypasses yfinance library which gets rate-limited on quoteSummary.
The v8/finance/chart endpoint works without auth/crumb.
"""
import logging
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://query1.finance.yahoo.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
}


async def fetch_chart(ticker: str, range_: str = "6mo", interval: str = "1d") -> dict | None:
    """
    Fetch chart data from Yahoo v8 API.
    Returns dict with 'meta' (quote info) and 'bars' (OHLCV list).
    """
    url = f"{BASE_URL}/v8/finance/chart/{ticker}"
    params = {
        "range": range_,
        "interval": interval,
        "includePrePost": "false",
        "events": "div,splits",
    }
    try:
        async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=15) as client:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                logger.warning(f"Yahoo chart API returned {resp.status_code} for {ticker}")
                return None
            data = resp.json()
            chart = data.get("chart", {})
            if chart.get("error"):
                logger.warning(f"Yahoo chart error for {ticker}: {chart['error']}")
                return None
            results = chart.get("result", [])
            if not results:
                return None
            return _parse_chart_result(results[0])
    except Exception as e:
        logger.error(f"Yahoo chart fetch error for {ticker}: {e}")
        return None


def _parse_chart_result(result: dict) -> dict:
    meta = result.get("meta", {})
    timestamps = result.get("timestamp", [])
    indicators = result.get("indicators", {})
    quotes = indicators.get("quote", [{}])[0]

    bars = []
    for i, ts in enumerate(timestamps):
        o = quotes.get("open", [None])[i]
        h = quotes.get("high", [None])[i]
        l = quotes.get("low", [None])[i]
        c = quotes.get("close", [None])[i]
        v = quotes.get("volume", [None])[i]
        if o is None or h is None or l is None or c is None:
            continue
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        bars.append({
            "time": dt.isoformat(),
            "open": round(o, 2),
            "high": round(h, 2),
            "low": round(l, 2),
            "close": round(c, 2),
            "volume": int(v or 0),
        })

    price = meta.get("regularMarketPrice")
    prev_close = meta.get("chartPreviousClose")
    change = round(price - prev_close, 2) if price and prev_close else None
    change_pct = round((change / prev_close) * 100, 2) if change and prev_close else None

    return {
        "meta": {
            "ticker": meta.get("symbol", ""),
            "shortName": meta.get("shortName"),
            "longName": meta.get("longName"),
            "currency": meta.get("currency"),
            "exchange": meta.get("exchangeName"),
            "instrumentType": meta.get("instrumentType"),
            "regularMarketPrice": price,
            "chartPreviousClose": prev_close,
            "change": change,
            "changePercent": change_pct,
            "regularMarketVolume": meta.get("regularMarketVolume"),
            "regularMarketDayHigh": meta.get("regularMarketDayHigh"),
            "regularMarketDayLow": meta.get("regularMarketDayLow"),
            "fiftyTwoWeekHigh": meta.get("fiftyTwoWeekHigh"),
            "fiftyTwoWeekLow": meta.get("fiftyTwoWeekLow"),
        },
        "bars": bars,
    }


async def fetch_quote_via_chart(ticker: str) -> dict | None:
    """Get basic quote info using the chart API metadata."""
    result = await fetch_chart(ticker, range_="1d", interval="1d")
    if not result:
        return None
    return result["meta"]


async def search_symbols(query: str, max_results: int = 8) -> list[dict]:
    """
    Search for tickers by symbol or company name using Yahoo Finance search API.
    Returns list of dicts with 'symbol', 'name', 'exchange', and 'type' keys.
    """
    url = f"{BASE_URL}/v1/finance/search"
    params = {
        "q": query,
        "quotesCount": max_results,
        "newsCount": 0,
        "listsCount": 0,
        "enableFuzzyQuery": "true",
    }
    try:
        async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=10) as client:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                logger.warning(f"Yahoo search API returned {resp.status_code} for query '{query}'")
                return []
            data = resp.json()
            quotes = data.get("quotes", [])
            results = []
            for q in quotes:
                symbol = q.get("symbol", "")
                # Skip non-US tickers (contain dots like "AAPL.L") unless they're common ETFs
                if "." in symbol:
                    continue
                results.append({
                    "symbol": symbol,
                    "name": q.get("longname") or q.get("shortname") or "",
                    "exchange": q.get("exchDisp", ""),
                    "type": q.get("quoteType", ""),
                })
            return results[:max_results]
    except Exception as e:
        logger.error(f"Yahoo search error for query '{query}': {e}")
        return []
