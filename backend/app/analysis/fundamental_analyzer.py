"""
Fundamental analysis engine.
Computes three pillar scores with weights: Valuation 35%, Growth 30%, Quality 35%.

- Valuation (Forward PE 25%, EV/EBITDA 25%, PEG 20%, P/S 15%, P/B 15%)
  — scored RELATIVE to sector/peer benchmarks
  — PE is growth-adjusted: high-growth companies are allowed higher multiples
- Growth (Revenue YoY 30%, Earnings YoY 30%, Revenue QoQ 10%, FCF Growth QoQ 10%, Forward Growth Est 20%)
- Quality (ROIC 18%, FCF Yield 18%, Operating Margin 13%, D/E 13%, Cash Conversion 12%, OCF Trend 12%, Current Ratio 7%, Interest Coverage 7%)
  — Banks use: ROE 35%, ROA 25%, D/E 20%, Payout 20%

Quarterly data pipeline (Revenue QoQ, FCF Growth QoQ):
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

from app.analysis.grading import clamp, interpolate, score_to_grade
from app.analysis.peg_calculator import calculate_peg
from app.analysis.sector_benchmarks import get_benchmark, score_relative
from app.schemas.fundamental import (
    FundamentalAnalysis,
    GrowthMetrics,
    MetricScore,
    QualityMetrics,
    ValuationMetrics,
)
from app.services.cache_manager import CacheManager
from app.services.finnhub_service import FinnhubService
from app.services.yfinance_service import YFinanceService

logger = logging.getLogger(__name__)


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

        benchmarks = await self._get_peer_benchmarks(ticker, info)

        # Compute sub-scores (3 pillars)
        valuation = self._score_valuation(info, financials, data_gaps, benchmarks)
        growth = self._score_growth(info, financials, data_gaps, get_benchmark(info.get("sector")))
        quality = self._score_quality(info, financials, data_gaps, benchmarks)

        # Overall: Valuation 35%, Growth 30%, Quality 35%
        sub_scores = [
            (valuation.composite_score, 0.35),
            (growth.composite_score, 0.30),
            (quality.composite_score, 0.35),
        ]
        available_subs = [(s, w) for s, w in sub_scores if s > 0]
        if available_subs:
            total_w = sum(w for _, w in available_subs)
            overall = sum(s * (w / total_w) for s, w in available_subs)
        else:
            overall = 0

        total_metrics = 14
        available_count = total_metrics - len(data_gaps)
        confidence = available_count / total_metrics

        return FundamentalAnalysis(
            ticker=ticker,
            valuation=valuation,
            growth=growth,
            quality=quality,
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
            if not info.get("evFcfRatio") and metric.get("currentEv/freeCashFlowTTM"):
                ev_fcf = metric["currentEv/freeCashFlowTTM"]
                if ev_fcf > 0:
                    info["evFcfRatio"] = ev_fcf
            # EV/EBITDA
            if not info.get("evEbitda") and metric.get("currentEv/ebitdaTTM"):
                info["evEbitda"] = metric["currentEv/ebitdaTTM"]
            # ROIC
            if not info.get("roic"):
                roic = metric.get("roicTTM") or metric.get("roicAnnual")
                if roic is not None:
                    info["roic"] = roic
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
            # Net income for cash conversion ratio
            if not info.get("netIncome") and metric.get("netIncomeAnnual"):
                info["netIncome"] = metric["netIncomeAnnual"]
            # Interest Coverage
            if not info.get("interestCoverage") and metric.get("netInterestCoverageTTM"):
                info["interestCoverage"] = metric["netInterestCoverageTTM"]
            # Current Ratio
            if not info.get("currentRatio"):
                cr = metric.get("currentRatioQuarterly") or metric.get("currentRatioAnnual")
                if cr is not None:
                    info["currentRatio"] = cr

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

        # Build cash_flow dict from XBRL data when yfinance cash flow is missing
        if not data.get("cash_flow") and quarterly:
            cf_data = {}
            for period, values in quarterly.items():
                ocf = values.get("Operating Cash Flow")
                if ocf is not None:
                    entry = {"Operating Cash Flow": ocf}
                    capex = values.get("Capital Expenditure")
                    if capex is not None:
                        entry["Free Cash Flow"] = ocf - abs(capex)
                    cf_data[period] = entry
            if cf_data:
                data["cash_flow"] = cf_data

        return data

    async def _get_quarterly_income(self, ticker: str) -> dict | None:
        """
        3-tier fallback for quarterly income data:
        1. Cache (source=finnhub or edgar, 24h TTL)
        2. Finnhub /stock/financials-reported
        3. SEC EDGAR company_facts
        """
        from app.services.xbrl_mapper import parse_edgar_quarterly, parse_finnhub_quarterly

        for source in ("finnhub", "edgar"):
            cached = await self.cache.get_fundamental(ticker, "quarterly_income", source=source)
            if cached and len(cached) >= 3:
                logger.debug(f"Using cached {source} quarterly data for {ticker} ({len(cached)} quarters)")
                return cached

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

        if self.edgar:
            try:
                cik_cache = await self.cache.get_fundamental(ticker, "cik_mapping", source="edgar", ttl=604800)
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
        cached = await self.cache.get_peer_benchmarks(ticker)
        if cached and cached.get("medians"):
            medians = cached["medians"]
            medians["source"] = cached.get("source", "peers")
            return medians

        peer_tickers = await self.finnhub.get_peers(ticker)
        if peer_tickers and len(peer_tickers) >= 3:
            peer_tickers = peer_tickers[:8]

            tasks = [self.finnhub.get_basic_financials(p) for p in peer_tickers]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            pe_vals, fpe_vals, pb_vals, ps_vals, ev_ebitda_vals = [], [], [], [], []
            for i, result in enumerate(results):
                if isinstance(result, Exception) or result is None:
                    continue
                metric = result.get("metric", {})
                pe = metric.get("peBasicExclExtraTTM")
                fpe = metric.get("forwardPE")
                pb = metric.get("pbAnnual")
                ps = metric.get("psTTM")
                ev_eb = metric.get("currentEv/ebitdaTTM")
                if pe and pe > 0:
                    pe_vals.append(pe)
                if fpe and fpe > 0:
                    fpe_vals.append(fpe)
                if pb and pb > 0:
                    pb_vals.append(pb)
                if ps and ps > 0:
                    ps_vals.append(ps)
                if ev_eb and ev_eb > 0:
                    ev_ebitda_vals.append(ev_eb)

            if len(pe_vals) >= 3:
                sector_fallback = get_benchmark(info.get("sector"))
                pe_median = round(statistics.median(pe_vals), 2)
                medians = {
                    "pe": pe_median,
                    "fpe": round(statistics.median(fpe_vals), 2) if len(fpe_vals) >= 3 else round(pe_median * 0.85, 2),
                    "pb": round(statistics.median(pb_vals), 2) if len(pb_vals) >= 3 else sector_fallback["pb"],
                    "ps": round(statistics.median(ps_vals), 2) if len(ps_vals) >= 3 else sector_fallback["ps"],
                    "peg": sector_fallback["peg"],
                    "ev_ebitda": round(statistics.median(ev_ebitda_vals), 2) if len(ev_ebitda_vals) >= 3 else sector_fallback.get("ev_ebitda", 15),
                }

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

        sector = info.get("sector")
        benchmarks = get_benchmark(sector)
        source = f"sector ({sector})" if sector else "default"

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
        fpe = self._score_forward_pe(info, data_gaps, benchmarks, growth_rate)
        ev_eb = self._score_ev_ebitda(info, data_gaps, benchmarks)
        peg = self._score_peg(info, financials, data_gaps, benchmarks)
        pb = self._score_pb(info, data_gaps, benchmarks)
        ps = self._score_ps(info, data_gaps, benchmarks)

        composite = _weighted_average([
            (fpe, 0.25), (ev_eb, 0.25), (peg, 0.20), (ps, 0.15), (pb, 0.15),
        ])
        return ValuationMetrics(
            forward_pe=fpe,
            ev_ebitda=ev_eb,
            peg_ratio=peg,
            pb_ratio=pb,
            ps_ratio=ps,
            composite_score=round(composite, 1),
            grade=score_to_grade(composite),
        )

    def _get_earnings_growth_rate(self, info: dict, financials: dict) -> float | None:
        """Get best available earnings growth rate as a decimal (0.25 = 25%)."""
        eg = info.get("earningsGrowth")
        if eg is not None and eg > 0:
            return eg

        eg5 = info.get("epsGrowth5Y")
        if eg5 is not None and eg5 > 0:
            return eg5 / 100

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

        BASELINE_GROWTH = 0.08
        growth_ratio = growth_rate / BASELINE_GROWTH
        adjustment = max(1.0, min(growth_ratio ** 0.5, 2.0))
        return benchmark * adjustment

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

    def _score_ev_ebitda(self, info: dict, data_gaps: list, benchmarks: dict) -> MetricScore:
        ev_eb = info.get("evEbitda")
        if ev_eb is None:
            data_gaps.append("EV/EBITDA")
            return MetricScore(description="Not available")
        if ev_eb < 0:
            return MetricScore(value=round(ev_eb, 2), score=10, grade=score_to_grade(10),
                               description="Negative EBITDA")

        benchmark = benchmarks.get("ev_ebitda", 15)
        score = score_relative(ev_eb, benchmark)
        ratio = ev_eb / benchmark if benchmark > 0 else 1
        source = benchmarks.get("source", "sector")

        if ratio < 0.8:
            context = "Cheap vs peers"
        elif ratio < 1.1:
            context = "In line with peers"
        elif ratio < 1.5:
            context = "Premium to peers"
        else:
            context = "Expensive vs peers"

        desc = f"EV/EBITDA {ev_eb:.1f} vs {source} median {benchmark:.1f} — {context}"
        return MetricScore(value=round(ev_eb, 2), score=round(score, 1), grade=score_to_grade(score), description=desc)

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
        fcf_qoq = self._score_fcf_growth_qoq(info, financials, data_gaps)
        fwd = self._score_forward_growth_est(info, data_gaps, sector_benchmarks)

        composite = _weighted_average([
            (rev_yoy, 0.30), (earn_yoy, 0.30), (rev_qoq, 0.10),
            (fcf_qoq, 0.10), (fwd, 0.20),
        ])
        return GrowthMetrics(
            revenue_yoy=rev_yoy,
            earnings_yoy=earn_yoy,
            revenue_qoq=rev_qoq,
            fcf_growth_qoq=fcf_qoq,
            forward_growth_est=fwd,
            composite_score=round(composite, 1),
            grade=score_to_grade(composite),
        )

    def _sector_relative_growth_score(self, pct: float, benchmark: float) -> float:
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

        if revenues[1] == 0:
            data_gaps.append("Revenue QoQ")
            return MetricScore(description="Prior quarter revenue is zero")

        qoq_pct = ((revenues[0] - revenues[1]) / abs(revenues[1])) * 100

        breakpoints = [
            (-15, 5), (-10, 15), (-5, 28), (-2, 40), (0, 50),
            (2, 60), (5, 72), (8, 80), (12, 88), (20, 95),
        ]
        score = interpolate(qoq_pct, breakpoints)

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

    def _score_fcf_growth_qoq(self, info: dict, financials: dict, data_gaps: list) -> MetricScore:
        """Score FCF growth using cash flow statements (annual periods as fallback)."""
        cf = financials.get("cash_flow", {})
        if not cf:
            data_gaps.append("FCF Growth")
            return MetricScore(description="Not available")

        periods = sorted(cf.keys(), reverse=True)
        fcfs = []
        for p in periods[:3]:
            fcf = cf[p].get("Free Cash Flow") or cf[p].get("FreeCashFlow")
            if fcf is not None:
                fcfs.append(fcf)

        if len(fcfs) < 2:
            data_gaps.append("FCF Growth")
            return MetricScore(description="Insufficient FCF data")

        current, prior = fcfs[0], fcfs[1]

        if prior == 0:
            if current > 0:
                score = 75
                desc = "FCF turned positive"
            elif current < 0:
                score = 20
                desc = "FCF remains weak"
            else:
                score = 50
                desc = "FCF flat at zero"
            return MetricScore(value=None, score=score, grade=score_to_grade(score), description=desc)

        growth_pct = ((current - prior) / abs(prior)) * 100

        breakpoints = [
            (-15, 5), (-10, 15), (-5, 28), (-2, 40), (0, 50),
            (2, 60), (5, 72), (8, 80), (12, 88), (20, 95),
        ]
        score = interpolate(growth_pct, breakpoints)

        # Momentum adjustment
        momentum = ""
        if len(fcfs) >= 3 and fcfs[2] != 0:
            prior_growth = ((prior - fcfs[2]) / abs(fcfs[2])) * 100
            if growth_pct > prior_growth + 2:
                score = min(score + 10, 99)
                momentum = " (accelerating)"
            elif growth_pct < prior_growth - 2:
                score = max(score - 10, 1)
                momentum = " (decelerating)"
            else:
                momentum = " (stable)"

        desc = f"FCF {growth_pct:+.1f}% growth{momentum}"
        return MetricScore(value=round(growth_pct, 1), score=round(score, 1),
                           grade=score_to_grade(score), description=desc)

    def _score_forward_growth_est(self, info: dict, data_gaps: list, sector_benchmarks: dict) -> MetricScore:
        """Score forward-looking growth using analyst target price upside or earnings growth estimate."""
        target = info.get("targetMeanPrice")
        current = info.get("currentPrice") or info.get("regularMarketPrice")

        # Try analyst target price upside as a forward-looking signal
        if target and current and current > 0:
            upside = ((target - current) / current) * 100
            score = clamp(50 + upside, 0, 100)
            return MetricScore(value=round(upside, 1), score=round(score, 1), grade=score_to_grade(score),
                               description=f"Analyst target {upside:+.1f}% upside")

        # Fallback: use forward earnings growth if available
        growth = info.get("earningsGrowth")
        if growth:
            pct = growth * 100
            benchmark = sector_benchmarks.get("earnings_growth", 10)
            absolute_score = self._growth_rate_score(pct)
            relative_score = self._sector_relative_growth_score(pct, benchmark)
            score = round((absolute_score + relative_score) / 2, 1)
            return MetricScore(value=round(pct, 1), score=score, grade=score_to_grade(score),
                               description=f"Forward est. {pct:+.1f}% (sector avg: {benchmark}%)")

        data_gaps.append("Forward Growth Est.")
        return MetricScore(description="Not available")

    # ── Quality Scoring ──────────────────────────────────────────────
    # Standard weights: ROIC 18%, FCF 18%, OpMargin 13%, D/E 13%, Cash Conv 12%, OCF 12%, CR 7%, IC 7%
    # Bank weights: ROE 35%, ROA 25%, D/E (lenient) 20%, Payout 20%

    @staticmethod
    def _is_financial_sector(sector: str | None) -> bool:
        if not sector:
            return False
        s = sector.lower()
        return any(x in s for x in ["financial", "banking", "insurance", "bank"])

    def _score_quality(self, info: dict, financials: dict, data_gaps: list, benchmarks: dict) -> QualityMetrics:
        if self._is_financial_sector(info.get("sector")):
            return self._score_bank_quality(info, data_gaps)
        return self._score_standard_quality(info, financials, data_gaps, benchmarks)

    def _score_standard_quality(self, info: dict, financials: dict, data_gaps: list, benchmarks: dict) -> QualityMetrics:
        roic = self._score_roic(info, data_gaps)
        fcf = self._score_fcf_yield(info, financials, data_gaps)
        om = self._score_operating_margin(info, data_gaps, benchmarks)
        de = self._score_debt_to_equity(info, data_gaps)
        cc = self._score_cash_conversion(info, financials, data_gaps)
        ocf = self._score_ocf_trend(financials, data_gaps)
        cr = self._score_current_ratio(info, data_gaps)
        ic = self._score_interest_coverage(info, data_gaps)

        composite = _weighted_average([
            (roic, 0.18), (fcf, 0.18), (om, 0.13), (de, 0.13),
            (cc, 0.12), (ocf, 0.12), (cr, 0.07), (ic, 0.07),
        ])
        return QualityMetrics(
            roic=roic,
            fcf_yield=fcf,
            operating_margin=om,
            debt_to_equity=de,
            cash_conversion=cc,
            ocf_trend=ocf,
            current_ratio=cr,
            interest_coverage=ic,
            composite_score=round(composite, 1),
            grade=score_to_grade(composite),
        )

    def _score_bank_quality(self, info: dict, data_gaps: list) -> QualityMetrics:
        de = self._score_bank_debt_to_equity(info, data_gaps)
        roe = self._score_roe(info, data_gaps)
        roa = self._score_roa(info, data_gaps)
        pr = self._score_payout_ratio(info, data_gaps)

        composite = _weighted_average([
            (roe, 0.35), (roa, 0.25), (de, 0.20), (pr, 0.20),
        ])
        return QualityMetrics(
            debt_to_equity=de,
            roe=roe,
            roa=roa,
            payout_ratio=pr,
            composite_score=round(composite, 1),
            grade=score_to_grade(composite),
        )

    def _score_roic(self, info: dict, data_gaps: list) -> MetricScore:
        roic = info.get("roic")
        if roic is None:
            data_gaps.append("ROIC")
            return MetricScore(description="Not available")

        score = interpolate(roic, [
            (0, 5), (3, 15), (5, 25), (8, 40), (10, 50),
            (12, 60), (15, 72), (20, 85), (25, 92), (30, 95),
        ])

        if roic >= 20:
            desc = f"ROIC {roic:.1f}% — Excellent capital efficiency"
        elif roic >= 12:
            desc = f"ROIC {roic:.1f}% — Good capital efficiency"
        elif roic >= 8:
            desc = f"ROIC {roic:.1f}% — Average capital efficiency"
        elif roic >= 5:
            desc = f"ROIC {roic:.1f}% — Below average"
        else:
            desc = f"ROIC {roic:.1f}% — Poor capital efficiency"

        return MetricScore(value=round(roic, 2), score=round(score, 1),
                           grade=score_to_grade(score), description=desc)

    def _score_debt_to_equity(self, info: dict, data_gaps: list) -> MetricScore:
        de = info.get("debtToEquity")
        if de is None:
            data_gaps.append("Debt/Equity")
            return MetricScore(description="Not available")
        de_ratio = de / 100 if de > 10 else de

        score = interpolate(de_ratio, [
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

    def _score_fcf_yield(self, info: dict, financials: dict, data_gaps: list) -> MetricScore:
        fcf = info.get("freeCashflow")
        market_cap = info.get("marketCap")
        fcf_yield = None

        if fcf and market_cap and market_cap > 0:
            fcf_yield = (fcf / market_cap) * 100
        else:
            cf = financials.get("cash_flow", {})
            if cf:
                latest = sorted(cf.keys(), reverse=True)
                if latest:
                    stmt_fcf = cf[latest[0]].get("Free Cash Flow") or cf[latest[0]].get("FreeCashFlow")
                    if stmt_fcf and market_cap and market_cap > 0:
                        fcf_yield = (stmt_fcf / market_cap) * 100

        if fcf_yield is None and info.get("evFcfRatio"):
            ev_fcf = info["evFcfRatio"]
            if ev_fcf > 0:
                fcf_yield = (1.0 / ev_fcf) * 100

        if fcf_yield is None:
            data_gaps.append("FCF Yield")
            return MetricScore(description="Not available")

        score = interpolate(fcf_yield, [
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

    def _score_operating_margin(self, info: dict, data_gaps: list, benchmarks: dict) -> MetricScore:
        """Score operating margin relative to sector benchmark."""
        om = info.get("operatingMargins")
        if om is None:
            data_gaps.append("Operating Margin")
            return MetricScore(description="Not available")

        pct = om * 100
        sector_benchmarks = get_benchmark(info.get("sector"))
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
                score = 50.0
                for i in range(len(breakpoints) - 1):
                    r1, s1 = breakpoints[i]
                    r2, s2 = breakpoints[i + 1]
                    if r1 <= ratio <= r2:
                        t = (ratio - r1) / (r2 - r1) if r2 > r1 else 0
                        score = round(s1 + t * (s2 - s1), 1)
                        break
        else:
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

    def _score_cash_conversion(self, info: dict, financials: dict, data_gaps: list) -> MetricScore:
        """
        Cash Conversion Ratio = FCF / Net Income.
        Cross-checks earnings quality: a healthy company converts most net income to FCF.
        """
        fcf = info.get("freeCashflow")
        if fcf is None:
            cf = financials.get("cash_flow", {})
            if cf:
                latest = sorted(cf.keys(), reverse=True)
                if latest:
                    fcf = cf[latest[0]].get("Free Cash Flow") or cf[latest[0]].get("FreeCashFlow")

        # Get net income from multiple sources
        net_income = info.get("netIncome")
        if net_income is None:
            inc = financials.get("income_statement", {})
            if inc:
                latest = sorted(inc.keys(), reverse=True)
                if latest:
                    net_income = inc[latest[0]].get("Net Income") or inc[latest[0]].get("NetIncome")
        if net_income is None:
            pm = info.get("profitMargins")
            rev = info.get("totalRevenue") or info.get("revenue")
            if pm is not None and rev:
                net_income = pm * rev

        if fcf is None or net_income is None:
            data_gaps.append("Cash Conversion")
            return MetricScore(description="Not available")

        # Edge cases for sign mismatches
        if net_income < 0 and fcf > 0:
            return MetricScore(value=None, score=80, grade=score_to_grade(80),
                               description="Positive FCF despite accounting loss — good cash generation")
        if net_income < 0 and fcf <= 0:
            return MetricScore(value=None, score=25, grade=score_to_grade(25),
                               description="Both NI and FCF negative — weak")
        if net_income == 0:
            score = 60 if fcf > 0 else 30
            return MetricScore(value=None, score=score, grade=score_to_grade(score),
                               description=f"Zero net income, FCF {'positive' if fcf > 0 else 'negative'}")

        ratio = fcf / net_income

        breakpoints = [
            (-0.5, 5),   # FCF deeply negative vs positive NI
            (0.0, 15),   # Zero FCF
            (0.3, 30),   # FCF well below NI
            (0.6, 42),   # FCF lagging NI
            (0.8, 55),   # Slightly below — acceptable
            (1.0, 70),   # FCF matches NI — healthy
            (1.2, 80),   # FCF exceeds NI — strong
            (1.5, 88),   # Much more FCF than NI
            (2.0, 92),   # Very high conversion
        ]
        score = interpolate(ratio, breakpoints)

        if ratio >= 1.2:
            desc = f"CCR {ratio:.2f}x — Excellent cash conversion"
        elif ratio >= 0.8:
            desc = f"CCR {ratio:.2f}x — Healthy cash conversion"
        elif ratio >= 0.5:
            desc = f"CCR {ratio:.2f}x — FCF lagging earnings"
        elif ratio >= 0:
            desc = f"CCR {ratio:.2f}x — Weak cash conversion"
        else:
            desc = f"CCR {ratio:.2f}x — Negative FCF despite positive earnings"

        return MetricScore(value=round(ratio, 2), score=round(score, 1),
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

        if ocfs[1] != 0:
            growth_pct = ((ocfs[0] - ocfs[1]) / abs(ocfs[1])) * 100
        else:
            growth_pct = 100 if ocfs[0] > 0 else -100

        if ocfs[0] > 0:
            score = interpolate(growth_pct, [
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
            score = interpolate(growth_pct, [
                (-50, 5), (-20, 12), (0, 20), (50, 30),
            ])
            desc = "Negative operating cash flow"

        return MetricScore(value=round(ocfs[0], 0), score=round(score, 1),
                           grade=score_to_grade(score), description=desc)

    def _score_current_ratio(self, info: dict, data_gaps: list) -> MetricScore:
        cr = info.get("currentRatio")
        if cr is None:
            data_gaps.append("Current Ratio")
            return MetricScore(description="Not available")

        # Peaks around 2.0; penalizes both too-low (liquidity risk) and too-high (capital inefficiency)
        score = interpolate(cr, [
            (0.3, 5), (0.5, 15), (0.8, 35), (1.0, 50), (1.2, 62),
            (1.5, 75), (2.0, 82), (2.5, 75), (3.0, 65), (5.0, 45),
        ])

        if cr >= 2.5:
            desc = f"CR {cr:.2f} — High, may indicate idle capital"
        elif cr >= 1.5:
            desc = f"CR {cr:.2f} — Healthy liquidity"
        elif cr >= 1.0:
            desc = f"CR {cr:.2f} — Adequate liquidity"
        elif cr >= 0.8:
            desc = f"CR {cr:.2f} — Tight liquidity"
        else:
            desc = f"CR {cr:.2f} — Liquidity risk"

        return MetricScore(value=round(cr, 2), score=round(score, 1),
                           grade=score_to_grade(score), description=desc)

    def _score_interest_coverage(self, info: dict, data_gaps: list) -> MetricScore:
        ic = info.get("interestCoverage")
        if ic is None:
            data_gaps.append("Interest Coverage")
            return MetricScore(description="Not available")

        score = interpolate(ic, [
            (0, 5), (1.0, 15), (1.5, 25), (2.5, 40), (4.0, 55),
            (6.0, 65), (8.0, 72), (10.0, 78), (15.0, 85), (25.0, 88),
        ])

        if ic >= 15:
            desc = f"IC {ic:.1f}x — Excellent debt service capacity"
        elif ic >= 6:
            desc = f"IC {ic:.1f}x — Comfortable coverage"
        elif ic >= 2.5:
            desc = f"IC {ic:.1f}x — Adequate coverage"
        elif ic >= 1.5:
            desc = f"IC {ic:.1f}x — Tight coverage"
        else:
            desc = f"IC {ic:.1f}x — Dangerous, may struggle to cover interest"

        return MetricScore(value=round(ic, 2), score=round(score, 1),
                           grade=score_to_grade(score), description=desc)

    # ── Bank-Specific Quality Methods ─────────────────────────────────

    def _score_bank_debt_to_equity(self, info: dict, data_gaps: list) -> MetricScore:
        de = info.get("debtToEquity")
        if de is None:
            data_gaps.append("Debt/Equity")
            return MetricScore(description="Not available")
        de_ratio = de / 100 if de > 10 else de

        score = interpolate(de_ratio, [
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

        score = interpolate(roe, [
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

        score = interpolate(roa, [
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

        score = interpolate(pr, [
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

    # ── Helpers ───────────────────────────────────────────────────────

    def _growth_rate_score(self, pct: float) -> float:
        return interpolate(pct, [
            (-50, 1), (-30, 8), (-20, 15), (-10, 25), (-5, 35),
            (0, 45), (5, 55), (15, 70), (25, 85), (50, 95),
        ])

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
