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

      {/* Sub-scores grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Valuation */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-gray-300">Valuation</h3>
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-400">{data.valuation.composite_score.toFixed(0)}/100</span>
              <LetterGrade grade={data.valuation.grade} size="sm" />
            </div>
          </div>
          <MetricCard label="Forward P/E" metric={data.valuation.forward_pe} format={formatRatio} />
          <MetricCard label="P/E Ratio" metric={data.valuation.pe_ratio} format={formatRatio} />
          <MetricCard label="PEG Ratio" metric={data.valuation.peg_ratio} format={formatRatio} />
          <MetricCard label="P/B Ratio" metric={data.valuation.pb_ratio} format={formatRatio} />
          <MetricCard label="P/S Ratio" metric={data.valuation.ps_ratio} format={formatRatio} />
        </div>

        {/* Growth */}
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
          <MetricCard label="Revenue Trend" metric={data.growth.revenue_trend} />
          <MetricCard label="Analyst Growth Est." metric={data.growth.analyst_growth_est} />
        </div>

        {/* Financial Health */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-gray-300">Financial Health</h3>
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-400">{data.health.composite_score.toFixed(0)}/100</span>
              <LetterGrade grade={data.health.grade} size="sm" />
            </div>
          </div>
          <MetricCard label="Debt/Equity" metric={data.health.debt_to_equity} format={formatRatio} />
          {data.health.roe?.value != null ? (
            <>
              <MetricCard label="Return on Equity" metric={data.health.roe} format={(v) => `${v.toFixed(1)}%`} />
              <MetricCard label="Return on Assets" metric={data.health.roa} format={(v) => `${v.toFixed(2)}%`} />
              <MetricCard label="Payout Ratio" metric={data.health.payout_ratio} format={(v) => `${v.toFixed(0)}%`} />
            </>
          ) : (
            <>
              <MetricCard label="Current Ratio" metric={data.health.current_ratio} format={formatRatio} />
              <MetricCard label="Interest Coverage" metric={data.health.interest_coverage} format={(v) => `${v.toFixed(1)}x`} />
              <MetricCard label="FCF Yield" metric={data.health.fcf_yield} format={(v) => `${v.toFixed(1)}%`} />
              <MetricCard label="OCF Trend" metric={data.health.ocf_trend} />
            </>
          )}
        </div>

        {/* Profitability */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-gray-300">Profitability</h3>
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-400">{data.profitability.composite_score.toFixed(0)}/100</span>
              <LetterGrade grade={data.profitability.grade} size="sm" />
            </div>
          </div>
          <MetricCard label="Gross Margin" metric={data.profitability.gross_margin} format={(v) => `${v.toFixed(1)}%`} />
          <MetricCard label="Operating Margin" metric={data.profitability.operating_margin} format={(v) => `${v.toFixed(1)}%`} />
          <MetricCard label="Net Margin" metric={data.profitability.net_margin} format={(v) => `${v.toFixed(1)}%`} />
          <MetricCard label="Margin Trend" metric={data.profitability.margin_trend} />
        </div>
      </div>
    </div>
  );
}
