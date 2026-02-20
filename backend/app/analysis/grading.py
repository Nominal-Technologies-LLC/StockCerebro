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


def interpolate(value: float, breakpoints: list[tuple[float, float]]) -> float:
    """Smooth linear interpolation between breakpoints [(input_value, score), ...]."""
    import math

    if not isinstance(value, (int, float)) or math.isnan(value) or math.isinf(value):
        return 50.0

    for v, s in breakpoints:
        if math.isnan(v) or math.isinf(v) or math.isnan(s) or math.isinf(s):
            return 50.0

    if value <= breakpoints[0][0]:
        return float(breakpoints[0][1])
    if value >= breakpoints[-1][0]:
        return float(breakpoints[-1][1])
    for i in range(len(breakpoints) - 1):
        v1, s1 = breakpoints[i]
        v2, s2 = breakpoints[i + 1]
        if v1 <= value <= v2:
            if v2 - v1 == 0:
                return float(s1)
            t = (value - v1) / (v2 - v1)
            return round(s1 + t * (s2 - s1), 1)
    return 50.0
