from pydantic import BaseModel

from app.schemas.fundamental import FundamentalAnalysis
from app.schemas.technical import TechnicalAnalysis


class SwingTradeAssessment(BaseModel):
    opportunity_rating: str = "None"  # Strong, Moderate, Weak, None
    entry_zone: list[float] = []  # [low, high]
    stop_loss: float | None = None
    target_price: float | None = None
    risk_reward_ratio: float | None = None
    reasoning: list[str] = []


class ScoreBreakdown(BaseModel):
    fundamental_score: float = 0
    fundamental_weight: float = 0.60
    technical_daily_score: float = 0
    technical_weekly_score: float = 0
    technical_hourly_score: float = 0
    technical_consensus: float = 0
    technical_weight: float = 0.40


class NewsArticle(BaseModel):
    title: str
    url: str
    source: str = ""
    published: str = ""
    summary: str = ""


class Scorecard(BaseModel):
    ticker: str
    overall_score: float = 0
    grade: str = "N/A"
    signal: str = "HOLD"  # STRONG BUY, BUY, HOLD, SELL, STRONG SELL
    score_breakdown: ScoreBreakdown = ScoreBreakdown()
    fundamental: FundamentalAnalysis | None = None
    technical_daily: TechnicalAnalysis | None = None
    swing_trade: SwingTradeAssessment = SwingTradeAssessment()
    confidence: float = 0
    override_applied: bool = False
    override_reason: str = ""
