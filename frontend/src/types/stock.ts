export interface CompanyOverview {
  ticker: string;
  name: string | null;
  sector: string | null;
  industry: string | null;
  is_etf: boolean;
  market_cap: number | null;
  price: number | null;
  change: number | null;
  change_percent: number | null;
  volume: number | null;
  avg_volume: number | null;
  day_high: number | null;
  day_low: number | null;
  fifty_two_week_high: number | null;
  fifty_two_week_low: number | null;
  pe_ratio: number | null;
  forward_pe: number | null;
  dividend_yield: number | null;
  beta: number | null;
  description: string | null;
  website: string | null;
  logo_url: string | null;
}

export interface OHLCVBar {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface ChartData {
  ticker: string;
  period: string;
  interval: string;
  bars: OHLCVBar[];
}

export interface MetricScore {
  value: number | null;
  score: number;
  grade: string;
  description: string;
}

export interface ValuationMetrics {
  forward_pe: MetricScore;
  ev_ebitda: MetricScore;
  peg_ratio: MetricScore;
  pb_ratio: MetricScore;
  ps_ratio: MetricScore;
  composite_score: number;
  grade: string;
}

export interface GrowthMetrics {
  revenue_yoy: MetricScore;
  earnings_yoy: MetricScore;
  revenue_qoq: MetricScore;
  earnings_qoq: MetricScore;
  forward_growth_est: MetricScore;
  composite_score: number;
  grade: string;
}

export interface QualityMetrics {
  // Standard metrics (non-financial companies)
  roic: MetricScore;
  fcf_yield: MetricScore;
  operating_margin: MetricScore;
  debt_to_equity: MetricScore;
  margin_trend: MetricScore;
  ocf_trend: MetricScore;
  // Bank/financial metrics
  roe: MetricScore;
  roa: MetricScore;
  payout_ratio: MetricScore;
  composite_score: number;
  grade: string;
}

export interface FundamentalAnalysis {
  ticker: string;
  valuation: ValuationMetrics;
  growth: GrowthMetrics;
  quality: QualityMetrics;
  overall_score: number;
  grade: string;
  confidence: number;
  data_gaps: string[];
}

export interface MovingAverageSignal {
  period: number;
  type: string;
  value: number | null;
  signal: string;
}

export interface MACDData {
  macd_line: number | null;
  signal_line: number | null;
  histogram: number | null;
  signal: string;
  crossover_recent: boolean;
  score: number;
}

export interface RSIData {
  value: number | null;
  signal: string;
  score: number;
}

export interface SupportResistance {
  support_levels: number[];
  resistance_levels: number[];
  nearest_support: number | null;
  nearest_resistance: number | null;
  score: number;
}

export interface VolumeAnalysis {
  current_volume: number | null;
  avg_volume_20: number | null;
  relative_volume: number | null;
  volume_trend: string;
  price_volume_confirmation: string;
  obv_trend: string;
  score: number;
}

export interface ChartPattern {
  name: string;
  signal: string;
  bias: number;
  description: string;
}

export interface TechnicalAnalysis {
  ticker: string;
  timeframe: string;
  current_price: number | null;
  moving_averages: MovingAverageSignal[];
  ma_score: number;
  macd: MACDData;
  rsi: RSIData;
  support_resistance: SupportResistance;
  volume_analysis: VolumeAnalysis;
  patterns: ChartPattern[];
  pattern_score: number;
  overall_score: number;
  grade: string;
  signal: string;
}

export interface SwingTradeAssessment {
  opportunity_rating: string;
  entry_zone: number[];
  stop_loss: number | null;
  target_price: number | null;
  risk_reward_ratio: number | null;
  reasoning: string[];
}

export interface ScoreBreakdown {
  fundamental_score: number;
  fundamental_weight: number;
  technical_daily_score: number;
  technical_weekly_score: number;
  technical_hourly_score: number;
  technical_consensus: number;
  technical_weight: number;
}

export interface NewsArticle {
  title: string;
  url: string;
  source: string;
  published: string;
  summary: string;
}

export interface QuarterlyEarnings {
  period_end: string;
  period_label: string;
  revenue: number | null;
  net_income: number | null;
  operating_income: number | null;
  operating_margin: number | null;
  revenue_qoq: number | null;
  net_income_qoq: number | null;
  revenue_yoy: number | null;
  net_income_yoy: number | null;
  filing_url: string | null;
  filing_date: string | null;
}

export interface EarningsResponse {
  ticker: string;
  quarters: QuarterlyEarnings[];
  data_source: string;
}

export interface Scorecard {
  ticker: string;
  overall_score: number;
  grade: string;
  signal: string;
  score_breakdown: ScoreBreakdown;
  fundamental: FundamentalAnalysis | null;
  technical_daily: TechnicalAnalysis | null;
  swing_trade: SwingTradeAssessment;
  confidence: number;
  override_applied: boolean;
  override_reason: string;
}
