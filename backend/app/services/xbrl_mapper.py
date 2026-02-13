"""
XBRL-to-dict converter for Finnhub and EDGAR quarterly financial data.

Outputs the same shape as yfinance quarterly income data:
{
    "2024-12-31": {"Total Revenue": 124.3e9, "Net Income": 36.3e9, "Operating Income": 42.8e9},
    "2024-09-30": {...},
    ...
}

IMPORTANT: SEC 10-Q income statements report cumulative year-to-date figures:
  Q1 = standalone quarter
  Q2 = 6-month cumulative (need to subtract Q1)
  Q3 = 9-month cumulative (need to subtract Q1+Q2)
  Q4 = annual (from 10-K, excluded here)
This module de-accumulates to produce standalone quarterly numbers.
"""
import logging
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)

# XBRL concept mapping — companies use different GAAP tags
REVENUE_CONCEPTS = [
    "us-gaap_Revenues",
    "us-gaap_RevenueFromContractWithCustomerExcludingAssessedTax",
    "us-gaap_SalesRevenueNet",
    "us-gaap_InterestAndDividendIncomeOperating",  # Banks
]
NET_INCOME_CONCEPTS = [
    "us-gaap_NetIncomeLoss",
    "us-gaap_ProfitLoss",
]
OPERATING_INCOME_CONCEPTS = [
    "us-gaap_OperatingIncomeLoss",
]

_METRIC_KEYS = ["Total Revenue", "Net Income", "Operating Income"]


def _first_match(report_data: dict, concepts: list[str]) -> float | None:
    """Return the value for the first matching XBRL concept found in a report."""
    for concept in concepts:
        val = report_data.get(concept)
        if val is not None:
            try:
                return float(val)
            except (ValueError, TypeError):
                continue
    return None


def _parse_date(s: str) -> datetime | None:
    """Parse date string like '2024-12-31' or '2024-12-31 00:00:00'."""
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def parse_finnhub_quarterly(reports: list[dict]) -> dict:
    """
    Parse Finnhub /stock/financials-reported response data array
    into standalone quarterly income dict keyed by period end date.

    Handles cumulative YTD figures by grouping by fiscal year start
    and de-accumulating to get standalone quarters.
    """
    # First pass: extract raw data with start/end dates
    raw_entries = []
    for entry in reports:
        report = entry.get("report", {})
        if not report:
            continue

        start_str = entry.get("startDate", "")
        end_str = entry.get("endDate", "")
        start_dt = _parse_date(start_str)
        end_dt = _parse_date(end_str)

        if not end_dt:
            continue

        # Flatten the report sections
        flat = {}
        for section_key in ("ic", "bs", "cf"):
            section = report.get(section_key, [])
            if isinstance(section, list):
                for item in section:
                    concept = item.get("concept", "")
                    value = item.get("value")
                    if concept and value is not None:
                        flat[concept] = value

        revenue = _first_match(flat, REVENUE_CONCEPTS)
        net_income = _first_match(flat, NET_INCOME_CONCEPTS)
        operating_income = _first_match(flat, OPERATING_INCOME_CONCEPTS)

        if revenue is None and net_income is None:
            continue

        period_data = {}
        if revenue is not None:
            period_data["Total Revenue"] = revenue
        if net_income is not None:
            period_data["Net Income"] = net_income
        if operating_income is not None:
            period_data["Operating Income"] = operating_income

        days = (end_dt - start_dt).days if start_dt else 0

        raw_entries.append({
            "start": start_dt,
            "end": end_dt,
            "end_key": end_dt.strftime("%Y-%m-%d"),
            "days": days,
            "data": period_data,
        })

    if not raw_entries:
        return {}

    # Group entries by fiscal year start date for de-accumulation
    # Entries with the same start date belong to the same fiscal year
    fy_groups: dict[str, list[dict]] = defaultdict(list)
    standalone_entries = []

    for entry in raw_entries:
        days = entry["days"]
        if days <= 0 or (85 <= days <= 100):
            # Standalone quarter (~90 days) or no start date
            standalone_entries.append(entry)
        else:
            # Cumulative YTD — group by fiscal year start
            start_key = entry["start"].strftime("%Y-%m-%d") if entry["start"] else "unknown"
            fy_groups[start_key].append(entry)

    result = {}

    # Add standalone quarters directly
    for entry in standalone_entries:
        result[entry["end_key"]] = entry["data"]

    # De-accumulate cumulative entries within each fiscal year
    for fy_start, entries in fy_groups.items():
        # Sort by end date (ascending) so we can subtract prior cumulative
        entries.sort(key=lambda e: e["end"])

        for i, entry in enumerate(entries):
            if i == 0:
                # First cumulative entry — this is Q1 if it's ~90 days,
                # or a 6-month entry if standalone Q1 was already captured
                # Check if we already have a standalone entry near this fiscal year start
                standalone_q1 = None
                for se in standalone_entries:
                    # Find standalone Q1 with matching fiscal year
                    if se["start"] and se["start"].strftime("%Y-%m-%d") == fy_start:
                        standalone_q1 = se
                        break

                if standalone_q1:
                    # De-accumulate: this cumulative entry minus standalone Q1
                    deaccum = {}
                    for key in _METRIC_KEYS:
                        cum_val = entry["data"].get(key)
                        q1_val = standalone_q1["data"].get(key)
                        if cum_val is not None and q1_val is not None:
                            deaccum[key] = cum_val - q1_val
                    if deaccum:
                        result[entry["end_key"]] = deaccum
                else:
                    # No standalone Q1 found — treat this cumulative as standalone
                    # (might be Q1 itself with a slightly off date range)
                    result[entry["end_key"]] = entry["data"]
            else:
                # Subtract prior cumulative to get standalone quarter
                prior = entries[i - 1]
                deaccum = {}
                for key in _METRIC_KEYS:
                    cum_val = entry["data"].get(key)
                    prior_val = prior["data"].get(key)
                    if cum_val is not None and prior_val is not None:
                        deaccum[key] = cum_val - prior_val
                if deaccum:
                    result[entry["end_key"]] = deaccum

    logger.info(f"Parsed {len(result)} quarters from Finnhub financials-reported")
    return result


def parse_edgar_quarterly(facts: dict) -> dict:
    """
    Parse SEC EDGAR company_facts response into quarterly income dict.

    EDGAR data already has start/end dates with period duration, so we filter
    for standalone quarterly periods (~90 days) directly.

    The facts response structure:
    {
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            {"end": "2024-12-31", "val": 124300000000, "form": "10-Q", "filed": "2025-01-30", ...},
                            ...
                        ]
                    }
                },
                ...
            }
        }
    }
    """
    us_gaap = facts.get("facts", {}).get("us-gaap", {})
    if not us_gaap:
        return {}

    # Collect all quarterly data points by period end date
    period_data: dict[str, dict[str, float]] = defaultdict(dict)

    def _extract_concept(gaap_data: dict, concepts: list[str], output_key: str):
        for concept in concepts:
            # Concepts in EDGAR don't have the "us-gaap_" prefix
            clean_concept = concept.replace("us-gaap_", "")
            concept_data = gaap_data.get(clean_concept, {})
            units = concept_data.get("units", {})
            usd_entries = units.get("USD", [])

            if not usd_entries:
                continue

            # Filter for 10-Q filings (quarterly) and deduplicate by period
            quarterly_entries: dict[str, dict] = {}
            for entry in usd_entries:
                form = entry.get("form", "")
                if form not in ("10-Q", "10-Q/A"):
                    continue

                end = entry.get("end", "")
                start = entry.get("start", "")
                filed = entry.get("filed", "")
                val = entry.get("val")

                if not end or val is None:
                    continue

                # Filter out cumulative YTD aggregates
                # Quarterly periods should be ~90 days
                if start:
                    try:
                        s = datetime.strptime(start, "%Y-%m-%d")
                        e = datetime.strptime(end, "%Y-%m-%d")
                        days = (e - s).days
                        if days > 120:  # Skip anything longer than ~4 months
                            continue
                    except ValueError:
                        pass

                # Deduplicate: keep the latest filing for each period
                existing = quarterly_entries.get(end)
                if existing is None or filed > existing.get("filed", ""):
                    quarterly_entries[end] = {"val": val, "filed": filed}

            for end_date, data in quarterly_entries.items():
                period_data[end_date][output_key] = float(data["val"])

    _extract_concept(us_gaap, REVENUE_CONCEPTS, "Total Revenue")
    _extract_concept(us_gaap, NET_INCOME_CONCEPTS, "Net Income")
    _extract_concept(us_gaap, OPERATING_INCOME_CONCEPTS, "Operating Income")

    # Only keep periods that have at least revenue or net income
    result = {
        period: data
        for period, data in period_data.items()
        if "Total Revenue" in data or "Net Income" in data
    }

    logger.info(f"Parsed {len(result)} quarters from EDGAR company facts")
    return result
