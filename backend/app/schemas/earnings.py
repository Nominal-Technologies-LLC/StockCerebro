from pydantic import BaseModel


class QuarterlyEarnings(BaseModel):
    period_end: str  # "2024-12-28"
    period_label: str  # "Q4 2024"
    revenue: float | None = None
    net_income: float | None = None
    operating_income: float | None = None
    operating_margin: float | None = None  # percentage, e.g. 35.2
    revenue_qoq: float | None = None  # % change vs prior quarter
    net_income_qoq: float | None = None
    revenue_yoy: float | None = None  # % change vs same quarter last year
    net_income_yoy: float | None = None
    filing_url: str | None = None  # SEC.gov direct link to 10-Q
    filing_date: str | None = None  # Date the 10-Q was filed


class EarningsResponse(BaseModel):
    ticker: str
    quarters: list[QuarterlyEarnings] = []  # most recent first, up to 8
    data_source: str = "unknown"  # "finnhub", "edgar", "yfinance"
