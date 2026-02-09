import type { ScoreBreakdown } from '../../types/stock';
import { getScoreColor } from '../../utils/grading';

interface Props {
  breakdown: ScoreBreakdown;
}

export default function ScoreBreakdownView({ breakdown }: Props) {
  const fundPct = Math.round(breakdown.fundamental_weight * 100);
  const techPct = Math.round(breakdown.technical_weight * 100);
  const hasFundamental = fundPct > 0;

  const items = [
    ...(hasFundamental
      ? [{ label: 'Fundamental', score: breakdown.fundamental_score, weight: `${fundPct}%` }]
      : []),
    { label: 'Technical (Daily)', score: breakdown.technical_daily_score, weight: `${Math.round(techPct * 0.50)}%` },
    { label: 'Technical (Weekly)', score: breakdown.technical_weekly_score, weight: `${Math.round(techPct * 0.35)}%` },
    { label: 'Technical (Hourly)', score: breakdown.technical_hourly_score, weight: `${Math.round(techPct * 0.15)}%` },
  ];

  return (
    <div className="card">
      <h3 className="card-header">Score Breakdown</h3>
      {!hasFundamental && (
        <p className="text-xs text-gray-500 mb-3">ETF — Technical analysis only</p>
      )}
      <div className="space-y-3">
        {items.map((item) => (
          <div key={item.label}>
            <div className="flex items-center justify-between text-sm mb-1">
              <span className="text-gray-400">{item.label}</span>
              <div className="flex items-center gap-2">
                <span className="text-gray-500 text-xs">{item.weight}</span>
                <span className="font-medium text-white">{item.score.toFixed(0)}</span>
              </div>
            </div>
            <div className="w-full h-2 bg-gray-800 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${item.score}%`,
                  backgroundColor: getScoreColor(item.score),
                }}
              />
            </div>
          </div>
        ))}
        <div className="border-t border-gray-800 pt-2 mt-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-300 font-medium">Technical Consensus</span>
            <span className="font-bold text-white">{breakdown.technical_consensus.toFixed(0)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
