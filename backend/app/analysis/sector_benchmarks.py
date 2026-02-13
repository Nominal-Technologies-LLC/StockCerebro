"""
Sector-relative valuation benchmarks.

Provides median valuation metrics per GICS sector and a continuous
interpolated scoring function that compares a stock's metric to its
sector/peer benchmark.
"""

# Median valuation and profitability metrics by GICS sector.
# Sources: approximate cross-sector medians from S&P 500 constituents.
# These serve as fallback when live peer data isn't available.
SECTOR_BENCHMARKS: dict[str, dict[str, float]] = {
    "Technology":              {"pe": 28, "fpe": 24, "pb": 7,   "ps": 6,   "peg": 1.5, "gross_margin": 65, "operating_margin": 25, "net_margin": 20, "revenue_growth": 15, "earnings_growth": 18},
    "Communication Services":  {"pe": 22, "fpe": 19, "pb": 3.5, "ps": 3.5, "peg": 1.8, "gross_margin": 55, "operating_margin": 20, "net_margin": 15, "revenue_growth": 8,  "earnings_growth": 10},
    "Consumer Cyclical":       {"pe": 22, "fpe": 19, "pb": 5,   "ps": 1.5, "peg": 1.4, "gross_margin": 35, "operating_margin": 8,  "net_margin": 5,  "revenue_growth": 8,  "earnings_growth": 10},
    "Consumer Defensive":      {"pe": 22, "fpe": 20, "pb": 5,   "ps": 1.8, "peg": 2.5, "gross_margin": 30, "operating_margin": 10, "net_margin": 6,  "revenue_growth": 3,  "earnings_growth": 5},
    "Healthcare":              {"pe": 25, "fpe": 20, "pb": 4,   "ps": 4,   "peg": 1.8, "gross_margin": 65, "operating_margin": 18, "net_margin": 12, "revenue_growth": 10, "earnings_growth": 12},
    "Financial Services":      {"pe": 13, "fpe": 12, "pb": 1.3, "ps": 3,   "peg": 1.5, "gross_margin": 70, "operating_margin": 30, "net_margin": 22, "revenue_growth": 5,  "earnings_growth": 8},
    "Industrials":             {"pe": 20, "fpe": 18, "pb": 4,   "ps": 2,   "peg": 1.7, "gross_margin": 25, "operating_margin": 10, "net_margin": 6,  "revenue_growth": 5,  "earnings_growth": 8},
    "Energy":                  {"pe": 12, "fpe": 11, "pb": 1.8, "ps": 1.2, "peg": 1.0, "gross_margin": 20, "operating_margin": 8,  "net_margin": 5,  "revenue_growth": 5,  "earnings_growth": 8},
    "Basic Materials":         {"pe": 15, "fpe": 13, "pb": 2,   "ps": 1.5, "peg": 1.5, "gross_margin": 20, "operating_margin": 12, "net_margin": 8,  "revenue_growth": 4,  "earnings_growth": 6},
    "Utilities":               {"pe": 17, "fpe": 16, "pb": 1.8, "ps": 2.5, "peg": 3.0, "gross_margin": 35, "operating_margin": 18, "net_margin": 12, "revenue_growth": 3,  "earnings_growth": 4},
    "Real Estate":             {"pe": 35, "fpe": 30, "pb": 2,   "ps": 8,   "peg": 2.5, "gross_margin": 45, "operating_margin": 25, "net_margin": 15, "revenue_growth": 5,  "earnings_growth": 6},
}

# Default benchmark for unknown sectors
DEFAULT_BENCHMARK: dict[str, float] = {"pe": 20, "fpe": 17, "pb": 3, "ps": 3, "peg": 1.5, "gross_margin": 40, "operating_margin": 15, "net_margin": 10, "revenue_growth": 8, "earnings_growth": 10}

# Aliases: map alternate sector names from different data sources to canonical names
_ALIASES: dict[str, str] = {
    "technology":               "Technology",
    "tech":                     "Technology",
    "information technology":   "Technology",
    "communication services":   "Communication Services",
    "communication":            "Communication Services",
    "media":                    "Communication Services",
    "consumer cyclical":        "Consumer Cyclical",
    "consumer discretionary":   "Consumer Cyclical",
    "consumer defensive":       "Consumer Defensive",
    "consumer staples":         "Consumer Defensive",
    "healthcare":               "Healthcare",
    "health care":              "Healthcare",
    "financial services":       "Financial Services",
    "financials":               "Financial Services",
    "financial":                "Financial Services",
    "industrials":              "Industrials",
    "industrial":               "Industrials",
    "energy":                   "Energy",
    "basic materials":          "Basic Materials",
    "materials":                "Basic Materials",
    "utilities":                "Utilities",
    "real estate":              "Real Estate",
}


def get_benchmark(sector: str | None) -> dict[str, float]:
    """Return benchmark medians for the given sector name, with fuzzy matching."""
    if not sector:
        return DEFAULT_BENCHMARK

    # Try direct match
    if sector in SECTOR_BENCHMARKS:
        return SECTOR_BENCHMARKS[sector]

    # Try alias lookup (case-insensitive)
    canonical = _ALIASES.get(sector.lower().strip())
    if canonical and canonical in SECTOR_BENCHMARKS:
        return SECTOR_BENCHMARKS[canonical]

    # Try substring matching as last resort
    sector_lower = sector.lower()
    for alias, canonical in _ALIASES.items():
        if alias in sector_lower or sector_lower in alias:
            if canonical in SECTOR_BENCHMARKS:
                return SECTOR_BENCHMARKS[canonical]

    return DEFAULT_BENCHMARK


def score_relative(value: float, benchmark: float, lower_is_better: bool = True) -> float:
    """
    Score a valuation metric relative to a benchmark using linear interpolation.

    For lower_is_better=True (PE, P/B, P/S, PEG):
      ratio < 1 means stock is cheaper than benchmark → higher score
      ratio > 1 means stock is more expensive → lower score

    Returns a score between 0 and 100.
    """
    if benchmark <= 0:
        return 50.0  # Can't compare to zero/negative benchmark

    ratio = value / benchmark
    if not lower_is_better:
        # Invert: higher-is-better (not used for valuation but available)
        ratio = benchmark / value if value > 0 else 3.0

    # Interpolation breakpoints: (ratio, score)
    breakpoints = [
        (0.0, 98),
        (0.4, 95),
        (0.6, 85),
        (0.8, 72),
        (1.0, 60),
        (1.2, 50),
        (1.5, 38),
        (2.0, 25),
        (3.0, 10),
    ]

    # Clamp at boundaries
    if ratio <= breakpoints[0][0]:
        return float(breakpoints[0][1])
    if ratio >= breakpoints[-1][0]:
        return float(breakpoints[-1][1])

    # Linear interpolation between adjacent breakpoints
    for i in range(len(breakpoints) - 1):
        r1, s1 = breakpoints[i]
        r2, s2 = breakpoints[i + 1]
        if r1 <= ratio <= r2:
            t = (ratio - r1) / (r2 - r1)
            return round(s1 + t * (s2 - s1), 1)

    return 50.0
