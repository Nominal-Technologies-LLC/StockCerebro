import { useState } from 'react';
import type { EarningsResponse, QuarterlyEarnings } from '../../types/stock';
import { formatLargeNumber } from '../../utils/formatting';

interface Props {
  data: EarningsResponse;
}

function DeltaBadge({ value, label }: { value: number | null; label: string }) {
  if (value == null) return null;
  const isPositive = value > 0;
  const color = isPositive ? 'text-green-400' : value < 0 ? 'text-red-400' : 'text-gray-400';
  return (
    <span className={`text-xs font-medium ${color}`}>
      {isPositive ? '+' : ''}{value.toFixed(1)}% {label}
    </span>
  );
}

function SurpriseBadge({ value }: { value: number | null }) {
  if (value == null) return null;
  const beat = value > 0;
  const miss = value < 0;
  const bg = beat ? 'bg-green-500/15 text-green-400' : miss ? 'bg-red-500/15 text-red-400' : 'bg-gray-500/15 text-gray-400';
  const label = beat ? 'Beat' : miss ? 'Miss' : 'Met';
  return (
    <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${bg}`}>
      {label} {value > 0 ? '+' : ''}{value.toFixed(1)}%
    </span>
  );
}

function QuarterCard({ quarter, defaultExpanded }: { quarter: QuarterlyEarnings; defaultExpanded: boolean }) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  return (
    <div className="card">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between text-left"
      >
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold text-gray-200">{quarter.period_label}</span>
          {quarter.revenue != null && (
            <span className="text-sm text-gray-400">
              Rev: {formatLargeNumber(quarter.revenue)}
            </span>
          )}
          {quarter.eps_surprise_pct != null && (
            <SurpriseBadge value={quarter.eps_surprise_pct} />
          )}
          {quarter.filing_url && (
            <a
              href={quarter.filing_url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1"
            >
              SEC Filing
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
          )}
        </div>
        <div className="flex items-center gap-3">
          <DeltaBadge value={quarter.revenue_yoy} label="YoY" />
          <svg
            className={`w-4 h-4 text-gray-500 transition-transform ${expanded ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {expanded && (
        <div className="mt-4 pt-3 border-t border-gray-800 space-y-3">
          {/* Revenue */}
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500">Revenue</span>
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium text-gray-200">
                {quarter.revenue != null ? formatLargeNumber(quarter.revenue) : 'N/A'}
              </span>
              {quarter.revenue_estimate != null && (
                <span className="text-xs text-gray-500">
                  Est: {formatLargeNumber(quarter.revenue_estimate)}
                </span>
              )}
              {quarter.revenue_surprise_pct != null && (
                <SurpriseBadge value={quarter.revenue_surprise_pct} />
              )}
              <DeltaBadge value={quarter.revenue_qoq} label="QoQ" />
              <DeltaBadge value={quarter.revenue_yoy} label="YoY" />
            </div>
          </div>

          {/* EPS */}
          {(quarter.eps_actual != null || quarter.eps_estimate != null) && (
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500">EPS</span>
              <div className="flex items-center gap-3">
                {quarter.eps_actual != null && (
                  <span className="text-sm font-medium text-gray-200">
                    ${quarter.eps_actual.toFixed(2)}
                  </span>
                )}
                {quarter.eps_estimate != null && (
                  <span className="text-xs text-gray-500">
                    Est: ${quarter.eps_estimate.toFixed(2)}
                  </span>
                )}
                <SurpriseBadge value={quarter.eps_surprise_pct} />
              </div>
            </div>
          )}

          {/* Net Income */}
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500">Net Income</span>
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium text-gray-200">
                {quarter.net_income != null ? formatLargeNumber(quarter.net_income) : 'N/A'}
              </span>
              <DeltaBadge value={quarter.net_income_qoq} label="QoQ" />
              <DeltaBadge value={quarter.net_income_yoy} label="YoY" />
            </div>
          </div>

          {/* Operating Income */}
          {quarter.operating_income != null && (
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500">Operating Income</span>
              <span className="text-sm font-medium text-gray-200">
                {formatLargeNumber(quarter.operating_income)}
              </span>
            </div>
          )}

          {/* Operating Margin */}
          {quarter.operating_margin != null && (
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500">Operating Margin</span>
              <span className="text-sm font-medium text-gray-200">
                {quarter.operating_margin.toFixed(1)}%
              </span>
            </div>
          )}

          {/* Filing Date */}
          {quarter.filing_date && (
            <div className="flex items-center justify-between pt-2 border-t border-gray-800/50">
              <span className="text-xs text-gray-500">Filed</span>
              <span className="text-xs text-gray-400">{quarter.filing_date}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function EarningsDashboard({ data }: Props) {
  if (!data.quarters.length) {
    return (
      <div className="card text-center py-8">
        <p className="text-gray-500">No quarterly earnings data available</p>
      </div>
    );
  }

  const sourceLabel = data.data_source === 'finnhub'
    ? 'Finnhub + SEC EDGAR'
    : data.data_source === 'edgar'
    ? 'SEC EDGAR'
    : data.data_source;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-medium text-gray-300">
          Quarterly Earnings ({data.quarters.length} quarters)
        </h3>
        <span className="text-xs text-gray-600">Source: {sourceLabel}</span>
      </div>
      {data.quarters.map((quarter, i) => (
        <QuarterCard key={quarter.period_end} quarter={quarter} defaultExpanded={i === 0} />
      ))}
    </div>
  );
}
