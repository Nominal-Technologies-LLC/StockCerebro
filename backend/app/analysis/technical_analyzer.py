"""
Technical analysis engine.
Computes per-timeframe score (0-100):
- Moving Averages (35%): Price vs SMA/EMA, golden/death cross
- MACD (25%): Line vs signal, histogram momentum, zero-line, crossovers
- RSI (20%): Mean-reversion scoring
- Support/Resistance (20%): Proximity, breakout detection
"""
import logging
import math

import numpy as np

from app.analysis.grading import clamp, score_to_grade, score_to_signal
from app.schemas.technical import (
    MACDData,
    MovingAverageSignal,
    RSIData,
    SupportResistance,
    TechnicalAnalysis,
)

logger = logging.getLogger(__name__)


class TechnicalAnalyzer:
    def analyze(self, ticker: str, bars: list[dict], timeframe: str) -> TechnicalAnalysis | None:
        if len(bars) < 20:
            return None

        closes = np.array([b["close"] for b in bars], dtype=float)
        highs = np.array([b["high"] for b in bars], dtype=float)
        lows = np.array([b["low"] for b in bars], dtype=float)
        current_price = closes[-1]

        # Moving averages
        ma_signals, ma_score = self._compute_moving_averages(closes, current_price, timeframe)

        # MACD
        macd_data = self._compute_macd(closes)

        # RSI
        rsi_data = self._compute_rsi(closes)

        # Support/Resistance
        sr_data = self._compute_support_resistance(highs, lows, closes, current_price)

        # Overall score
        overall = ma_score * 0.35 + macd_data.score * 0.25 + rsi_data.score * 0.20 + sr_data.score * 0.20

        return TechnicalAnalysis(
            ticker=ticker,
            timeframe=timeframe,
            current_price=round(current_price, 2),
            moving_averages=ma_signals,
            ma_score=round(ma_score, 1),
            macd=macd_data,
            rsi=rsi_data,
            support_resistance=sr_data,
            overall_score=round(overall, 1),
            grade=score_to_grade(overall),
            signal=score_to_signal(overall),
        )

    def _compute_moving_averages(self, closes: np.ndarray, price: float, timeframe: str) -> tuple[list[MovingAverageSignal], float]:
        signals = []
        scores = []

        # SMA periods based on timeframe
        if timeframe == "hourly":
            sma_periods = [20, 50]
            ema_periods = [12, 26]
        elif timeframe == "weekly":
            sma_periods = [10, 20, 50]
            ema_periods = [12, 26]
        else:  # daily
            sma_periods = [20, 50, 100, 200]
            ema_periods = [12, 26, 50]

        for period in sma_periods:
            if len(closes) >= period:
                sma = np.mean(closes[-period:])
                signal = "bullish" if price > sma else "bearish"
                score = 70 if price > sma else 30
                signals.append(MovingAverageSignal(
                    period=period, type="SMA", value=round(float(sma), 2), signal=signal
                ))
                scores.append(score)

        for period in ema_periods:
            if len(closes) >= period:
                ema = self._calc_ema(closes, period)
                signal = "bullish" if price > ema else "bearish"
                score = 70 if price > ema else 30
                signals.append(MovingAverageSignal(
                    period=period, type="EMA", value=round(float(ema), 2), signal=signal
                ))
                scores.append(score)

        # Golden/Death cross detection (SMA 50 vs 200 for daily)
        if timeframe == "daily" and len(closes) >= 200:
            sma50 = np.mean(closes[-50:])
            sma200 = np.mean(closes[-200:])
            if sma50 > sma200:
                # Check if recent crossover
                prev_sma50 = np.mean(closes[-55:-5])
                prev_sma200 = np.mean(closes[-205:-5])
                if prev_sma50 <= prev_sma200:
                    scores.append(90)  # Recent golden cross
                else:
                    scores.append(75)
            else:
                prev_sma50 = np.mean(closes[-55:-5])
                prev_sma200 = np.mean(closes[-205:-5])
                if prev_sma50 >= prev_sma200:
                    scores.append(10)  # Recent death cross
                else:
                    scores.append(25)

        ma_score = float(np.mean(scores)) if scores else 50
        return signals, ma_score

    def _compute_macd(self, closes: np.ndarray) -> MACDData:
        if len(closes) < 35:
            return MACDData(score=50)

        ema12 = self._calc_ema_series(closes, 12)
        ema26 = self._calc_ema_series(closes, 26)
        macd_line = ema12 - ema26
        signal_line = self._calc_ema_series(macd_line[~np.isnan(macd_line)], 9)

        # Align arrays
        min_len = min(len(macd_line), len(signal_line))
        macd_line = macd_line[-min_len:]
        signal_line = signal_line[-min_len:]
        histogram = macd_line - signal_line

        current_macd = float(macd_line[-1])
        current_signal = float(signal_line[-1])
        current_hist = float(histogram[-1])

        # Score components
        score = 50

        # MACD above signal = bullish
        if current_macd > current_signal:
            score += 15
        else:
            score -= 15

        # Histogram momentum (growing vs shrinking)
        if len(histogram) >= 3:
            if abs(current_hist) > abs(float(histogram[-2])):
                if current_hist > 0:
                    score += 10  # Growing bullish momentum
                else:
                    score -= 10  # Growing bearish momentum
            else:
                if current_hist > 0:
                    score += 5  # Waning bullish
                else:
                    score -= 5  # Waning bearish

        # Above/below zero
        if current_macd > 0:
            score += 10
        else:
            score -= 10

        # Recent crossover
        crossover = False
        if len(macd_line) >= 3:
            prev_diff = float(macd_line[-2]) - float(signal_line[-2])
            curr_diff = current_macd - current_signal
            if prev_diff <= 0 < curr_diff:
                score += 15
                crossover = True
            elif prev_diff >= 0 > curr_diff:
                score -= 15
                crossover = True

        score = clamp(score)
        signal = "bullish" if score > 55 else ("bearish" if score < 45 else "neutral")

        return MACDData(
            macd_line=round(current_macd, 4),
            signal_line=round(current_signal, 4),
            histogram=round(current_hist, 4),
            signal=signal,
            crossover_recent=crossover,
            score=round(score, 1),
        )

    def _compute_rsi(self, closes: np.ndarray, period: int = 14) -> RSIData:
        if len(closes) < period + 1:
            return RSIData(score=50)

        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])

        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        # Mean-reversion scoring: oversold = buy signal (high score), overbought = sell signal
        if rsi < 20:
            score = 90  # Deeply oversold - strong buy
            signal = "oversold"
        elif rsi < 30:
            score = 80
            signal = "oversold"
        elif rsi < 40:
            score = 65
            signal = "neutral"
        elif rsi < 60:
            score = 50
            signal = "neutral"
        elif rsi < 70:
            score = 35
            signal = "neutral"
        elif rsi < 80:
            score = 20
            signal = "overbought"
        else:
            score = 10  # Deeply overbought - strong sell
            signal = "overbought"

        return RSIData(value=round(rsi, 1), signal=signal, score=round(score, 1))

    def _compute_support_resistance(self, highs: np.ndarray, lows: np.ndarray,
                                     closes: np.ndarray, price: float) -> SupportResistance:
        # Find pivot highs and lows
        support_levels = []
        resistance_levels = []

        window = 5
        for i in range(window, len(lows) - window):
            if lows[i] == min(lows[i - window:i + window + 1]):
                support_levels.append(float(lows[i]))
            if highs[i] == max(highs[i - window:i + window + 1]):
                resistance_levels.append(float(highs[i]))

        # Cluster nearby levels (within 1.5%)
        support_levels = self._cluster_levels(support_levels, price)
        resistance_levels = self._cluster_levels(resistance_levels, price)

        # Filter: supports below price, resistances above
        supports = sorted([s for s in support_levels if s < price], reverse=True)[:3]
        resistances = sorted([r for r in resistance_levels if r > price])[:3]

        nearest_support = supports[0] if supports else None
        nearest_resistance = resistances[0] if resistances else None

        # Score based on proximity and position
        score = 50
        if nearest_support and nearest_resistance:
            range_size = nearest_resistance - nearest_support
            if range_size > 0:
                position = (price - nearest_support) / range_size
                if position < 0.3:
                    score = 75  # Near support - good entry
                elif position > 0.7:
                    score = 30  # Near resistance - risky
                else:
                    score = 50
        elif nearest_support and not nearest_resistance:
            score = 60  # Above all resistance - breakout
        elif nearest_resistance and not nearest_support:
            score = 35  # Below all support - breakdown

        return SupportResistance(
            support_levels=supports,
            resistance_levels=resistances,
            nearest_support=nearest_support,
            nearest_resistance=nearest_resistance,
            score=round(score, 1),
        )

    def _cluster_levels(self, levels: list[float], reference: float, threshold: float = 0.015) -> list[float]:
        if not levels:
            return []
        levels = sorted(levels)
        clusters = []
        current_cluster = [levels[0]]

        for i in range(1, len(levels)):
            if reference > 0 and abs(levels[i] - current_cluster[-1]) / reference < threshold:
                current_cluster.append(levels[i])
            else:
                clusters.append(sum(current_cluster) / len(current_cluster))
                current_cluster = [levels[i]]
        clusters.append(sum(current_cluster) / len(current_cluster))
        return [round(c, 2) for c in clusters]

    def _calc_ema(self, data: np.ndarray, period: int) -> float:
        if len(data) < period:
            return float(np.mean(data))
        multiplier = 2 / (period + 1)
        ema = float(np.mean(data[:period]))
        for i in range(period, len(data)):
            ema = (data[i] - ema) * multiplier + ema
        return ema

    def _calc_ema_series(self, data: np.ndarray, period: int) -> np.ndarray:
        if len(data) < period:
            return data.copy()
        result = np.full_like(data, np.nan, dtype=float)
        result[period - 1] = np.mean(data[:period])
        multiplier = 2 / (period + 1)
        for i in range(period, len(data)):
            result[i] = (data[i] - result[i - 1]) * multiplier + result[i - 1]
        return result
