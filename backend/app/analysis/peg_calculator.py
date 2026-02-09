"""
Manual PEG ratio calculation.
yfinance pegRatio is broken since June 2025, so we compute it ourselves.

PEG = trailing_PE / (earnings_growth_rate * 100)

Growth rate sources (in priority order):
1. Analyst consensus 5-year earnings growth estimate
2. Trailing 3-year EPS CAGR calculated from income statements
"""
import logging
import math

logger = logging.getLogger(__name__)


def calculate_peg(info: dict, financials: dict) -> tuple[float | None, str]:
    """
    Returns (peg_ratio, method_used).
    method_used is one of: 'analyst_estimate', 'trailing_3yr', 'unavailable'
    """
    trailing_pe = info.get("trailingPE")
    if not trailing_pe or trailing_pe <= 0:
        return None, "unavailable"

    # Method 1: Analyst 5-year growth estimate
    growth_est = info.get("earningsGrowth")  # sometimes available as decimal
    # Try earningsQuarterlyGrowth or analyst targets
    five_yr_growth = info.get("earningsGrowth")

    # Check for analyst growth data
    if five_yr_growth and five_yr_growth > 0:
        peg = trailing_pe / (five_yr_growth * 100)
        return round(peg, 2), "analyst_estimate"

    # Method 2: Trailing 3-year EPS CAGR
    eps_growth = _calc_trailing_eps_growth(financials)
    if eps_growth and eps_growth > 0:
        peg = trailing_pe / (eps_growth * 100)
        return round(peg, 2), "trailing_3yr"

    return None, "unavailable"


def _calc_trailing_eps_growth(financials: dict) -> float | None:
    """Calculate 3-year EPS CAGR from income statement data."""
    income = financials.get("income_statement")
    if not income:
        return None

    # Get sorted periods (most recent first)
    periods = sorted(income.keys(), reverse=True)
    if len(periods) < 2:
        return None

    # Get net income and shares outstanding for CAGR
    recent = income[periods[0]]
    oldest_idx = min(3, len(periods) - 1)
    oldest = income[periods[oldest_idx]]

    recent_ni = recent.get("Net Income") or recent.get("NetIncome")
    oldest_ni = oldest.get("Net Income") or oldest.get("NetIncome")

    if not recent_ni or not oldest_ni or oldest_ni <= 0 or recent_ni <= 0:
        return None

    years = oldest_idx
    if years <= 0:
        return None

    try:
        cagr = (recent_ni / oldest_ni) ** (1 / years) - 1
        if math.isnan(cagr) or math.isinf(cagr):
            return None
        return cagr
    except (ValueError, ZeroDivisionError):
        return None
