"""API request validation utilities."""
import re
from fastapi import HTTPException


def validate_ticker(ticker: str) -> str:
    """Validate and normalize ticker symbol.

    Args:
        ticker: Raw ticker string from request

    Returns:
        Validated and normalized ticker (uppercase, stripped)

    Raises:
        HTTPException: If ticker is invalid
    """
    if not ticker or not ticker.strip():
        raise HTTPException(status_code=400, detail="Ticker cannot be empty")

    ticker = ticker.upper().strip()

    # Valid tickers: 1-10 chars, letters, numbers, dots, dashes
    # Examples: AAPL, BRK.B, SPY, QQQ, MSFT
    if not re.match(r'^[A-Z0-9.\-]{1,10}$', ticker):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid ticker format: '{ticker}'. Use 1-10 alphanumeric characters."
        )

    return ticker
