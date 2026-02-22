from pydantic import BaseModel


class SymbolSearchResult(BaseModel):
    symbol: str
    name: str
    exchange: str = ""
    type: str = ""


class CompanyOverview(BaseModel):
    ticker: str
    name: str | None = None
    sector: str | None = None
    industry: str | None = None
    is_etf: bool = False
    market_cap: float | None = None
    price: float | None = None
    change: float | None = None
    change_percent: float | None = None
    volume: int | None = None
    avg_volume: int | None = None
    day_high: float | None = None
    day_low: float | None = None
    fifty_two_week_high: float | None = None
    fifty_two_week_low: float | None = None
    pe_ratio: float | None = None
    forward_pe: float | None = None
    dividend_yield: float | None = None
    beta: float | None = None
    description: str | None = None
    website: str | None = None
    logo_url: str | None = None


class OHLCVBar(BaseModel):
    time: str  # ISO date or unix timestamp
    open: float
    high: float
    low: float
    close: float
    volume: int


class ChartData(BaseModel):
    ticker: str
    period: str
    interval: str
    bars: list[OHLCVBar]
