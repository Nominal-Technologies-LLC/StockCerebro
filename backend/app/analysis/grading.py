"""Shared grading utilities for converting scores to letter grades and signals."""


def score_to_grade(score: float) -> str:
    """Convert a 0-100 score to a letter grade.

    Centered so 50 = average (C range), matching intuitive stock ratings:
      A = great, B = pretty good, C = ok, D = not good, F = stay clear.
    """
    if score >= 92:
        return "A+"
    elif score >= 85:
        return "A"
    elif score >= 80:
        return "A-"
    elif score >= 75:
        return "B+"
    elif score >= 70:
        return "B"
    elif score >= 65:
        return "B-"
    elif score >= 60:
        return "C+"
    elif score >= 55:
        return "C"
    elif score >= 50:
        return "C-"
    elif score >= 45:
        return "D+"
    elif score >= 38:
        return "D"
    elif score >= 30:
        return "D-"
    elif score >= 20:
        return "F+"
    else:
        return "F"


def score_to_signal(score: float) -> str:
    if score >= 80:
        return "STRONG BUY"
    elif score >= 65:
        return "BUY"
    elif score >= 45:
        return "HOLD"
    elif score >= 30:
        return "SELL"
    else:
        return "STRONG SELL"


def clamp(value: float, low: float = 0, high: float = 100) -> float:
    return max(low, min(high, value))
