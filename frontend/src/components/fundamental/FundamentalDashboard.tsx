import type { FundamentalAnalysis } from '../../types/stock';
import LetterGrade from '../common/LetterGrade';
import ScoreGauge from '../common/ScoreGauge';
import MetricCard from '../common/MetricCard';
import { formatPercent, formatRatio } from '../../utils/formatting';

interface Props {
  data: FundamentalAnalysis;
}

export default function FundamentalDashboard({ data }: Props) {
  return (
    <div className="space-y-6">
      {/* Overall */}
      <div className="card flex items-center gap-6">
        <ScoreGauge score={data.overall_score} size="md" label="Fundamental" />
        <div>
          <div className="flex items-center gap-2">
            <LetterGrade grade={data.grade} size="md" />
            <span className="text-gray-400 text-sm">
              Confidence: {Math.round(data.confidence * 100)}%
            </span>
          </div>
          {data.data_gaps.length > 0 && (
            <p className="text-xs text-yellow-500 mt-1">
              Missing: {data.data_gaps.join(', ')}
            </p>
          )}
        </div>
      </div>

      {/* Sub-scores grid — 3 pillars */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Valuation */}
        {data.valuation && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-gray-300">Valuation</h3>
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-400">{data.valuation.composite_score.toFixed(0)}/100</span>
                <LetterGrade grade={data.valuation.grade} size="sm" />
              </div>
            </div>
            <MetricCard label="Forward P/E" metric={data.valuation.forward_pe} format={formatRatio} />
            <MetricCard label="EV/EBITDA" metric={data.valuation.ev_ebitda} format={formatRatio} />
            <MetricCard label="PEG Ratio" metric={data.valuation.peg_ratio} format={formatRatio} />
            <MetricCard label="P/B Ratio" metric={data.valuation.pb_ratio} format={formatRatio} />
            <MetricCard label="P/S Ratio" metric={data.valuation.ps_ratio} format={formatRatio} />
          </div>
        )}

        {/* Growth */}
        {data.growth && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-gray-300">Growth</h3>
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-400">{data.growth.composite_score.toFixed(0)}/100</span>
                <LetterGrade grade={data.growth.grade} size="sm" />
              </div>
            </div>
            <MetricCard label="Revenue YoY" metric={data.growth.revenue_yoy} format={(v) => `${v > 0 ? '+' : ''}${v.toFixed(1)}%`} />
            <MetricCard label="Earnings YoY" metric={data.growth.earnings_yoy} format={(v) => `${v > 0 ? '+' : ''}${v.toFixed(1)}%`} />
            <MetricCard label="Revenue QoQ" metric={data.growth.revenue_qoq} format={(v) => `${v > 0 ? '+' : ''}${v.toFixed(1)}%`} />
            <MetricCard label="FCF Growth" metric={data.growth.fcf_growth_qoq} format={(v) => `${v > 0 ? '+' : ''}${v.toFixed(1)}%`} />
            <MetricCard label="Forward Growth Est." metric={data.growth.forward_growth_est} />
          </div>
        )}

        {/* Quality */}
        {data.quality && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-gray-300">Quality</h3>
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-400">{data.quality.composite_score.toFixed(0)}/100</span>
                <LetterGrade grade={data.quality.grade} size="sm" />
              </div>
            </div>
            {data.quality.roe?.value != null ? (
              <>
                <MetricCard label="Return on Equity" metric={data.quality.roe} format={(v) => `${v.toFixed(1)}%`} />
                <MetricCard label="Return on Assets" metric={data.quality.roa} format={(v) => `${v.toFixed(2)}%`} />
                <MetricCard label="Debt/Equity" metric={data.quality.debt_to_equity} format={formatRatio} />
                <MetricCard label="Payout Ratio" metric={data.quality.payout_ratio} format={(v) => `${v.toFixed(0)}%`} />
              </>
            ) : (
              <>
                <MetricCard label="ROIC" metric={data.quality.roic} format={(v) => `${v.toFixed(1)}%`} />
                <MetricCard label="FCF Yield" metric={data.quality.fcf_yield} format={(v) => `${v.toFixed(1)}%`} />
                <MetricCard label="Operating Margin" metric={data.quality.operating_margin} format={(v) => `${v.toFixed(1)}%`} />
                <MetricCard label="Debt/Equity" metric={data.quality.debt_to_equity} format={formatRatio} />
                <MetricCard label="Cash Conversion" metric={data.quality.cash_conversion} format={(v) => `${v.toFixed(2)}x`} />
                <MetricCard label="OCF Trend" metric={data.quality.ocf_trend} />
                <MetricCard label="Current Ratio" metric={data.quality.current_ratio} format={formatRatio} />
                <MetricCard label="Interest Coverage" metric={data.quality.interest_coverage} format={(v) => `${v.toFixed(1)}x`} />
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
