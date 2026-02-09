from pydantic import BaseModel


class MovingAverageSignal(BaseModel):
    period: int
    type: str  # SMA or EMA
    value: float | None = None
    signal: str = "neutral"  # bullish, bearish, neutral


class MACDData(BaseModel):
    macd_line: float | None = None
    signal_line: float | None = None
    histogram: float | None = None
    signal: str = "neutral"
    crossover_recent: bool = False
    score: float = 0


class RSIData(BaseModel):
    value: float | None = None
    signal: str = "neutral"  # oversold, overbought, neutral
    score: float = 0


class SupportResistance(BaseModel):
    support_levels: list[float] = []
    resistance_levels: list[float] = []
    nearest_support: float | None = None
    nearest_resistance: float | None = None
    score: float = 0


class VolumeAnalysis(BaseModel):
    current_volume: int | None = None
    avg_volume_20: int | None = None
    relative_volume: float | None = None
    volume_trend: str = "stable"  # increasing, decreasing, stable
    price_volume_confirmation: str = "neutral"  # bullish, bearish, weak_bullish, weak_bearish, neutral
    obv_trend: str = "flat"  # rising, falling, flat
    score: float = 0


class ChartPattern(BaseModel):
    name: str
    signal: str = "neutral"  # bullish, bearish, neutral
    bias: float = 0  # -1 (bearish) to +1 (bullish)
    description: str = ""


class TechnicalAnalysis(BaseModel):
    ticker: str
    timeframe: str  # hourly, daily, weekly
    current_price: float | None = None
    moving_averages: list[MovingAverageSignal] = []
    ma_score: float = 0
    macd: MACDData = MACDData()
    rsi: RSIData = RSIData()
    support_resistance: SupportResistance = SupportResistance()
    volume_analysis: VolumeAnalysis = VolumeAnalysis()
    patterns: list[ChartPattern] = []
    pattern_score: float = 0
    overall_score: float = 0
    grade: str = "N/A"
    signal: str = "HOLD"
