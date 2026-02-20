"""
Technical analysis engine.
Computes per-timeframe score (0-100):
- Moving Averages (25%): Price vs SMA/EMA, golden/death cross
- MACD (20%): Line vs signal, histogram momentum, zero-line, crossovers
- RSI (15%): Mean-reversion scoring
- Support/Resistance (15%): Proximity, breakout detection
- Volume Analysis (15%): Trend, relative volume, price-volume confirmation
- Chart Patterns (10%): Head & shoulders, double top/bottom, triangles, engulfing
"""
import logging
import math

import numpy as np

from app.analysis.grading import clamp, interpolate, score_to_grade, score_to_signal
from app.schemas.technical import (
    ChartPattern,
    MACDData,
    MovingAverageSignal,
    RSIData,
    SupportResistance,
    TechnicalAnalysis,
    VolumeAnalysis,
)

logger = logging.getLogger(__name__)


class TechnicalAnalyzer:
    def analyze(self, ticker: str, bars: list[dict], timeframe: str) -> TechnicalAnalysis | None:
        if len(bars) < 20:
            return None

        closes = np.array([b["close"] for b in bars], dtype=float)
        highs = np.array([b["high"] for b in bars], dtype=float)
        lows = np.array([b["low"] for b in bars], dtype=float)
        opens = np.array([b["open"] for b in bars], dtype=float)
        volumes = np.array([b["volume"] for b in bars], dtype=float)
        current_price = closes[-1]

        # Moving averages
        ma_signals, ma_score = self._compute_moving_averages(closes, current_price, timeframe)

        # MACD
        macd_data = self._compute_macd(closes)

        # RSI
        rsi_data = self._compute_rsi(closes)

        # Support/Resistance
        sr_data = self._compute_support_resistance(highs, lows, closes, current_price)

        # Volume analysis
        vol_data = self._compute_volume_analysis(closes, volumes)

        # Chart patterns
        patterns, pattern_score = self._detect_patterns(opens, highs, lows, closes, volumes)

        # Overall score (weighted)
        overall = (
            ma_score * 0.25
            + macd_data.score * 0.20
            + rsi_data.score * 0.15
            + sr_data.score * 0.15
            + vol_data.score * 0.15
            + pattern_score * 0.10
        )

        return TechnicalAnalysis(
            ticker=ticker,
            timeframe=timeframe,
            current_price=round(current_price, 2),
            moving_averages=ma_signals,
            ma_score=round(ma_score, 1),
            macd=macd_data,
            rsi=rsi_data,
            support_resistance=sr_data,
            volume_analysis=vol_data,
            patterns=patterns,
            pattern_score=round(pattern_score, 1),
            overall_score=round(overall, 1),
            grade=score_to_grade(overall),
            signal=score_to_signal(overall),
        )

    # ── Moving Averages ─────────────────────────────────────────────

    def _compute_moving_averages(self, closes: np.ndarray, price: float, timeframe: str) -> tuple[list[MovingAverageSignal], float]:
        signals = []
        scores = []

        # SMA periods based on timeframe
        if timeframe == "hourly":
            sma_periods = [20, 50, 120, 200]
            ema_periods = [12, 26]
        elif timeframe == "weekly":
            sma_periods = [10, 20, 50, 120, 200]
            ema_periods = [12, 26]
        else:  # daily
            sma_periods = [20, 50, 100, 120, 200]
            ema_periods = [12, 26, 50]

        for period in sma_periods:
            if len(closes) >= period:
                sma = float(np.mean(closes[-period:]))
                pct_diff = ((price - sma) / sma) * 100 if sma != 0 else 0
                signal = "bullish" if price > sma else "bearish"
                score = interpolate(pct_diff, [
                    (-15, 10), (-8, 25), (-3, 40), (0, 50),
                    (3, 60), (8, 75), (15, 90),
                ])
                signals.append(MovingAverageSignal(
                    period=period, type="SMA", value=round(sma, 2), signal=signal
                ))
                scores.append(score)

        for period in ema_periods:
            if len(closes) >= period:
                ema = self._calc_ema(closes, period)
                pct_diff = ((price - ema) / ema) * 100 if ema != 0 else 0
                signal = "bullish" if price > ema else "bearish"
                score = interpolate(pct_diff, [
                    (-15, 10), (-8, 25), (-3, 40), (0, 50),
                    (3, 60), (8, 75), (15, 90),
                ])
                signals.append(MovingAverageSignal(
                    period=period, type="EMA", value=round(float(ema), 2), signal=signal
                ))
                scores.append(score)

        # Golden/Death cross detection (SMA 50 vs 200)
        if len(closes) >= 200:
            sma50 = np.mean(closes[-50:])
            sma200 = np.mean(closes[-200:])
            if sma50 > sma200:
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

    # ── MACD ────────────────────────────────────────────────────────

    def _compute_macd(self, closes: np.ndarray) -> MACDData:
        if len(closes) < 35:
            return MACDData(score=50)

        ema12 = self._calc_ema_series(closes, 12)
        ema26 = self._calc_ema_series(closes, 26)
        macd_line = ema12 - ema26
        signal_line = self._calc_ema_series(macd_line[~np.isnan(macd_line)], 9)

        min_len = min(len(macd_line), len(signal_line))
        macd_line = macd_line[-min_len:]
        signal_line = signal_line[-min_len:]
        histogram = macd_line - signal_line

        current_macd = float(macd_line[-1])
        current_signal = float(signal_line[-1])
        current_hist = float(histogram[-1])

        score = 50
        if current_macd > current_signal:
            score += 15
        else:
            score -= 15

        if len(histogram) >= 3:
            if abs(current_hist) > abs(float(histogram[-2])):
                score += 10 if current_hist > 0 else -10
            else:
                score += 5 if current_hist > 0 else -5

        if current_macd > 0:
            score += 10
        else:
            score -= 10

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

    # ── RSI ─────────────────────────────────────────────────────────

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

        # Determine trend from SMA50 for trend-aware RSI scoring
        price = float(closes[-1])
        in_uptrend = None
        if len(closes) >= 50:
            sma50 = float(np.mean(closes[-50:]))
            in_uptrend = price > sma50

        if rsi < 30:
            score = 85 if in_uptrend else 80
            signal = "oversold"
        elif rsi < 40:
            score = 70 if in_uptrend else 60
            signal = "neutral"
        elif rsi < 60:
            score = 55 if in_uptrend else 45
            signal = "neutral"
        elif rsi < 70:
            score = 45 if in_uptrend else 30
            signal = "neutral"
        elif rsi < 80:
            score = 35 if in_uptrend else 15
            signal = "overbought"
        else:
            score = 20 if in_uptrend else 5
            signal = "overbought"

        return RSIData(value=round(rsi, 1), signal=signal, score=round(score, 1))

    # ── Support / Resistance ────────────────────────────────────────

    def _compute_support_resistance(self, highs: np.ndarray, lows: np.ndarray,
                                     closes: np.ndarray, price: float) -> SupportResistance:
        support_levels = []
        resistance_levels = []

        window = 5
        for i in range(window, len(lows) - window):
            if lows[i] == min(lows[i - window:i + window + 1]):
                support_levels.append(float(lows[i]))
            if highs[i] == max(highs[i - window:i + window + 1]):
                resistance_levels.append(float(highs[i]))

        support_levels = self._cluster_levels(support_levels, price)
        resistance_levels = self._cluster_levels(resistance_levels, price)

        supports = sorted([s for s in support_levels if s < price], reverse=True)[:3]
        resistances = sorted([r for r in resistance_levels if r > price])[:3]

        nearest_support = supports[0] if supports else None
        nearest_resistance = resistances[0] if resistances else None

        score = 50
        if nearest_support and nearest_resistance:
            range_size = nearest_resistance - nearest_support
            if range_size > 0:
                position = (price - nearest_support) / range_size
                if position < 0.3:
                    score = 75
                elif position > 0.7:
                    score = 30
                else:
                    score = 50
        elif nearest_support and not nearest_resistance:
            score = 60
        elif nearest_resistance and not nearest_support:
            score = 35

        return SupportResistance(
            support_levels=supports,
            resistance_levels=resistances,
            nearest_support=nearest_support,
            nearest_resistance=nearest_resistance,
            score=round(score, 1),
        )

    # ── Volume Analysis ─────────────────────────────────────────────

    def _compute_volume_analysis(self, closes: np.ndarray, volumes: np.ndarray) -> VolumeAnalysis:
        if len(volumes) < 20 or np.sum(volumes) == 0:
            return VolumeAnalysis(score=50)

        current_vol = float(volumes[-1])
        avg_vol_20 = float(np.mean(volumes[-20:]))
        avg_vol_5 = float(np.mean(volumes[-5:])) if len(volumes) >= 5 else current_vol

        # Relative volume (current vs 20-day avg)
        rel_vol = current_vol / avg_vol_20 if avg_vol_20 > 0 else 1.0

        # Volume trend: compare recent 5-bar avg to 20-bar avg
        vol_trend = "increasing" if avg_vol_5 > avg_vol_20 * 1.1 else (
            "decreasing" if avg_vol_5 < avg_vol_20 * 0.9 else "stable"
        )

        # Price-volume confirmation
        # Recent price direction
        price_change_5 = (closes[-1] - closes[-6]) / closes[-6] if len(closes) >= 6 else 0
        pv_confirm = "neutral"
        if price_change_5 > 0.01 and avg_vol_5 > avg_vol_20:
            pv_confirm = "bullish"  # Price up on increasing volume
        elif price_change_5 < -0.01 and avg_vol_5 > avg_vol_20:
            pv_confirm = "bearish"  # Price down on increasing volume
        elif price_change_5 > 0.01 and avg_vol_5 < avg_vol_20:
            pv_confirm = "weak_bullish"  # Price up but low volume — weak rally
        elif price_change_5 < -0.01 and avg_vol_5 < avg_vol_20:
            pv_confirm = "weak_bearish"  # Price down on low volume — selling exhaustion

        # OBV trend (simplified: direction of OBV over last 20 bars)
        obv = np.zeros(len(closes))
        for i in range(1, len(closes)):
            if closes[i] > closes[i - 1]:
                obv[i] = obv[i - 1] + volumes[i]
            elif closes[i] < closes[i - 1]:
                obv[i] = obv[i - 1] - volumes[i]
            else:
                obv[i] = obv[i - 1]

        obv_recent = obv[-20:]
        obv_slope = (obv_recent[-1] - obv_recent[0]) / max(abs(obv_recent[0]), 1)
        obv_trend = "rising" if obv_slope > 0.05 else ("falling" if obv_slope < -0.05 else "flat")

        # Scoring
        score = 50

        # Relative volume: high volume during uptrend = bullish confirmation
        if rel_vol > 1.5 and price_change_5 > 0:
            score += 15
        elif rel_vol > 1.5 and price_change_5 < 0:
            score -= 15
        elif rel_vol > 1.1 and price_change_5 > 0:
            score += 8
        elif rel_vol > 1.1 and price_change_5 < 0:
            score -= 8

        # Price-volume confirmation
        if pv_confirm == "bullish":
            score += 12
        elif pv_confirm == "bearish":
            score -= 12
        elif pv_confirm == "weak_bullish":
            score += 3
        elif pv_confirm == "weak_bearish":
            score += 5  # Selling exhaustion can be slightly bullish

        # OBV trend
        if obv_trend == "rising":
            score += 8
        elif obv_trend == "falling":
            score -= 8

        score = clamp(score)

        return VolumeAnalysis(
            current_volume=int(current_vol),
            avg_volume_20=int(avg_vol_20),
            relative_volume=round(rel_vol, 2),
            volume_trend=vol_trend,
            price_volume_confirmation=pv_confirm,
            obv_trend=obv_trend,
            score=round(score, 1),
        )

    # ── Chart Pattern Detection ─────────────────────────────────────

    def _detect_patterns(self, opens: np.ndarray, highs: np.ndarray,
                         lows: np.ndarray, closes: np.ndarray,
                         volumes: np.ndarray) -> tuple[list[ChartPattern], float]:
        patterns: list[ChartPattern] = []

        # Only run pattern detection if we have enough bars
        if len(closes) >= 30:
            self._detect_double_top_bottom(highs, lows, closes, patterns)
        if len(closes) >= 40:
            self._detect_head_and_shoulders(highs, lows, closes, patterns)
        if len(closes) >= 20:
            self._detect_triangles(highs, lows, closes, patterns)
        if len(closes) >= 3:
            self._detect_candlestick_patterns(opens, highs, lows, closes, volumes, patterns)

        if not patterns:
            return patterns, 50.0

        # Score: average the bias of detected patterns
        # Each pattern has a bias (-1 to +1), we scale to 0-100
        biases = [p.bias for p in patterns]
        avg_bias = sum(biases) / len(biases)
        score = 50 + avg_bias * 30  # range: roughly 20-80
        score = clamp(score)

        return patterns, score

    def _detect_double_top_bottom(self, highs: np.ndarray, lows: np.ndarray,
                                   closes: np.ndarray, patterns: list[ChartPattern]):
        """Detect double top / double bottom in last 60 bars."""
        n = min(len(highs), 60)
        h = highs[-n:]
        l = lows[-n:]
        c = closes[-n:]
        price = c[-1]

        # Find pivot highs/lows
        window = 5
        pivot_highs = []
        pivot_lows = []
        for i in range(window, n - window):
            if h[i] == max(h[i - window:i + window + 1]):
                pivot_highs.append((i, float(h[i])))
            if l[i] == min(l[i - window:i + window + 1]):
                pivot_lows.append((i, float(l[i])))

        # Double top: two highs at similar level, price now below both
        for i in range(len(pivot_highs)):
            for j in range(i + 1, len(pivot_highs)):
                idx_a, val_a = pivot_highs[i]
                idx_b, val_b = pivot_highs[j]
                if abs(idx_b - idx_a) < 8:
                    continue  # Too close
                avg_peak = (val_a + val_b) / 2
                if avg_peak == 0:
                    continue
                if abs(val_a - val_b) / avg_peak < 0.03 and price < avg_peak * 0.97:
                    patterns.append(ChartPattern(
                        name="Double Top",
                        signal="bearish",
                        bias=-0.6,
                        description=f"Two peaks near ${avg_peak:.2f}, price broke below",
                    ))
                    return  # One is enough

        # Double bottom: two lows at similar level, price now above both
        for i in range(len(pivot_lows)):
            for j in range(i + 1, len(pivot_lows)):
                idx_a, val_a = pivot_lows[i]
                idx_b, val_b = pivot_lows[j]
                if abs(idx_b - idx_a) < 8:
                    continue
                avg_trough = (val_a + val_b) / 2
                if avg_trough == 0:
                    continue
                if abs(val_a - val_b) / avg_trough < 0.03 and price > avg_trough * 1.03:
                    patterns.append(ChartPattern(
                        name="Double Bottom",
                        signal="bullish",
                        bias=0.6,
                        description=f"Two troughs near ${avg_trough:.2f}, price broke above",
                    ))
                    return

    def _detect_head_and_shoulders(self, highs: np.ndarray, lows: np.ndarray,
                                    closes: np.ndarray, patterns: list[ChartPattern]):
        """Detect head & shoulders or inverse H&S in last 80 bars."""
        n = min(len(highs), 80)
        h = highs[-n:]
        l = lows[-n:]
        c = closes[-n:]
        price = c[-1]

        window = 5
        pivot_highs = []
        pivot_lows = []
        for i in range(window, n - window):
            if h[i] == max(h[i - window:i + window + 1]):
                pivot_highs.append((i, float(h[i])))
            if l[i] == min(l[i - window:i + window + 1]):
                pivot_lows.append((i, float(l[i])))

        # Head & Shoulders: three highs where middle is highest
        if len(pivot_highs) >= 3:
            for i in range(len(pivot_highs) - 2):
                _, left = pivot_highs[i]
                _, head = pivot_highs[i + 1]
                _, right = pivot_highs[i + 2]
                if head == 0 or left == 0:
                    continue
                # Head must be higher than both shoulders
                if head > left and head > right:
                    # Shoulders should be roughly similar (within 5%)
                    avg_shoulder = (left + right) / 2
                    if avg_shoulder > 0 and abs(left - right) / avg_shoulder < 0.05:
                        # Price should be near or below neckline
                        if price < avg_shoulder:
                            patterns.append(ChartPattern(
                                name="Head & Shoulders",
                                signal="bearish",
                                bias=-0.7,
                                description=f"Head at ${head:.2f}, shoulders near ${avg_shoulder:.2f}",
                            ))
                            break

        # Inverse H&S: three lows where middle is lowest
        if len(pivot_lows) >= 3:
            for i in range(len(pivot_lows) - 2):
                _, left = pivot_lows[i]
                _, head = pivot_lows[i + 1]
                _, right = pivot_lows[i + 2]
                if head == 0 or left == 0:
                    continue
                if head < left and head < right:
                    avg_shoulder = (left + right) / 2
                    if avg_shoulder > 0 and abs(left - right) / avg_shoulder < 0.05:
                        if price > avg_shoulder:
                            patterns.append(ChartPattern(
                                name="Inverse Head & Shoulders",
                                signal="bullish",
                                bias=0.7,
                                description=f"Head at ${head:.2f}, shoulders near ${avg_shoulder:.2f}",
                            ))
                            break

    def _detect_triangles(self, highs: np.ndarray, lows: np.ndarray,
                          closes: np.ndarray, patterns: list[ChartPattern]):
        """Detect ascending/descending triangles in last 40 bars."""
        n = min(len(highs), 40)
        h = highs[-n:]
        l = lows[-n:]

        # Use linear regression on recent highs and lows to find converging trendlines
        x = np.arange(n, dtype=float)
        if n < 10:
            return

        # Fit lines to the upper (highs) and lower (lows) boundaries
        high_slope = np.polyfit(x, h, 1)[0]
        low_slope = np.polyfit(x, l, 1)[0]

        # Ascending triangle: flat top (resistance), rising lows
        if abs(high_slope) < 0.05 * np.mean(h) / n and low_slope > 0.02 * np.mean(l) / n:
            patterns.append(ChartPattern(
                name="Ascending Triangle",
                signal="bullish",
                bias=0.5,
                description="Flat resistance with rising support — bullish continuation",
            ))
            return

        # Descending triangle: flat bottom (support), falling highs
        if abs(low_slope) < 0.05 * np.mean(l) / n and high_slope < -0.02 * np.mean(h) / n:
            patterns.append(ChartPattern(
                name="Descending Triangle",
                signal="bearish",
                bias=-0.5,
                description="Flat support with falling resistance — bearish continuation",
            ))
            return

        # Symmetrical triangle: converging trendlines
        if high_slope < -0.01 * np.mean(h) / n and low_slope > 0.01 * np.mean(l) / n:
            patterns.append(ChartPattern(
                name="Symmetrical Triangle",
                signal="neutral",
                bias=0.0,
                description="Converging trendlines — breakout direction uncertain",
            ))

    def _detect_candlestick_patterns(self, opens: np.ndarray, highs: np.ndarray,
                                      lows: np.ndarray, closes: np.ndarray,
                                      volumes: np.ndarray, patterns: list[ChartPattern]):
        """Detect recent candlestick patterns (last 3 bars)."""
        if len(closes) < 3:
            return

        o1, h1, l1, c1 = opens[-2], highs[-2], lows[-2], closes[-2]
        o2, h2, l2, c2 = opens[-1], highs[-1], lows[-1], closes[-1]
        body1 = abs(c1 - o1)
        body2 = abs(c2 - o2)
        avg_body = np.mean(np.abs(closes[-20:] - opens[-20:])) if len(closes) >= 20 else body1

        if avg_body == 0:
            return

        # Bullish Engulfing: bearish candle followed by larger bullish candle
        if c1 < o1 and c2 > o2 and body2 > body1 * 1.2 and o2 <= c1 and c2 >= o1:
            patterns.append(ChartPattern(
                name="Bullish Engulfing",
                signal="bullish",
                bias=0.5,
                description="Bullish reversal — buyers overwhelmed sellers",
            ))

        # Bearish Engulfing
        elif c1 > o1 and c2 < o2 and body2 > body1 * 1.2 and o2 >= c1 and c2 <= o1:
            patterns.append(ChartPattern(
                name="Bearish Engulfing",
                signal="bearish",
                bias=-0.5,
                description="Bearish reversal — sellers overwhelmed buyers",
            ))

        # Hammer (bullish reversal at bottom): small body at top, long lower shadow
        lower_shadow2 = min(o2, c2) - l2
        upper_shadow2 = h2 - max(o2, c2)
        if body2 > 0 and lower_shadow2 > body2 * 2 and upper_shadow2 < body2 * 0.5:
            # Check if in a downtrend (price below 10-bar avg)
            if len(closes) >= 10 and c2 < np.mean(closes[-10:]):
                patterns.append(ChartPattern(
                    name="Hammer",
                    signal="bullish",
                    bias=0.4,
                    description="Potential bullish reversal — rejection of lower prices",
                ))

        # Shooting Star (bearish reversal at top): small body at bottom, long upper shadow
        if body2 > 0 and upper_shadow2 > body2 * 2 and lower_shadow2 < body2 * 0.5:
            if len(closes) >= 10 and c2 > np.mean(closes[-10:]):
                patterns.append(ChartPattern(
                    name="Shooting Star",
                    signal="bearish",
                    bias=-0.4,
                    description="Potential bearish reversal — rejection of higher prices",
                ))

        # Doji: very small body relative to average
        if body2 < avg_body * 0.1 and (h2 - l2) > avg_body * 0.5:
            patterns.append(ChartPattern(
                name="Doji",
                signal="neutral",
                bias=0.0,
                description="Indecision — potential trend reversal",
            ))

    # ── Helpers ──────────────────────────────────────────────────────

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
