"""Shared grading utilities for converting scores to letter grades and signals."""


def score_to_grade(score: float) -> str:
    if score >= 93:
        return "A+"
    elif score >= 90:
        return "A"
    elif score >= 87:
        return "A-"
    elif score >= 83:
        return "B+"
    elif score >= 80:
        return "B"
    elif score >= 77:
        return "B-"
    elif score >= 73:
        return "C+"
    elif score >= 70:
        return "C"
    elif score >= 67:
        return "C-"
    elif score >= 63:
        return "D+"
    elif score >= 60:
        return "D"
    elif score >= 50:
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
