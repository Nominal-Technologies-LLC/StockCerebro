import type { SwingTradeAssessment } from '../../types/stock';
import { formatCurrency } from '../../utils/formatting';

interface Props {
  swing: SwingTradeAssessment;
}

export default function SwingTradeView({ swing }: Props) {
  const ratingColors: Record<string, string> = {
    Strong: 'text-green-400 bg-green-500/20 border-green-500/30',
    Moderate: 'text-yellow-400 bg-yellow-500/20 border-yellow-500/30',
    Weak: 'text-orange-400 bg-orange-500/20 border-orange-500/30',
    None: 'text-gray-400 bg-gray-500/20 border-gray-500/30',
  };

  return (
    <div className="card">
      <h3 className="card-header">Swing Trade Assessment</h3>
      <div className="flex items-center gap-3 mb-4">
        <span className={`px-3 py-1 rounded-full border text-sm font-medium ${ratingColors[swing.opportunity_rating] || ratingColors.None}`}>
          {swing.opportunity_rating} Opportunity
        </span>
        {swing.risk_reward_ratio != null && (
          <span className="text-sm text-gray-400">
            R/R: {swing.risk_reward_ratio.toFixed(1)}:1
          </span>
        )}
      </div>

      {swing.entry_zone.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm mb-4">
          <div>
            <div className="text-gray-500 text-xs uppercase">Entry Zone</div>
            <div className="text-white font-medium">
              {formatCurrency(swing.entry_zone[0])} - {formatCurrency(swing.entry_zone[1])}
            </div>
          </div>
          <div>
            <div className="text-gray-500 text-xs uppercase">Stop Loss</div>
            <div className="text-red-400 font-medium">{formatCurrency(swing.stop_loss)}</div>
          </div>
          <div>
            <div className="text-gray-500 text-xs uppercase">Target</div>
            <div className="text-green-400 font-medium">{formatCurrency(swing.target_price)}</div>
          </div>
          <div>
            <div className="text-gray-500 text-xs uppercase">Risk/Reward</div>
            <div className="text-white font-medium">
              {swing.risk_reward_ratio?.toFixed(1) ?? 'N/A'}:1
            </div>
          </div>
        </div>
      )}

      {swing.reasoning.length > 0 && (
        <ul className="space-y-1">
          {swing.reasoning.map((r, i) => (
            <li key={i} className="text-sm text-gray-400 flex gap-2">
              <span className="text-gray-600">-</span>
              {r}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
