"""
Scorecard engine - combines fundamental + technical scores, generates signals,
swing trade assessment.

technical_consensus = daily*0.50 + weekly*0.35 + hourly*0.15
overall_score = fundamental*0.50 + technical_consensus*0.50

Override rules prevent recommending buys when fundamentals and technicals strongly disagree.
"""
import logging

from app.analysis.grading import score_to_grade, score_to_signal
from app.schemas.scorecard import Scorecard, ScoreBreakdown, SwingTradeAssessment

logger = logging.getLogger(__name__)


class ScorecardEngine:
    def __init__(self, aggregator):
        self.aggregator = aggregator

    async def generate(self, ticker: str) -> Scorecard | None:
        # Fetch all analyses
        fundamental = await self.aggregator.get_fundamental_analysis(ticker)
        tech_daily = await self.aggregator.get_technical_analysis(ticker, "daily")
        tech_weekly = await self.aggregator.get_technical_analysis(ticker, "weekly")
        tech_hourly = await self.aggregator.get_technical_analysis(ticker, "hourly")

        if not tech_daily:
            return None

        # tech_daily is guaranteed to exist here due to early return above
        daily_score = tech_daily.overall_score
        weekly_score = tech_weekly.overall_score if tech_weekly else 50
        hourly_score = tech_hourly.overall_score if tech_hourly else 50
        tech_consensus = daily_score * 0.50 + weekly_score * 0.35 + hourly_score * 0.15

        # Determine if fundamentals are meaningful (not an ETF with all N/A)
        has_fundamentals = (
            fundamental is not None
            and fundamental.confidence > 0
            and fundamental.overall_score > 0
        )

        if has_fundamentals:
            fund_score = fundamental.overall_score
            overall = fund_score * 0.50 + tech_consensus * 0.50
            fund_weight = 0.50
            tech_weight = 0.50
        else:
            # ETF or no fundamental data: 100% technical
            fund_score = 0
            overall = tech_consensus
            fund_weight = 0.0
            tech_weight = 1.0
            fundamental = None  # Don't include empty fundamental data

        signal = score_to_signal(overall)

        # Override rules (only when fundamentals are available)
        override_applied = False
        override_reason = ""

        if has_fundamentals:
            if fund_score < 30 and tech_consensus > 70:
                if signal in ("STRONG BUY", "BUY"):
                    signal = "HOLD"
                    override_applied = True
                    override_reason = "Weak fundamentals override bullish technicals"
            elif fund_score > 70 and tech_consensus < 30:
                if signal in ("STRONG SELL", "SELL"):
                    signal = "HOLD"
                    override_applied = True
                    override_reason = "Strong fundamentals override bearish technicals"

        # Swing trade assessment
        swing = self._assess_swing_trade(tech_daily, fund_score if has_fundamentals else 50)

        # Confidence
        if has_fundamentals:
            confidence = fundamental.confidence
        else:
            confidence = 0.7  # Technical-only has decent confidence

        breakdown = ScoreBreakdown(
            fundamental_score=round(fund_score, 1),
            fundamental_weight=round(fund_weight, 2),
            technical_daily_score=round(daily_score, 1),
            technical_weekly_score=round(weekly_score, 1),
            technical_hourly_score=round(hourly_score, 1),
            technical_consensus=round(tech_consensus, 1),
            technical_weight=round(tech_weight, 2),
        )

        return Scorecard(
            ticker=ticker,
            overall_score=round(overall, 1),
            grade=score_to_grade(overall),
            signal=signal,
            score_breakdown=breakdown,
            fundamental=fundamental,
            technical_daily=tech_daily,
            swing_trade=swing,
            confidence=round(confidence, 2),
            override_applied=override_applied,
            override_reason=override_reason,
        )

    def _assess_swing_trade(self, tech_daily, fund_score: float) -> SwingTradeAssessment:
        if not tech_daily or not tech_daily.support_resistance:
            return SwingTradeAssessment()

        sr = tech_daily.support_resistance
        price = tech_daily.current_price
        if not price or not sr.nearest_support or not sr.nearest_resistance:
            return SwingTradeAssessment(reasoning=["Insufficient support/resistance data"])

        support = sr.nearest_support
        resistance = sr.nearest_resistance

        # Entry zone: near support
        entry_low = support * 0.995
        entry_high = support * 1.02

        # Stop loss: 2% below support
        stop_loss = support * 0.98

        # Target: nearest resistance
        target = resistance

        # Risk/reward
        risk = price - stop_loss
        reward = target - price
        if risk <= 0:
            return SwingTradeAssessment(
                reasoning=["Price at or below stop loss level - excessive risk"]
            )

        rr_ratio = reward / risk

        # Determine opportunity rating
        reasoning = []
        if rr_ratio >= 3:
            rating = "Strong"
            reasoning.append(f"Excellent risk/reward ratio of {rr_ratio:.1f}:1")
        elif rr_ratio >= 2:
            rating = "Strong"
            reasoning.append(f"Good risk/reward ratio of {rr_ratio:.1f}:1")
        elif rr_ratio >= 1.5:
            rating = "Moderate"
            reasoning.append(f"Acceptable risk/reward ratio of {rr_ratio:.1f}:1")
        elif rr_ratio >= 1:
            rating = "Weak"
            reasoning.append(f"Marginal risk/reward ratio of {rr_ratio:.1f}:1")
        else:
            rating = "None"
            reasoning.append(f"Poor risk/reward ratio of {rr_ratio:.1f}:1")

        # Adjust based on RSI
        if tech_daily.rsi and tech_daily.rsi.value:
            if tech_daily.rsi.value < 35:
                reasoning.append("RSI indicates oversold - favorable entry")
            elif tech_daily.rsi.value > 65:
                reasoning.append("RSI elevated - wait for pullback")
                if rating == "Strong":
                    rating = "Moderate"

        # Adjust based on fundamentals
        if fund_score >= 70:
            reasoning.append("Strong fundamental backing")
        elif fund_score < 40:
            reasoning.append("Weak fundamentals add risk")
            if rating == "Strong":
                rating = "Moderate"

        return SwingTradeAssessment(
            opportunity_rating=rating,
            entry_zone=[round(entry_low, 2), round(entry_high, 2)],
            stop_loss=round(stop_loss, 2),
            target_price=round(target, 2),
            risk_reward_ratio=round(rr_ratio, 2),
            reasoning=reasoning,
        )
