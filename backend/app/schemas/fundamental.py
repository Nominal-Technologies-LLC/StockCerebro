from pydantic import BaseModel


class MetricScore(BaseModel):
    value: float | None = None
    score: float = 0  # 0-100
    grade: str = "N/A"
    description: str = ""


class ValuationMetrics(BaseModel):
    pe_ratio: MetricScore = MetricScore()
    peg_ratio: MetricScore = MetricScore()
    pb_ratio: MetricScore = MetricScore()
    ps_ratio: MetricScore = MetricScore()
    composite_score: float = 0
    grade: str = "N/A"


class GrowthMetrics(BaseModel):
    revenue_yoy: MetricScore = MetricScore()
    earnings_yoy: MetricScore = MetricScore()
    revenue_trend: MetricScore = MetricScore()
    analyst_growth_est: MetricScore = MetricScore()
    composite_score: float = 0
    grade: str = "N/A"


class HealthMetrics(BaseModel):
    # Standard metrics (non-financial companies)
    debt_to_equity: MetricScore = MetricScore()
    current_ratio: MetricScore = MetricScore()
    interest_coverage: MetricScore = MetricScore()
    fcf_yield: MetricScore = MetricScore()
    ocf_trend: MetricScore = MetricScore()
    # Bank/financial metrics (populated for Financial Services sector)
    roe: MetricScore = MetricScore()
    roa: MetricScore = MetricScore()
    payout_ratio: MetricScore = MetricScore()
    composite_score: float = 0
    grade: str = "N/A"


class ProfitabilityMetrics(BaseModel):
    gross_margin: MetricScore = MetricScore()
    operating_margin: MetricScore = MetricScore()
    net_margin: MetricScore = MetricScore()
    margin_trend: MetricScore = MetricScore()
    composite_score: float = 0
    grade: str = "N/A"


class FundamentalAnalysis(BaseModel):
    ticker: str
    valuation: ValuationMetrics = ValuationMetrics()
    growth: GrowthMetrics = GrowthMetrics()
    health: HealthMetrics = HealthMetrics()
    profitability: ProfitabilityMetrics = ProfitabilityMetrics()
    overall_score: float = 0
    grade: str = "N/A"
    confidence: float = 0  # 0-1, how much data was available
    data_gaps: list[str] = []
