"""
Fundamental analysis engine.
Computes four equally weighted (25% each) sub-scores:
- Valuation (Forward PE 30%, PEG 25%, P/S 20%, P/B 15%, Trailing PE 10%)
  — scored RELATIVE to sector/peer benchmarks, not absolute thresholds
  — PE and Forward PE are growth-adjusted: high-growth companies are allowed higher multiples
- Growth (Revenue YoY 25%, Earnings YoY 25%, Revenue QoQ 12.5%, Earnings QoQ 12.5%, Analyst Growth Est. 25%)
- Financial Health (Interest Coverage 20%, FCF Yield 30%, OCF Trend 25%, D/E 15%, Current Ratio 10%)
- Profitability (Gross Margin 20%, Operating Margin 30%, Net Margin 25%, Margin Trend 25%)

Quarterly data pipeline (Revenue QoQ, Earnings QoQ, Margin Trend):
  1. Finnhub /stock/financials-reported (primary)
  2. SEC EDGAR company_facts (fallback)
  3. yfinance quarterly data (last resort)

When a metric is missing (N/A), its weight is redistributed proportionally among
the metrics that do have data, so missing data never drags down the score.
"""
import asyncio
import logging
import statistics

from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.grading import clamp, score_to_grade
from app.analysis.peg_calculator import calculate_peg
from app.analysis.sector_benchmarks import get_benchmark, score_relative
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


def _interpolate(value: float, breakpoints: list[tuple[float, float]]) -> float:
    """Smooth linear interpolation between breakpoints [(input_value, score), ...]."""
    import math

    # Validate input value
    if not isinstance(value, (int, float)) or math.isnan(value) or math.isinf(value):
        return 50.0  # Return neutral score for invalid input

    # Validate breakpoints
    for v, s in breakpoints:
        if math.isnan(v) or math.isinf(v) or math.isnan(s) or math.isinf(s):
            return 50.0  # Return neutral score if breakpoints are invalid

    if value <= breakpoints[0][0]:
        return float(breakpoints[0][1])
    if value >= breakpoints[-1][0]:
        return float(breakpoints[-1][1])
    for i in range(len(breakpoints) - 1):
        v1, s1 = breakpoints[i]
        v2, s2 = breakpoints[i + 1]
        if v1 <= value <= v2:
            if v2 - v1 == 0:  # Prevent division by zero
                return float(s1)
            t = (value - v1) / (v2 - v1)
            return round(s1 + t * (s2 - s1), 1)
    return 50.0


def _weighted_average(items: list[tuple[MetricScore, float]]) -> float:
    """
    Compute weighted average, redistributing weight from missing metrics.
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
    def __init__(self, db: AsyncSession, cache: CacheManager, yf: YFinanceService, finnhub: FinnhubService, edgar=None):
        self.db = db
        self.cache = cache
        self.yf = yf
        self.finnhub = finnhub
        self.edgar = edgar

    async def analyze(self, ticker: str) -> FundamentalAnalysis | None:
        info = await self._get_info(ticker)
        if not info:
            return None

        financials = await self._get_financials(ticker)
        data_gaps = []

        # Fetch sector/peer benchmarks for relative valuation scoring
        benchmarks = await self._get_peer_benchmarks(ticker, info)

        # Compute sub-scores
        valuation = self._score_valuation(info, financials, data_gaps, benchmarks)
        growth = self._score_growth(info, financials, data_gaps, get_benchmark(info.get("sector")))
        health = self._score_health(info, financials, data_gaps)
        profitability = self._score_profitability(info, financials, data_gaps, benchmarks)

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

        total_metrics = 15
        available_count = total_metrics - len(data_gaps)
        confidence = available_count / total_metrics

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

    # ── Data Fetching ────────────────────────────────────────────────

    async def _get_info(self, ticker: str) -> dict | None:
        cached = await self.cache.get_company(ticker)
        info = cached or {}

        # Enrich with Finnhub basic financials
        finnhub_metrics = await self.finnhub.get_basic_financials(ticker)
        if finnhub_metrics:
            metric = finnhub_metrics.get("metric", {})
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
            if not info.get("forwardPE") and metric.get("forwardPE"):
                info["forwardPE"] = metric["forwardPE"]
            if not info.get("dividendYield") and metric.get("dividendYieldIndicatedAnnual"):
                info["dividendYield"] = metric["dividendYieldIndicatedAnnual"] / 100
            if not info.get("freeCashflow") and metric.get("freeCashFlowTTM"):
                info["freeCashflow"] = metric["freeCashFlowTTM"]
            # Growth rate data for PE growth adjustment
            if not info.get("epsGrowth5Y") and metric.get("epsGrowth5Y"):
                info["epsGrowth5Y"] = metric["epsGrowth5Y"]
            if not info.get("interestCoverage"):
                ic = metric.get("netInterestCoverageTTM") or metric.get("netInterestCoverageAnnual")
                if ic and ic > 0:
                    info["interestCoverage"] = ic
            if not info.get("evFcfRatio") and metric.get("currentEv/freeCashFlowTTM"):
                ev_fcf = metric["currentEv/freeCashFlowTTM"]
                if ev_fcf > 0:
                    info["evFcfRatio"] = ev_fcf
            # Bank-specific metrics
            if not info.get("roe"):
                roe = metric.get("roeTTM") or metric.get("roeRfy")
                if roe is not None:
                    info["roe"] = roe
            if not info.get("roa"):
                roa = metric.get("roaTTM") or metric.get("roaRfy")
                if roa is not None:
                    info["roa"] = roa
            if not info.get("payoutRatio"):
                pr = metric.get("payoutRatioTTM") or metric.get("payoutRatioAnnual")
                if pr is not None:
                    info["payoutRatio"] = pr

        # Enrich with Finnhub company profile for sector/industry
        if not info.get("sector"):
            profile = await self.finnhub.get_company_profile(ticker)
            if profile:
                fh_industry = profile.get("finnhubIndustry")
                if fh_industry:
                    info["sector"] = fh_industry
                if not info.get("name"):
                    info["name"] = profile.get("name")

        if not info:
            yf_info = await self.yf.get_info(ticker)
            if yf_info:
                info = yf_info
                await self.cache.set_company(ticker, info)

        return info if info else None

    async def _get_financials(self, ticker: str) -> dict:
        cached = await self.cache.get_fundamental(ticker, "financials")
        if cached:
            data = cached
        else:
            data = await self.yf.get_financials(ticker)
            if data:
                await self.cache.set_fundamental(ticker, "financials", "yfinance", data)
            else:
                data = {}

        # Enrich with quarterly income from Finnhub/EDGAR pipeline
        quarterly = await self._get_quarterly_income(ticker)
        if quarterly and len(quarterly) >= 3:
            data["quarterly_income"] = quarterly
        elif not data.get("quarterly_income"):
            data["quarterly_income"] = quarterly or {}

        return data

    async def _get_quarterly_income(self, ticker: str) -> dict | None:
        """
        3-tier fallback for quarterly income data:
        1. Cache (source=finnhub or edgar, 24h TTL)
        2. Finnhub /stock/financials-reported
        3. SEC EDGAR company_facts
        """
        from app.services.xbrl_mapper import parse_edgar_quarterly, parse_finnhub_quarterly

        # Check cache for Finnhub or EDGAR quarterly data
        for source in ("finnhub", "edgar"):
            cached = await self.cache.get_fundamental(ticker, "quarterly_income", source=source)
            if cached and len(cached) >= 3:
                logger.debug(f"Using cached {source} quarterly data for {ticker} ({len(cached)} quarters)")
                return cached

        # Tier 2: Finnhub /stock/financials-reported
        try:
            reports = await self.finnhub.get_financials_reported(ticker)
            if reports:
                quarterly = parse_finnhub_quarterly(reports)
                if quarterly and len(quarterly) >= 3:
                    await self.cache.set_fundamental(ticker, "quarterly_income", "finnhub", quarterly)
                    logger.info(f"Finnhub quarterly data for {ticker}: {len(quarterly)} quarters")
                    return quarterly
        except Exception as e:
            logger.warning(f"Finnhub financials-reported failed for {ticker}: {e}")

        # Tier 3: SEC EDGAR
        if self.edgar:
            try:
                # Check for cached CIK mapping first
                cik_cache = await self.cache.get_fundamental(ticker, "cik_mapping", source="edgar", ttl=604800)  # 7 days
                cik = cik_cache.get("cik") if cik_cache else None

                if not cik:
                    cik = await self.edgar.lookup_cik(ticker)
                    if cik:
                        await self.cache.set_fundamental(ticker, "cik_mapping", "edgar", {"cik": cik})

                if cik:
                    facts = await self.edgar.get_company_facts(cik)
                    if facts:
                        quarterly = parse_edgar_quarterly(facts)
                        if quarterly and len(quarterly) >= 3:
                            await self.cache.set_fundamental(ticker, "quarterly_income", "edgar", quarterly)
                            logger.info(f"EDGAR quarterly data for {ticker}: {len(quarterly)} quarters")
                            return quarterly
            except Exception as e:
                logger.warning(f"EDGAR quarterly fetch failed for {ticker}: {e}")

        return None

    async def _get_peer_benchmarks(self, ticker: str, info: dict) -> dict:
        """
        Get valuation benchmarks from peers or sector.
        Returns: {"pe": float, "pb": float, "ps": float, "peg": float, "source": str}
        """
        # Check cache first
        cached = await self.cache.get_peer_benchmarks(ticker)
        if cached and cached.get("medians"):
            medians = cached["medians"]
            medians["source"] = cached.get("source", "peers")
            return medians

        # Try fetching live peer data from Finnhub
        peer_tickers = await self.finnhub.get_peers(ticker)
        if peer_tickers and len(peer_tickers) >= 3:
            # Limit to 8 peers to keep API calls reasonable
            peer_tickers = peer_tickers[:8]

            # Fetch basic_financials for all peers concurrently
            tasks = [self.finnhub.get_basic_financials(p) for p in peer_tickers]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            pe_vals, fpe_vals, pb_vals, ps_vals = [], [], [], []
            for i, result in enumerate(results):
                if isinstance(result, Exception) or result is None:
                    continue
                metric = result.get("metric", {})
                pe = metric.get("peBasicExclExtraTTM")
                fpe = metric.get("forwardPE")
                pb = metric.get("pbAnnual")
                ps = metric.get("psTTM")
                if pe and pe > 0:
                    pe_vals.append(pe)
                if fpe and fpe > 0:
                    fpe_vals.append(fpe)
                if pb and pb > 0:
                    pb_vals.append(pb)
                if ps and ps > 0:
                    ps_vals.append(ps)

            # Need at least 3 data points for a meaningful median
            if len(pe_vals) >= 3:
                sector_fallback = get_benchmark(info.get("sector"))
                pe_median = round(statistics.median(pe_vals), 2)
                medians = {
                    "pe": pe_median,
                    "fpe": round(statistics.median(fpe_vals), 2) if len(fpe_vals) >= 3 else round(pe_median * 0.85, 2),
                    "pb": round(statistics.median(pb_vals), 2) if len(pb_vals) >= 3 else sector_fallback["pb"],
                    "ps": round(statistics.median(ps_vals), 2) if len(ps_vals) >= 3 else sector_fallback["ps"],
                    "peg": sector_fallback["peg"],  # PEG not directly available from basic_financials
                }

                # Cache the result
                cache_data = {
                    "peers": peer_tickers,
                    "medians": medians,
                    "source": "peers",
                    "peer_count": len(pe_vals),
                }
                await self.cache.set_peer_benchmarks(ticker, cache_data)

                medians["source"] = "peers"
                logger.info(f"Peer benchmarks for {ticker}: PE={medians['pe']}, P/B={medians['pb']}, P/S={medians['ps']} (from {len(pe_vals)} peers)")
                return medians

        # Fallback: use sector benchmarks
        sector = info.get("sector")
        benchmarks = get_benchmark(sector)
        source = f"sector ({sector})" if sector else "default"

        # Cache sector fallback too so we don't re-fetch peers that returned too few results
        cache_data = {
            "peers": peer_tickers or [],
            "medians": benchmarks,
            "source": source,
        }
        await self.cache.set_peer_benchmarks(ticker, cache_data)

        benchmarks_with_source = {**benchmarks, "source": source}
        logger.info(f"Using {source} benchmarks for {ticker}: PE={benchmarks['pe']}, P/B={benchmarks['pb']}, P/S={benchmarks['ps']}")
        return benchmarks_with_source

    # ── Valuation Scoring (Sector/Peer Relative) ────────────────────

    def _score_valuation(self, info: dict, financials: dict, data_gaps: list, benchmarks: dict) -> ValuationMetrics:
        growth_rate = self._get_earnings_growth_rate(info, financials)
        pe = self._score_pe(info, data_gaps, benchmarks, growth_rate)
        fpe = self._score_forward_pe(info, data_gaps, benchmarks, growth_rate)
        peg = self._score_peg(info, financials, data_gaps, benchmarks)
        pb = self._score_pb(info, data_gaps, benchmarks)
        ps = self._score_ps(info, data_gaps, benchmarks)

        composite = _weighted_average([
            (fpe, 0.30), (peg, 0.25), (ps, 0.20), (pb, 0.15), (pe, 0.10),
        ])
        return ValuationMetrics(
            pe_ratio=pe,
            forward_pe=fpe,
            peg_ratio=peg,
            pb_ratio=pb,
            ps_ratio=ps,
            composite_score=round(composite, 1),
            grade=score_to_grade(composite),
        )

    def _get_earnings_growth_rate(self, info: dict, financials: dict) -> float | None:
        """Get best available earnings growth rate as a decimal (0.25 = 25%)."""
        # Priority 1: TTM YoY earnings growth from Finnhub
        eg = info.get("earningsGrowth")
        if eg is not None and eg > 0:
            return eg

        # Priority 2: 5-year EPS CAGR from Finnhub (smoothed long-term)
        eg5 = info.get("epsGrowth5Y")
        if eg5 is not None and eg5 > 0:
            return eg5 / 100

        # Priority 3: Trailing 3-year EPS CAGR from financials
        from app.analysis.peg_calculator import _calc_trailing_eps_growth
        cagr = _calc_trailing_eps_growth(financials)
        if cagr is not None and cagr > 0:
            return cagr

        return None

    @staticmethod
    def _growth_adjusted_benchmark(benchmark: float, growth_rate: float | None) -> float:
        """
        Adjust a PE benchmark upward for high-growth companies.
        A company growing faster than the ~8% market average is allowed a higher PE.
        """
        if growth_rate is None or growth_rate <= 0 or benchmark <= 0:
            return benchmark

        BASELINE_GROWTH = 0.08  # ~8% is average market earnings growth
        growth_ratio = growth_rate / BASELINE_GROWTH

        # sqrt dampening: 2x growth → 1.41x benchmark, 4x growth → 2x benchmark
        # Floor at 1.0: only boost for above-average growth, never penalize low growth
        # Cap at 2.0 to prevent extreme adjustments
        adjustment = max(1.0, min(growth_ratio ** 0.5, 2.0))
        return benchmark * adjustment

    def _score_pe(self, info: dict, data_gaps: list, benchmarks: dict, growth_rate: float | None) -> MetricScore:
        pe = info.get("trailingPE")
        if pe is None:
            data_gaps.append("PE Ratio")
            return MetricScore(description="Not available")
        if pe < 0:
            return MetricScore(value=round(pe, 2), score=10, grade=score_to_grade(10),
                               description="Negative earnings")

        benchmark_pe = benchmarks.get("pe", 20)
        adj_benchmark = self._growth_adjusted_benchmark(benchmark_pe, growth_rate)
        score = score_relative(pe, adj_benchmark)
        ratio = pe / adj_benchmark if adj_benchmark > 0 else 1
        source = benchmarks.get("source", "sector")

        if ratio < 0.8:
            context = "Undervalued vs peers"
        elif ratio < 1.1:
            context = "In line with peers"
        elif ratio < 1.5:
            context = "Premium to peers"
        else:
            context = "Expensive vs peers"

        growth_note = ""
        if growth_rate and adj_benchmark > benchmark_pe * 1.05:
            growth_note = f" (growth-adj {adj_benchmark:.0f})"
        desc = f"PE {pe:.1f} vs {source} median {benchmark_pe:.1f}{growth_note} — {context}"
        return MetricScore(value=round(pe, 2), score=round(score, 1), grade=score_to_grade(score), description=desc)

    def _score_forward_pe(self, info: dict, data_gaps: list, benchmarks: dict, growth_rate: float | None) -> MetricScore:
        fpe = info.get("forwardPE")
        if fpe is None:
            data_gaps.append("Forward PE")
            return MetricScore(description="Not available")
        if fpe < 0:
            return MetricScore(value=round(fpe, 2), score=10, grade=score_to_grade(10),
                               description="Negative forward earnings")

        benchmark_fpe = benchmarks.get("fpe", benchmarks.get("pe", 20) * 0.85)
        adj_benchmark = self._growth_adjusted_benchmark(benchmark_fpe, growth_rate)
        score = score_relative(fpe, adj_benchmark)
        ratio = fpe / adj_benchmark if adj_benchmark > 0 else 1
        source = benchmarks.get("source", "sector")

        if ratio < 0.8:
            context = "Undervalued vs peers"
        elif ratio < 1.1:
            context = "In line with peers"
        elif ratio < 1.5:
            context = "Premium to peers"
        else:
            context = "Expensive vs peers"

        growth_note = ""
        if growth_rate and adj_benchmark > benchmark_fpe * 1.05:
            growth_note = f" (growth-adj {adj_benchmark:.0f})"
        desc = f"Fwd PE {fpe:.1f} vs {source} median {benchmark_fpe:.1f}{growth_note} — {context}"
        return MetricScore(value=round(fpe, 2), score=round(score, 1), grade=score_to_grade(score), description=desc)

    def _score_peg(self, info: dict, financials: dict, data_gaps: list, benchmarks: dict) -> MetricScore:
        peg, method = calculate_peg(info, financials)
        if peg is None:
            data_gaps.append("PEG Ratio")
            return MetricScore(description="Cannot calculate PEG")
        if peg < 0:
            return MetricScore(value=round(peg, 2), score=10, grade=score_to_grade(10),
                               description=f"Negative PEG ({method})")

        benchmark_peg = benchmarks.get("peg", 1.5)
        score = score_relative(peg, benchmark_peg)
        ratio = peg / benchmark_peg if benchmark_peg > 0 else 1
        source = benchmarks.get("source", "sector")

        if ratio < 0.7:
            context = "Undervalued for growth"
        elif ratio < 1.0:
            context = "Good value for growth"
        elif ratio < 1.3:
            context = "Fairly valued for growth"
        else:
            context = "Expensive for growth"

        desc = f"PEG {peg:.2f} ({method}) vs {source} median {benchmark_peg:.2f} — {context}"
        return MetricScore(value=round(peg, 2), score=round(score, 1), grade=score_to_grade(score), description=desc)

    def _score_pb(self, info: dict, data_gaps: list, benchmarks: dict) -> MetricScore:
        pb = info.get("priceToBook")
        if pb is None:
            data_gaps.append("P/B Ratio")
            return MetricScore(description="Not available")

        benchmark_pb = benchmarks.get("pb", 3)
        score = score_relative(pb, benchmark_pb)
        source = benchmarks.get("source", "sector")
        ratio = pb / benchmark_pb if benchmark_pb > 0 else 1

        if ratio < 0.8:
            context = "Below peer avg"
        elif ratio < 1.2:
            context = "In line with peers"
        else:
            context = "Above peer avg"

        desc = f"P/B {pb:.1f} vs {source} median {benchmark_pb:.1f} — {context}"
        return MetricScore(value=round(pb, 2), score=round(score, 1), grade=score_to_grade(score), description=desc)

    def _score_ps(self, info: dict, data_gaps: list, benchmarks: dict) -> MetricScore:
        ps = info.get("priceToSalesTrailing12Months")
        if ps is None:
            data_gaps.append("P/S Ratio")
            return MetricScore(description="Not available")

        benchmark_ps = benchmarks.get("ps", 3)
        score = score_relative(ps, benchmark_ps)
        source = benchmarks.get("source", "sector")
        ratio = ps / benchmark_ps if benchmark_ps > 0 else 1

        if ratio < 0.8:
            context = "Below peer avg"
        elif ratio < 1.2:
            context = "In line with peers"
        else:
            context = "Above peer avg"

        desc = f"P/S {ps:.1f} vs {source} median {benchmark_ps:.1f} — {context}"
        return MetricScore(value=round(ps, 2), score=round(score, 1), grade=score_to_grade(score), description=desc)

    # ── Growth Scoring ───────────────────────────────────────────────

    def _score_growth(self, info: dict, financials: dict, data_gaps: list, sector_benchmarks: dict) -> GrowthMetrics:
        rev_yoy = self._score_revenue_yoy(info, financials, data_gaps, sector_benchmarks)
        earn_yoy = self._score_earnings_yoy(info, financials, data_gaps, sector_benchmarks)
        rev_qoq = self._score_revenue_qoq(financials, data_gaps)
        earn_qoq = self._score_earnings_qoq(financials, data_gaps)
        analyst = self._score_analyst_growth(info, data_gaps, sector_benchmarks)

        composite = _weighted_average([
            (rev_yoy, 0.25), (earn_yoy, 0.25), (rev_qoq, 0.125),
            (earn_qoq, 0.125), (analyst, 0.25),
        ])
        return GrowthMetrics(
            revenue_yoy=rev_yoy,
            earnings_yoy=earn_yoy,
            revenue_qoq=rev_qoq,
            earnings_qoq=earn_qoq,
            analyst_growth_est=analyst,
            composite_score=round(composite, 1),
            grade=score_to_grade(composite),
        )

    def _sector_relative_growth_score(self, pct: float, benchmark: float) -> float:
        """
        Score a growth rate relative to sector benchmark using linear interpolation.
        ratio = actual_growth / sector_benchmark; higher ratio = better score.
        Falls back to absolute scoring if benchmark is non-positive.
        """
        if benchmark <= 0:
            return self._growth_rate_score(pct)
        ratio = pct / benchmark
        breakpoints = [
            (0.0, 5), (0.3, 15), (0.5, 30), (0.7, 45), (0.9, 55),
            (1.0, 65), (1.2, 80), (1.5, 90), (2.0, 95),
        ]
        if ratio <= breakpoints[0][0]:
            return float(breakpoints[0][1])
        if ratio >= breakpoints[-1][0]:
            return float(breakpoints[-1][1])
        for i in range(len(breakpoints) - 1):
            r1, s1 = breakpoints[i]
            r2, s2 = breakpoints[i + 1]
            if r1 <= ratio <= r2:
                t = (ratio - r1) / (r2 - r1) if r2 > r1 else 0
                return round(s1 + t * (s2 - s1), 1)
        return 50.0

    def _score_revenue_yoy(self, info: dict, financials: dict, data_gaps: list, sector_benchmarks: dict) -> MetricScore:
        growth = info.get("revenueGrowth")
        if growth is None:
            growth = self._calc_yoy_growth(financials, "Total Revenue", "TotalRevenue")
        if growth is None:
            data_gaps.append("Revenue YoY")
            return MetricScore(description="Not available")
        pct = growth * 100
        benchmark = sector_benchmarks.get("revenue_growth", 8)
        absolute_score = self._growth_rate_score(pct)
        relative_score = self._sector_relative_growth_score(pct, benchmark)
        score = round((absolute_score + relative_score) / 2, 1)
        return MetricScore(value=round(pct, 1), score=score, grade=score_to_grade(score),
                           description=f"{pct:+.1f}% YoY (sector avg: {benchmark}%)")

    def _score_earnings_yoy(self, info: dict, financials: dict, data_gaps: list, sector_benchmarks: dict) -> MetricScore:
        growth = info.get("earningsGrowth")
        if growth is None:
            growth = self._calc_yoy_growth(financials, "Net Income", "NetIncome")
        if growth is None:
            data_gaps.append("Earnings YoY")
            return MetricScore(description="Not available")
        pct = growth * 100
        benchmark = sector_benchmarks.get("earnings_growth", 10)
        absolute_score = self._growth_rate_score(pct)
        relative_score = self._sector_relative_growth_score(pct, benchmark)
        score = round((absolute_score + relative_score) / 2, 1)
        return MetricScore(value=round(pct, 1), score=score, grade=score_to_grade(score),
                           description=f"{pct:+.1f}% YoY (sector avg: {benchmark}%)")

    def _score_revenue_qoq(self, financials: dict, data_gaps: list) -> MetricScore:
        """Score sequential quarter-over-quarter revenue growth with momentum adjustment."""
        quarterly = financials.get("quarterly_income")
        if not quarterly:
            data_gaps.append("Revenue QoQ")
            return MetricScore(description="Not available")

        periods = sorted(quarterly.keys(), reverse=True)
        if len(periods) < 2:
            data_gaps.append("Revenue QoQ")
            return MetricScore(description="Insufficient data")

        revenues = []
        for p in periods[:4]:
            rev = quarterly[p].get("Total Revenue") or quarterly[p].get("TotalRevenue")
            if rev:
                revenues.append(rev)

        if len(revenues) < 2:
            data_gaps.append("Revenue QoQ")
            return MetricScore(description="Insufficient data")

        # Most recent QoQ growth
        if revenues[1] == 0:
            data_gaps.append("Revenue QoQ")
            return MetricScore(description="Prior quarter revenue is zero")

        qoq_pct = ((revenues[0] - revenues[1]) / abs(revenues[1])) * 100

        breakpoints = [
            (-15, 5), (-10, 15), (-5, 28), (-2, 40), (0, 50),
            (2, 60), (5, 72), (8, 80), (12, 88), (20, 95),
        ]
        score = _interpolate(qoq_pct, breakpoints)

        # Momentum adjustment: compare current QoQ to prior QoQ
        momentum = ""
        if len(revenues) >= 3 and revenues[2] != 0:
            prior_qoq = ((revenues[1] - revenues[2]) / abs(revenues[2])) * 100
            if qoq_pct > prior_qoq + 1:
                score = min(score + 10, 99)
                momentum = " (accelerating)"
            elif qoq_pct < prior_qoq - 1:
                score = max(score - 10, 1)
                momentum = " (decelerating)"
            else:
                momentum = " (stable)"

        desc = f"{qoq_pct:+.1f}% QoQ{momentum}"
        return MetricScore(value=round(qoq_pct, 1), score=round(score, 1),
                           grade=score_to_grade(score), description=desc)

    def _score_earnings_qoq(self, financials: dict, data_gaps: list) -> MetricScore:
        """Score sequential quarter-over-quarter earnings growth with turnaround/loss handling."""
        quarterly = financials.get("quarterly_income")
        if not quarterly:
            data_gaps.append("Earnings QoQ")
            return MetricScore(description="Not available")

        periods = sorted(quarterly.keys(), reverse=True)
        if len(periods) < 2:
            data_gaps.append("Earnings QoQ")
            return MetricScore(description="Insufficient data")

        earnings = []
        for p in periods[:4]:
            ni = quarterly[p].get("Net Income") or quarterly[p].get("NetIncome")
            if ni is not None:
                earnings.append(ni)

        if len(earnings) < 2:
            data_gaps.append("Earnings QoQ")
            return MetricScore(description="Insufficient data")

        current, prior = earnings[0], earnings[1]

        # Handle sign transitions explicitly
        if prior < 0 and current > 0:
            # Turnaround: loss to profit
            score = 85
            desc = f"Turnaround: loss to profit (${current/1e6:,.0f}M)"
            return MetricScore(value=None, score=score, grade=score_to_grade(score), description=desc)
        elif prior > 0 and current < 0:
            # Into loss
            score = 10
            desc = f"Turned to loss (${current/1e6:,.0f}M)"
            return MetricScore(value=None, score=score, grade=score_to_grade(score), description=desc)
        elif prior == 0:
            data_gaps.append("Earnings QoQ")
            return MetricScore(description="Prior quarter earnings is zero")

        qoq_pct = ((current - prior) / abs(prior)) * 100

        breakpoints = [
            (-25, 5), (-15, 18), (-8, 32), (-3, 42), (0, 50),
            (3, 58), (8, 70), (15, 82), (25, 90), (40, 95),
        ]
        score = _interpolate(qoq_pct, breakpoints)

        # Momentum adjustment
        momentum = ""
        if len(earnings) >= 3 and earnings[2] != 0:
            # Only compute prior QoQ if same sign transition
            if (earnings[2] > 0 and prior > 0) or (earnings[2] < 0 and prior < 0):
                prior_qoq = ((prior - earnings[2]) / abs(earnings[2])) * 100
                if qoq_pct > prior_qoq + 2:
                    score = min(score + 10, 99)
                    momentum = " (accelerating)"
                elif qoq_pct < prior_qoq - 2:
                    score = max(score - 10, 1)
                    momentum = " (decelerating)"
                else:
                    momentum = " (stable)"

        desc = f"{qoq_pct:+.1f}% QoQ{momentum}"
        return MetricScore(value=round(qoq_pct, 1), score=round(score, 1),
                           grade=score_to_grade(score), description=desc)

    def _score_analyst_growth(self, info: dict, data_gaps: list, sector_benchmarks: dict) -> MetricScore:
        growth = info.get("earningsGrowth")
        target = info.get("targetMeanPrice")
        current = info.get("currentPrice") or info.get("regularMarketPrice")

        if growth:
            pct = growth * 100
            benchmark = sector_benchmarks.get("earnings_growth", 10)
            absolute_score = self._growth_rate_score(pct)
            relative_score = self._sector_relative_growth_score(pct, benchmark)
            score = round((absolute_score + relative_score) / 2, 1)
            return MetricScore(value=round(pct, 1), score=score, grade=score_to_grade(score),
                               description=f"Analyst est. {pct:+.1f}% (sector avg: {benchmark}%)")
        elif target and current and current > 0:
            upside = ((target - current) / current) * 100
            score = clamp(50 + upside, 0, 100)
            return MetricScore(value=round(upside, 1), score=score, grade=score_to_grade(score),
                               description=f"Analyst target {upside:+.1f}% upside")
        else:
            data_gaps.append("Analyst Growth Est.")
            return MetricScore(description="Not available")

    # ── Health Scoring ───────────────────────────────────────────────
    # Standard weights: IC 20%, FCF 30%, OCF 25%, D/E 15%, CR 10%
    # Bank weights: ROE 35%, ROA 25%, D/E (lenient) 20%, Payout 20%

    @staticmethod
    def _is_financial_sector(sector: str | None) -> bool:
        if not sector:
            return False
        s = sector.lower()
        return any(x in s for x in ["financial", "banking", "insurance", "bank"])

    def _score_health(self, info: dict, financials: dict, data_gaps: list) -> HealthMetrics:
        if self._is_financial_sector(info.get("sector")):
            return self._score_bank_health(info, data_gaps)
        return self._score_standard_health(info, financials, data_gaps)

    def _score_standard_health(self, info: dict, financials: dict, data_gaps: list) -> HealthMetrics:
        de = self._score_debt_to_equity(info, data_gaps)
        cr = self._score_current_ratio(info, data_gaps)
        ic = self._score_interest_coverage(info, data_gaps)
        fcf = self._score_fcf_yield(info, financials, data_gaps)
        ocf = self._score_ocf_trend(financials, data_gaps)

        composite = _weighted_average([
            (de, 0.15), (cr, 0.10), (ic, 0.20), (fcf, 0.30), (ocf, 0.25),
        ])
        return HealthMetrics(
            debt_to_equity=de,
            current_ratio=cr,
            interest_coverage=ic,
            fcf_yield=fcf,
            ocf_trend=ocf,
            composite_score=round(composite, 1),
            grade=score_to_grade(composite),
        )

    def _score_bank_health(self, info: dict, data_gaps: list) -> HealthMetrics:
        de = self._score_bank_debt_to_equity(info, data_gaps)
        roe = self._score_roe(info, data_gaps)
        roa = self._score_roa(info, data_gaps)
        pr = self._score_payout_ratio(info, data_gaps)

        composite = _weighted_average([
            (roe, 0.35), (roa, 0.25), (de, 0.20), (pr, 0.20),
        ])
        return HealthMetrics(
            debt_to_equity=de,
            roe=roe,
            roa=roa,
            payout_ratio=pr,
            composite_score=round(composite, 1),
            grade=score_to_grade(composite),
        )

    def _score_debt_to_equity(self, info: dict, data_gaps: list) -> MetricScore:
        de = info.get("debtToEquity")
        if de is None:
            data_gaps.append("Debt/Equity")
            return MetricScore(description="Not available")
        de_ratio = de / 100 if de > 10 else de

        score = _interpolate(de_ratio, [
            (0.0, 92), (0.3, 85), (0.5, 78), (0.8, 68),
            (1.0, 60), (1.5, 50), (2.0, 40), (3.0, 28), (5.0, 15),
        ])

        if de_ratio < 0.5:
            desc = f"D/E {de_ratio:.2f} — Very low leverage"
        elif de_ratio < 1.0:
            desc = f"D/E {de_ratio:.2f} — Moderate leverage"
        elif de_ratio < 2.0:
            desc = f"D/E {de_ratio:.2f} — Elevated leverage"
        else:
            desc = f"D/E {de_ratio:.2f} — High leverage"

        return MetricScore(value=round(de_ratio, 2), score=round(score, 1),
                           grade=score_to_grade(score), description=desc)

    def _score_current_ratio(self, info: dict, data_gaps: list) -> MetricScore:
        cr = info.get("currentRatio")
        if cr is None:
            data_gaps.append("Current Ratio")
            return MetricScore(description="Not available")

        score = _interpolate(cr, [
            (0.0, 5), (0.3, 15), (0.5, 30), (0.7, 42),
            (0.9, 53), (1.0, 58), (1.3, 68), (1.5, 75),
            (2.0, 85), (3.0, 88),
        ])

        if cr >= 2.0:
            desc = f"Current ratio {cr:.2f} — Strong liquidity"
        elif cr >= 1.0:
            desc = f"Current ratio {cr:.2f} — Adequate liquidity"
        elif cr >= 0.7:
            desc = f"Current ratio {cr:.2f} — Tight liquidity"
        else:
            desc = f"Current ratio {cr:.2f} — Weak liquidity"

        return MetricScore(value=round(cr, 2), score=round(score, 1),
                           grade=score_to_grade(score), description=desc)

    def _score_interest_coverage(self, info: dict, data_gaps: list) -> MetricScore:
        ic = info.get("interestCoverage")
        if ic is None:
            data_gaps.append("Interest Coverage")
            return MetricScore(description="Not available")

        score = _interpolate(ic, [
            (0, 5), (1, 15), (2, 30), (3, 40), (5, 55),
            (8, 65), (12, 75), (20, 85), (50, 92), (100, 95),
        ])

        if ic >= 20:
            desc = f"Interest coverage {ic:.1f}x — Excellent debt serviceability"
        elif ic >= 8:
            desc = f"Interest coverage {ic:.1f}x — Comfortable"
        elif ic >= 3:
            desc = f"Interest coverage {ic:.1f}x — Adequate"
        elif ic >= 1:
            desc = f"Interest coverage {ic:.1f}x — Tight"
        else:
            desc = f"Interest coverage {ic:.1f}x — Cannot cover interest"

        return MetricScore(value=round(ic, 1), score=round(score, 1),
                           grade=score_to_grade(score), description=desc)

    def _score_fcf_yield(self, info: dict, financials: dict, data_gaps: list) -> MetricScore:
        fcf = info.get("freeCashflow")
        market_cap = info.get("marketCap")
        fcf_yield = None

        # Try direct FCF / market_cap
        if fcf and market_cap and market_cap > 0:
            fcf_yield = (fcf / market_cap) * 100
        else:
            # Try from cash flow statements
            cf = financials.get("cash_flow", {})
            if cf:
                latest = sorted(cf.keys(), reverse=True)
                if latest:
                    stmt_fcf = cf[latest[0]].get("Free Cash Flow") or cf[latest[0]].get("FreeCashFlow")
                    if stmt_fcf and market_cap and market_cap > 0:
                        fcf_yield = (stmt_fcf / market_cap) * 100

        # Fallback: derive from EV/FCF ratio (EV-based approximation)
        if fcf_yield is None and info.get("evFcfRatio"):
            ev_fcf = info["evFcfRatio"]
            if ev_fcf > 0:
                fcf_yield = (1.0 / ev_fcf) * 100

        if fcf_yield is None:
            data_gaps.append("FCF Yield")
            return MetricScore(description="Not available")

        score = _interpolate(fcf_yield, [
            (-5, 5), (0, 20), (1, 38), (2, 50), (3, 60),
            (4, 67), (5, 73), (7, 82), (10, 90), (15, 95),
        ])

        if fcf_yield > 8:
            desc = f"FCF yield {fcf_yield:.1f}% — Excellent cash generation"
        elif fcf_yield > 4:
            desc = f"FCF yield {fcf_yield:.1f}% — Good cash generation"
        elif fcf_yield > 1:
            desc = f"FCF yield {fcf_yield:.1f}% — Moderate cash generation"
        elif fcf_yield > 0:
            desc = f"FCF yield {fcf_yield:.1f}% — Low but positive"
        else:
            desc = f"FCF yield {fcf_yield:.1f}% — Negative free cash flow"

        return MetricScore(value=round(fcf_yield, 2), score=round(score, 1),
                           grade=score_to_grade(score), description=desc)

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

        # Compute growth rate for continuous scoring
        if ocfs[1] != 0:
            growth_pct = ((ocfs[0] - ocfs[1]) / abs(ocfs[1])) * 100
        else:
            growth_pct = 100 if ocfs[0] > 0 else -100

        if ocfs[0] > 0:
            score = _interpolate(growth_pct, [
                (-50, 25), (-20, 35), (-5, 48), (0, 55),
                (5, 63), (10, 70), (20, 80), (50, 90),
            ])
            if growth_pct > 10:
                desc = f"OCF growing {growth_pct:+.0f}% — Strong and improving"
            elif growth_pct > 0:
                desc = f"OCF growing {growth_pct:+.0f}% — Positive and stable"
            else:
                desc = f"OCF declining {growth_pct:+.0f}% — Positive but weakening"
        else:
            score = _interpolate(growth_pct, [
                (-50, 5), (-20, 12), (0, 20), (50, 30),
            ])
            desc = "Negative operating cash flow"

        return MetricScore(value=round(ocfs[0], 0), score=round(score, 1),
                           grade=score_to_grade(score), description=desc)

    # ── Bank-Specific Health Methods ──────────────────────────────────

    def _score_bank_debt_to_equity(self, info: dict, data_gaps: list) -> MetricScore:
        de = info.get("debtToEquity")
        if de is None:
            data_gaps.append("Debt/Equity")
            return MetricScore(description="Not available")
        de_ratio = de / 100 if de > 10 else de

        # Banks naturally carry higher leverage; 2-4 is normal
        score = _interpolate(de_ratio, [
            (0.0, 92), (1.5, 85), (3.0, 68), (4.0, 55),
            (6.0, 38), (10.0, 18),
        ])

        if de_ratio < 2:
            desc = f"D/E {de_ratio:.2f} — Low leverage for a bank"
        elif de_ratio < 4:
            desc = f"D/E {de_ratio:.2f} — Normal bank leverage"
        elif de_ratio < 6:
            desc = f"D/E {de_ratio:.2f} — Elevated for a bank"
        else:
            desc = f"D/E {de_ratio:.2f} — High leverage even for a bank"

        return MetricScore(value=round(de_ratio, 2), score=round(score, 1),
                           grade=score_to_grade(score), description=desc)

    def _score_roe(self, info: dict, data_gaps: list) -> MetricScore:
        roe = info.get("roe")
        if roe is None:
            data_gaps.append("Return on Equity")
            return MetricScore(description="Not available")

        score = _interpolate(roe, [
            (0, 5), (3, 20), (7, 42), (10, 60),
            (13, 72), (15, 80), (20, 90), (25, 95),
        ])

        if roe >= 15:
            desc = f"ROE {roe:.1f}% — Excellent return on equity"
        elif roe >= 10:
            desc = f"ROE {roe:.1f}% — Good return on equity"
        elif roe >= 5:
            desc = f"ROE {roe:.1f}% — Moderate return on equity"
        else:
            desc = f"ROE {roe:.1f}% — Weak return on equity"

        return MetricScore(value=round(roe, 2), score=round(score, 1),
                           grade=score_to_grade(score), description=desc)

    def _score_roa(self, info: dict, data_gaps: list) -> MetricScore:
        roa = info.get("roa")
        if roa is None:
            data_gaps.append("Return on Assets")
            return MetricScore(description="Not available")

        # Banks: >1% is good, >1.5% is excellent (due to low-margin, high-leverage model)
        score = _interpolate(roa, [
            (0, 10), (0.3, 25), (0.5, 38), (0.8, 55),
            (1.0, 65), (1.3, 76), (1.5, 82), (2.0, 92), (2.5, 95),
        ])

        if roa >= 1.5:
            desc = f"ROA {roa:.2f}% — Excellent asset efficiency"
        elif roa >= 1.0:
            desc = f"ROA {roa:.2f}% — Good asset efficiency"
        elif roa >= 0.5:
            desc = f"ROA {roa:.2f}% — Moderate asset efficiency"
        else:
            desc = f"ROA {roa:.2f}% — Weak asset efficiency"

        return MetricScore(value=round(roa, 2), score=round(score, 1),
                           grade=score_to_grade(score), description=desc)

    def _score_payout_ratio(self, info: dict, data_gaps: list) -> MetricScore:
        pr = info.get("payoutRatio")
        if pr is None:
            data_gaps.append("Payout Ratio")
            return MetricScore(description="Not available")

        # Lower payout = more retained earnings = healthier balance sheet
        # Sweet spot 20-40% balances shareholder returns with capital retention
        score = _interpolate(pr, [
            (0, 78), (10, 82), (25, 85), (40, 72),
            (50, 62), (60, 50), (75, 33), (90, 18), (100, 5),
        ])

        if pr < 30:
            desc = f"Payout {pr:.0f}% — Conservative, retaining most earnings"
        elif pr < 50:
            desc = f"Payout {pr:.0f}% — Balanced returns and retention"
        elif pr < 70:
            desc = f"Payout {pr:.0f}% — Elevated payout"
        else:
            desc = f"Payout {pr:.0f}% — High payout, limited retained earnings"

        return MetricScore(value=round(pr, 1), score=round(score, 1),
                           grade=score_to_grade(score), description=desc)

    # ── Profitability Scoring ────────────────────────────────────────

    def _score_profitability(self, info: dict, financials: dict, data_gaps: list, benchmarks: dict) -> ProfitabilityMetrics:
        # Extract sector for sector-relative margin scoring
        sector = info.get("sector")
        sector_benchmarks = get_benchmark(sector)

        gm = self._score_gross_margin(info, data_gaps, sector_benchmarks)
        om = self._score_operating_margin(info, data_gaps, sector_benchmarks)
        nm = self._score_net_margin(info, data_gaps, sector_benchmarks)
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

    def _score_gross_margin(self, info: dict, data_gaps: list, sector_benchmarks: dict) -> MetricScore:
        """
        Score gross margin relative to sector benchmark.
        Higher margins are better, so we invert the score_relative logic.
        """
        gm = info.get("grossMargins")
        if gm is None:
            data_gaps.append("Gross Margin")
            return MetricScore(description="Not available")

        pct = gm * 100
        benchmark = sector_benchmarks.get("gross_margin", 40)  # Default 40% if not in benchmarks

        # For margins, higher is better, so we use inverted ratio
        # If actual > benchmark, score should be higher
        if benchmark > 0:
            ratio = pct / benchmark
            # Use interpolation breakpoints where ratio > 1 = better
            breakpoints = [
                (0.0, 5),   # 0% margin = terrible
                (0.3, 15),  # 30% of sector avg = poor
                (0.5, 30),  # 50% of sector avg = below average
                (0.7, 45),  # 70% of sector avg = fair
                (0.9, 55),  # 90% of sector avg = decent
                (1.0, 65),  # At sector avg = good
                (1.2, 80),  # 20% above avg = very good
                (1.5, 90),  # 50% above avg = excellent
                (2.0, 95),  # 2x sector avg = exceptional
            ]

            # Linear interpolation
            if ratio <= breakpoints[0][0]:
                score = float(breakpoints[0][1])
            elif ratio >= breakpoints[-1][0]:
                score = float(breakpoints[-1][1])
            else:
                for i in range(len(breakpoints) - 1):
                    r1, s1 = breakpoints[i]
                    r2, s2 = breakpoints[i + 1]
                    if r1 <= ratio <= r2:
                        t = (ratio - r1) / (r2 - r1) if r2 > r1 else 0
                        score = round(s1 + t * (s2 - s1), 1)
                        break
                else:
                    score = 50.0
        else:
            # Fallback to absolute thresholds if no valid benchmark
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

        return MetricScore(
            value=round(pct, 1),
            score=score,
            grade=score_to_grade(score),
            description=f"Gross margin {pct:.1f}% (sector avg: {benchmark:.0f}%)"
        )

    def _score_operating_margin(self, info: dict, data_gaps: list, sector_benchmarks: dict) -> MetricScore:
        """Score operating margin relative to sector benchmark."""
        om = info.get("operatingMargins")
        if om is None:
            data_gaps.append("Operating Margin")
            return MetricScore(description="Not available")

        pct = om * 100
        benchmark = sector_benchmarks.get("operating_margin", 15)

        if benchmark > 0:
            ratio = pct / benchmark
            breakpoints = [
                (0.0, 5), (0.3, 15), (0.5, 30), (0.7, 45), (0.9, 55),
                (1.0, 65), (1.2, 80), (1.5, 90), (2.0, 95),
            ]

            if ratio <= breakpoints[0][0]:
                score = float(breakpoints[0][1])
            elif ratio >= breakpoints[-1][0]:
                score = float(breakpoints[-1][1])
            else:
                for i in range(len(breakpoints) - 1):
                    r1, s1 = breakpoints[i]
                    r2, s2 = breakpoints[i + 1]
                    if r1 <= ratio <= r2:
                        t = (ratio - r1) / (r2 - r1) if r2 > r1 else 0
                        score = round(s1 + t * (s2 - s1), 1)
                        break
                else:
                    score = 50.0
        else:
            # Fallback
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

        return MetricScore(
            value=round(pct, 1),
            score=score,
            grade=score_to_grade(score),
            description=f"Operating margin {pct:.1f}% (sector avg: {benchmark:.0f}%)"
        )

    def _score_net_margin(self, info: dict, data_gaps: list, sector_benchmarks: dict) -> MetricScore:
        """Score net margin relative to sector benchmark."""
        nm = info.get("profitMargins")
        if nm is None:
            data_gaps.append("Net Margin")
            return MetricScore(description="Not available")

        pct = nm * 100
        benchmark = sector_benchmarks.get("net_margin", 10)

        if benchmark > 0:
            ratio = pct / benchmark
            breakpoints = [
                (0.0, 5), (0.3, 15), (0.5, 30), (0.7, 45), (0.9, 55),
                (1.0, 65), (1.2, 80), (1.5, 90), (2.0, 95),
            ]

            if ratio <= breakpoints[0][0]:
                score = float(breakpoints[0][1])
            elif ratio >= breakpoints[-1][0]:
                score = float(breakpoints[-1][1])
            else:
                for i in range(len(breakpoints) - 1):
                    r1, s1 = breakpoints[i]
                    r2, s2 = breakpoints[i + 1]
                    if r1 <= ratio <= r2:
                        t = (ratio - r1) / (r2 - r1) if r2 > r1 else 0
                        score = round(s1 + t * (s2 - s1), 1)
                        break
                else:
                    score = 50.0
        else:
            # Fallback
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

        return MetricScore(
            value=round(pct, 1),
            score=score,
            grade=score_to_grade(score),
            description=f"Net margin {pct:.1f}% (sector avg: {benchmark:.0f}%)"
        )

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

    # ── Helpers ───────────────────────────────────────────────────────

    def _growth_rate_score(self, pct: float) -> float:
        """
        Score growth rates with granular handling of negative values.
        Differentiates between mild decline (-5%), moderate (-20%), and severe (-50%+).
        """
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
        elif pct > -5:
            return 35  # Slight decline
        elif pct > -10:
            return 25  # Mild decline
        elif pct > -20:
            return 15  # Moderate decline
        elif pct > -30:
            return 10  # Serious decline
        elif pct > -50:
            return 5   # Severe decline
        else:
            return 1   # Catastrophic decline (>50% revenue/earnings loss)

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
