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


class TechnicalAnalysis(BaseModel):
    ticker: str
    timeframe: str  # hourly, daily, weekly
    current_price: float | None = None
    moving_averages: list[MovingAverageSignal] = []
    ma_score: float = 0
    macd: MACDData = MACDData()
    rsi: RSIData = RSIData()
    support_resistance: SupportResistance = SupportResistance()
    overall_score: float = 0
    grade: str = "N/A"
    signal: str = "HOLD"
