"""
Fundamental analysis engine.
Computes four equally weighted (25% each) sub-scores:
- Valuation (PE 30%, PEG 35%, P/B 15%, P/S 20%)
- Growth (Revenue YoY 30%, Earnings YoY 30%, Revenue Trend 15%, Analyst Growth Est. 25%)
- Financial Health (D/E 25%, Current Ratio 15%, Quick Ratio 10%, FCF Yield 30%, OCF Trend 20%)
- Profitability (Gross Margin 20%, Operating Margin 30%, Net Margin 25%, Margin Trend 25%)

When a metric is missing (N/A), its weight is redistributed proportionally among
the metrics that do have data, so missing data never drags down the score.
"""
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.grading import clamp, score_to_grade
from app.analysis.peg_calculator import calculate_peg
from app.schemas.fundamental import (
    FundamentalAnalysis,
    GrowthMetrics,
    HealthMetrics,
    MetricScore,
    ProfitabilityMetrics,
    ValuationMetrics,
)
from app.services.cache_manager import CacheManager
from app.services.finnhub_service import FinnhubService
from app.services.yfinance_service import YFinanceService

logger = logging.getLogger(__name__)


def _weighted_average(items: list[tuple[MetricScore, float]]) -> float:
    """
    Compute weighted average, redistributing weight from missing metrics.
    items: list of (MetricScore, base_weight) tuples.
    A metric is considered missing if its value is None and its score is 0.
    """
    available = [(m, w) for m, w in items if m.value is not None or m.score > 0]
    if not available:
        return 0.0
    total_weight = sum(w for _, w in available)
    if total_weight == 0:
        return 0.0
    return sum(m.score * (w / total_weight) for m, w in available)


class FundamentalAnalyzer:
    def __init__(self, db: AsyncSession, cache: CacheManager, yf: YFinanceService, finnhub: FinnhubService):
        self.db = db
        self.cache = cache
        self.yf = yf
        self.finnhub = finnhub

    async def analyze(self, ticker: str) -> FundamentalAnalysis | None:
        # Fetch data
        info = await self._get_info(ticker)
        if not info:
            return None

        financials = await self._get_financials(ticker)
        data_gaps = []

        # Compute sub-scores
        valuation = self._score_valuation(info, financials, data_gaps)
        growth = self._score_growth(info, financials, data_gaps)
        health = self._score_health(info, financials, data_gaps)
        profitability = self._score_profitability(info, financials, data_gaps)

        # Overall: redistribute weight among sub-scores that have data
        sub_scores = [
            (valuation.composite_score, 0.25),
            (growth.composite_score, 0.25),
            (health.composite_score, 0.25),
            (profitability.composite_score, 0.25),
        ]
        available_subs = [(s, w) for s, w in sub_scores if s > 0]
        if available_subs:
            total_w = sum(w for _, w in available_subs)
            overall = sum(s * (w / total_w) for s, w in available_subs)
        else:
            overall = 0

        # Confidence based on data completeness
        total_metrics = 13
        available = total_metrics - len(data_gaps)
        confidence = available / total_metrics

        return FundamentalAnalysis(
            ticker=ticker,
            valuation=valuation,
            growth=growth,
            health=health,
            profitability=profitability,
            overall_score=round(overall, 1),
            grade=score_to_grade(overall),
            confidence=round(confidence, 2),
            data_gaps=data_gaps,
        )

    async def _get_info(self, ticker: str) -> dict | None:
        cached = await self.cache.get_company(ticker)
        info = cached or {}

        # Enrich with Finnhub basic financials (PE, PB, margins, etc.)
        finnhub_metrics = await self.finnhub.get_basic_financials(ticker)
        if finnhub_metrics:
            metric = finnhub_metrics.get("metric", {})
            # Map Finnhub metric keys to yfinance-compatible keys
            if not info.get("trailingPE") and metric.get("peBasicExclExtraTTM"):
                info["trailingPE"] = metric["peBasicExclExtraTTM"]
            if not info.get("priceToBook") and metric.get("pbAnnual"):
                info["priceToBook"] = metric["pbAnnual"]
            if not info.get("priceToSalesTrailing12Months") and metric.get("psTTM"):
                info["priceToSalesTrailing12Months"] = metric["psTTM"]
            if not info.get("debtToEquity") and metric.get("totalDebt/totalEquityAnnual"):
                info["debtToEquity"] = metric["totalDebt/totalEquityAnnual"]
            if not info.get("currentRatio") and metric.get("currentRatioAnnual"):
                info["currentRatio"] = metric["currentRatioAnnual"]
            if not info.get("quickRatio") and metric.get("quickRatioAnnual"):
                info["quickRatio"] = metric["quickRatioAnnual"]
            if not info.get("grossMargins") and metric.get("grossMarginTTM"):
                info["grossMargins"] = metric["grossMarginTTM"] / 100
            if not info.get("operatingMargins") and metric.get("operatingMarginTTM"):
                info["operatingMargins"] = metric["operatingMarginTTM"] / 100
            if not info.get("profitMargins") and metric.get("netProfitMarginTTM"):
                info["profitMargins"] = metric["netProfitMarginTTM"] / 100
            if not info.get("revenueGrowth") and metric.get("revenueGrowthTTMYoy"):
                info["revenueGrowth"] = metric["revenueGrowthTTMYoy"] / 100
            if not info.get("earningsGrowth") and metric.get("epsGrowthTTMYoy"):
                info["earningsGrowth"] = metric["epsGrowthTTMYoy"] / 100
            if not info.get("beta") and metric.get("beta"):
                info["beta"] = metric["beta"]
            if not info.get("dividendYield") and metric.get("dividendYieldIndicatedAnnual"):
                info["dividendYield"] = metric["dividendYieldIndicatedAnnual"] / 100
            if not info.get("freeCashflow") and metric.get("freeCashFlowTTM"):
                info["freeCashflow"] = metric["freeCashFlowTTM"]

        if not info:
            # Last resort: try yfinance
            yf_info = await self.yf.get_info(ticker)
            if yf_info:
                info = yf_info
                await self.cache.set_company(ticker, info)

        return info if info else None

    async def _get_financials(self, ticker: str) -> dict:
        cached = await self.cache.get_fundamental(ticker, "financials")
        if cached:
            return cached
        # Try yfinance (may fail with 429)
        data = await self.yf.get_financials(ticker)
        if data:
            await self.cache.set_fundamental(ticker, "financials", "yfinance", data)
        return data or {}

    # --- Valuation Scoring ---

    def _score_valuation(self, info: dict, financials: dict, data_gaps: list) -> ValuationMetrics:
        pe = self._score_pe(info, data_gaps)
        peg = self._score_peg(info, financials, data_gaps)
        pb = self._score_pb(info, data_gaps)
        ps = self._score_ps(info, data_gaps)

        composite = _weighted_average([(pe, 0.30), (peg, 0.35), (pb, 0.15), (ps, 0.20)])
        return ValuationMetrics(
            pe_ratio=pe,
            peg_ratio=peg,
            pb_ratio=pb,
            ps_ratio=ps,
            composite_score=round(composite, 1),
            grade=score_to_grade(composite),
        )

    def _score_pe(self, info: dict, data_gaps: list) -> MetricScore:
        pe = info.get("trailingPE")
        if pe is None:
            data_gaps.append("PE Ratio")
            return MetricScore(description="Not available")
        if pe < 0:
            score = 10
        elif pe < 10:
            score = 95
        elif pe < 15:
            score = 85
        elif pe < 20:
            score = 70
        elif pe < 25:
            score = 55
        elif pe < 30:
            score = 40
        elif pe < 40:
            score = 25
        else:
            score = 10
        return MetricScore(value=round(pe, 2), score=score, grade=score_to_grade(score), description=self._pe_desc(pe))

    def _pe_desc(self, pe: float) -> str:
        if pe < 0:
            return "Negative earnings"
        elif pe < 15:
            return "Undervalued"
        elif pe < 25:
            return "Fairly valued"
        else:
            return "Premium valuation"

    def _score_peg(self, info: dict, financials: dict, data_gaps: list) -> MetricScore:
        peg, method = calculate_peg(info, financials)
        if peg is None:
            data_gaps.append("PEG Ratio")
            return MetricScore(description="Cannot calculate PEG")

        if peg < 0:
            score = 10
        elif peg < 0.5:
            score = 95
        elif peg < 1.0:
            score = 85
        elif peg < 1.5:
            score = 65
        elif peg < 2.0:
            score = 45
        elif peg < 3.0:
            score = 25
        else:
            score = 10

        desc = f"PEG {peg:.2f} ({method})"
        if peg < 1:
            desc += " - Undervalued relative to growth"
        elif peg < 2:
            desc += " - Fairly valued for growth"
        else:
            desc += " - Expensive for growth rate"

        return MetricScore(value=round(peg, 2), score=score, grade=score_to_grade(score), description=desc)

    def _score_pb(self, info: dict, data_gaps: list) -> MetricScore:
        pb = info.get("priceToBook")
        if pb is None:
            data_gaps.append("P/B Ratio")
            return MetricScore(description="Not available")
        if pb < 1:
            score = 90
        elif pb < 2:
            score = 75
        elif pb < 3:
            score = 60
        elif pb < 5:
            score = 40
        else:
            score = 20
        return MetricScore(value=round(pb, 2), score=score, grade=score_to_grade(score))

    def _score_ps(self, info: dict, data_gaps: list) -> MetricScore:
        ps = info.get("priceToSalesTrailing12Months")
        if ps is None:
            data_gaps.append("P/S Ratio")
            return MetricScore(description="Not available")
        if ps < 1:
            score = 90
        elif ps < 3:
            score = 75
        elif ps < 5:
            score = 55
        elif ps < 10:
            score = 35
        else:
            score = 15
        return MetricScore(value=round(ps, 2), score=score, grade=score_to_grade(score))

    # --- Growth Scoring ---

    def _score_growth(self, info: dict, financials: dict, data_gaps: list) -> GrowthMetrics:
        rev_yoy = self._score_revenue_yoy(info, financials, data_gaps)
        earn_yoy = self._score_earnings_yoy(info, financials, data_gaps)
        rev_trend = self._score_revenue_trend(financials, data_gaps)
        analyst = self._score_analyst_growth(info, data_gaps)

        composite = _weighted_average([
            (rev_yoy, 0.30), (earn_yoy, 0.30), (rev_trend, 0.15), (analyst, 0.25),
        ])
        return GrowthMetrics(
            revenue_yoy=rev_yoy,
            earnings_yoy=earn_yoy,
            revenue_trend=rev_trend,
            analyst_growth_est=analyst,
            composite_score=round(composite, 1),
            grade=score_to_grade(composite),
        )

    def _score_revenue_yoy(self, info: dict, financials: dict, data_gaps: list) -> MetricScore:
        growth = info.get("revenueGrowth")
        if growth is None:
            growth = self._calc_yoy_growth(financials, "Total Revenue", "TotalRevenue")
        if growth is None:
            data_gaps.append("Revenue YoY")
            return MetricScore(description="Not available")
        pct = growth * 100
        score = self._growth_rate_score(pct)
        return MetricScore(value=round(pct, 1), score=score, grade=score_to_grade(score),
                           description=f"{pct:+.1f}% YoY")

    def _score_earnings_yoy(self, info: dict, financials: dict, data_gaps: list) -> MetricScore:
        growth = info.get("earningsGrowth")
        if growth is None:
            growth = self._calc_yoy_growth(financials, "Net Income", "NetIncome")
        if growth is None:
            data_gaps.append("Earnings YoY")
            return MetricScore(description="Not available")
        pct = growth * 100
        score = self._growth_rate_score(pct)
        return MetricScore(value=round(pct, 1), score=score, grade=score_to_grade(score),
                           description=f"{pct:+.1f}% YoY")

    def _score_revenue_trend(self, financials: dict, data_gaps: list) -> MetricScore:
        quarterly = financials.get("quarterly_income")
        if not quarterly:
            data_gaps.append("Revenue Trend")
            return MetricScore(description="Not available")

        periods = sorted(quarterly.keys(), reverse=True)
        if len(periods) < 3:
            data_gaps.append("Revenue Trend")
            return MetricScore(description="Insufficient data")

        revenues = []
        for p in periods[:4]:
            rev = quarterly[p].get("Total Revenue") or quarterly[p].get("TotalRevenue")
            if rev:
                revenues.append(rev)

        if len(revenues) < 3:
            data_gaps.append("Revenue Trend")
            return MetricScore(description="Insufficient data")

        growth_rates = []
        for i in range(len(revenues) - 1):
            if revenues[i + 1] != 0:
                growth_rates.append((revenues[i] - revenues[i + 1]) / abs(revenues[i + 1]))

        if len(growth_rates) >= 2:
            if growth_rates[0] > growth_rates[1]:
                score = 80
                desc = "Accelerating revenue growth"
            elif growth_rates[0] > 0:
                score = 60
                desc = "Positive but decelerating growth"
            else:
                score = 30
                desc = "Revenue declining"
        else:
            data_gaps.append("Revenue Trend")
            return MetricScore(description="Limited trend data")

        return MetricScore(value=round(growth_rates[0] * 100, 1) if growth_rates else None,
                           score=score, grade=score_to_grade(score), description=desc)

    def _score_analyst_growth(self, info: dict, data_gaps: list) -> MetricScore:
        growth = info.get("earningsGrowth")
        target = info.get("targetMeanPrice")
        current = info.get("currentPrice") or info.get("regularMarketPrice")

        if growth:
            pct = growth * 100
            score = self._growth_rate_score(pct)
            return MetricScore(value=round(pct, 1), score=score, grade=score_to_grade(score),
                               description=f"Analyst est. {pct:+.1f}%")
        elif target and current and current > 0:
            upside = ((target - current) / current) * 100
            score = clamp(50 + upside, 0, 100)
            return MetricScore(value=round(upside, 1), score=score, grade=score_to_grade(score),
                               description=f"Analyst target {upside:+.1f}% upside")
        else:
            data_gaps.append("Analyst Growth Est.")
            return MetricScore(description="Not available")

    # --- Health Scoring ---

    def _score_health(self, info: dict, financials: dict, data_gaps: list) -> HealthMetrics:
        de = self._score_debt_to_equity(info, data_gaps)
        cr = self._score_current_ratio(info, data_gaps)
        qr = self._score_quick_ratio(info, data_gaps)
        fcf = self._score_fcf_yield(info, financials, data_gaps)
        ocf = self._score_ocf_trend(financials, data_gaps)

        composite = _weighted_average([
            (de, 0.25), (cr, 0.15), (qr, 0.10), (fcf, 0.30), (ocf, 0.20),
        ])
        return HealthMetrics(
            debt_to_equity=de,
            current_ratio=cr,
            quick_ratio=qr,
            fcf_yield=fcf,
            ocf_trend=ocf,
            composite_score=round(composite, 1),
            grade=score_to_grade(composite),
        )

    def _score_debt_to_equity(self, info: dict, data_gaps: list) -> MetricScore:
        de = info.get("debtToEquity")
        if de is None:
            data_gaps.append("Debt/Equity")
            return MetricScore(description="Not available")
        de_ratio = de / 100 if de > 10 else de
        if de_ratio < 0.3:
            score = 90
        elif de_ratio < 0.5:
            score = 80
        elif de_ratio < 1.0:
            score = 65
        elif de_ratio < 1.5:
            score = 45
        elif de_ratio < 2.0:
            score = 30
        else:
            score = 15
        return MetricScore(value=round(de_ratio, 2), score=score, grade=score_to_grade(score))

    def _score_current_ratio(self, info: dict, data_gaps: list) -> MetricScore:
        cr = info.get("currentRatio")
        if cr is None:
            data_gaps.append("Current Ratio")
            return MetricScore(description="Not available")
        if cr >= 2.0:
            score = 85
        elif cr >= 1.5:
            score = 75
        elif cr >= 1.0:
            score = 55
        elif cr >= 0.5:
            score = 30
        else:
            score = 10
        return MetricScore(value=round(cr, 2), score=score, grade=score_to_grade(score))

    def _score_quick_ratio(self, info: dict, data_gaps: list) -> MetricScore:
        qr = info.get("quickRatio")
        if qr is None:
            data_gaps.append("Quick Ratio")
            return MetricScore(description="Not available")
        if qr >= 1.5:
            score = 85
        elif qr >= 1.0:
            score = 70
        elif qr >= 0.5:
            score = 45
        else:
            score = 20
        return MetricScore(value=round(qr, 2), score=score, grade=score_to_grade(score))

    def _score_fcf_yield(self, info: dict, financials: dict, data_gaps: list) -> MetricScore:
        fcf = info.get("freeCashflow")
        market_cap = info.get("marketCap")
        if not fcf or not market_cap or market_cap <= 0:
            cf = financials.get("cash_flow", {})
            if cf:
                latest = sorted(cf.keys(), reverse=True)
                if latest:
                    fcf = cf[latest[0]].get("Free Cash Flow") or cf[latest[0]].get("FreeCashFlow")
            if not fcf or not market_cap or market_cap <= 0:
                data_gaps.append("FCF Yield")
                return MetricScore(description="Not available")

        fcf_yield = (fcf / market_cap) * 100
        if fcf_yield > 10:
            score = 95
        elif fcf_yield > 6:
            score = 80
        elif fcf_yield > 3:
            score = 65
        elif fcf_yield > 0:
            score = 45
        else:
            score = 15
        return MetricScore(value=round(fcf_yield, 2), score=score, grade=score_to_grade(score),
                           description=f"FCF yield {fcf_yield:.1f}%")

    def _score_ocf_trend(self, financials: dict, data_gaps: list) -> MetricScore:
        cf = financials.get("cash_flow", {})
        if not cf:
            data_gaps.append("OCF Trend")
            return MetricScore(description="Not available")

        periods = sorted(cf.keys(), reverse=True)
        ocfs = []
        for p in periods[:3]:
            ocf = cf[p].get("Operating Cash Flow") or cf[p].get("OperatingCashFlow") or cf[p].get("Total Cash From Operating Activities")
            if ocf is not None:
                ocfs.append(ocf)

        if len(ocfs) < 2:
            data_gaps.append("OCF Trend")
            return MetricScore(description="Limited OCF data")

        if ocfs[0] > ocfs[1]:
            if ocfs[0] > 0:
                score = 80
                desc = "Improving operating cash flow"
            else:
                score = 40
                desc = "Negative but improving OCF"
        else:
            if ocfs[0] > 0:
                score = 55
                desc = "Positive but declining OCF"
            else:
                score = 15
                desc = "Negative and declining OCF"

        return MetricScore(value=round(ocfs[0], 0), score=score, grade=score_to_grade(score), description=desc)

    # --- Profitability Scoring ---

    def _score_profitability(self, info: dict, financials: dict, data_gaps: list) -> ProfitabilityMetrics:
        gm = self._score_gross_margin(info, data_gaps)
        om = self._score_operating_margin(info, data_gaps)
        nm = self._score_net_margin(info, data_gaps)
        mt = self._score_margin_trend(info, financials, data_gaps)

        composite = _weighted_average([
            (gm, 0.20), (om, 0.30), (nm, 0.25), (mt, 0.25),
        ])
        return ProfitabilityMetrics(
            gross_margin=gm,
            operating_margin=om,
            net_margin=nm,
            margin_trend=mt,
            composite_score=round(composite, 1),
            grade=score_to_grade(composite),
        )

    def _score_gross_margin(self, info: dict, data_gaps: list) -> MetricScore:
        gm = info.get("grossMargins")
        if gm is None:
            data_gaps.append("Gross Margin")
            return MetricScore(description="Not available")
        pct = gm * 100
        if pct > 60:
            score = 90
        elif pct > 40:
            score = 75
        elif pct > 25:
            score = 55
        elif pct > 10:
            score = 35
        else:
            score = 15
        return MetricScore(value=round(pct, 1), score=score, grade=score_to_grade(score),
                           description=f"Gross margin {pct:.1f}%")

    def _score_operating_margin(self, info: dict, data_gaps: list) -> MetricScore:
        om = info.get("operatingMargins")
        if om is None:
            data_gaps.append("Operating Margin")
            return MetricScore(description="Not available")
        pct = om * 100
        if pct > 30:
            score = 90
        elif pct > 20:
            score = 75
        elif pct > 10:
            score = 60
        elif pct > 0:
            score = 40
        else:
            score = 15
        return MetricScore(value=round(pct, 1), score=score, grade=score_to_grade(score),
                           description=f"Operating margin {pct:.1f}%")

    def _score_net_margin(self, info: dict, data_gaps: list) -> MetricScore:
        nm = info.get("profitMargins")
        if nm is None:
            data_gaps.append("Net Margin")
            return MetricScore(description="Not available")
        pct = nm * 100
        if pct > 25:
            score = 90
        elif pct > 15:
            score = 75
        elif pct > 8:
            score = 60
        elif pct > 0:
            score = 40
        else:
            score = 15
        return MetricScore(value=round(pct, 1), score=score, grade=score_to_grade(score),
                           description=f"Net margin {pct:.1f}%")

    def _score_margin_trend(self, info: dict, financials: dict, data_gaps: list) -> MetricScore:
        quarterly = financials.get("quarterly_income", {})
        if not quarterly:
            data_gaps.append("Margin Trend")
            return MetricScore(description="No quarterly data")

        periods = sorted(quarterly.keys(), reverse=True)
        if len(periods) < 5:
            data_gaps.append("Margin Trend")
            return MetricScore(description="Insufficient quarterly data")

        def get_op_margin(period_data):
            revenue = period_data.get("Total Revenue") or period_data.get("TotalRevenue")
            op_income = period_data.get("Operating Income") or period_data.get("OperatingIncome") or period_data.get("EBIT")
            if revenue and op_income and revenue != 0:
                return op_income / revenue
            return None

        current_margin = get_op_margin(quarterly[periods[0]])
        yago_margin = get_op_margin(quarterly[periods[4]]) if len(periods) > 4 else None

        if current_margin is not None and yago_margin is not None:
            improvement = (current_margin - yago_margin) * 100
            if improvement > 3:
                score = 85
                desc = f"Margins expanding (+{improvement:.1f}pp)"
            elif improvement > 0:
                score = 65
                desc = f"Margins stable to improving (+{improvement:.1f}pp)"
            elif improvement > -3:
                score = 45
                desc = f"Margins slightly contracting ({improvement:.1f}pp)"
            else:
                score = 20
                desc = f"Margins contracting ({improvement:.1f}pp)"
            return MetricScore(value=round(improvement, 1), score=score, grade=score_to_grade(score), description=desc)

        data_gaps.append("Margin Trend")
        return MetricScore(description="Cannot determine margin trend")

    # --- Helpers ---

    def _growth_rate_score(self, pct: float) -> float:
        if pct > 50:
            return 95
        elif pct > 25:
            return 85
        elif pct > 15:
            return 70
        elif pct > 5:
            return 55
        elif pct > 0:
            return 45
        elif pct > -10:
            return 30
        else:
            return 10

    def _calc_yoy_growth(self, financials: dict, *field_names) -> float | None:
        income = financials.get("income_statement", {})
        if not income:
            return None
        periods = sorted(income.keys(), reverse=True)
        if len(periods) < 2:
            return None

        for name in field_names:
            recent = income[periods[0]].get(name)
            prior = income[periods[1]].get(name)
            if recent is not None and prior is not None and prior != 0:
                return (recent - prior) / abs(prior)
        return None
