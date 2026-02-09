import type { Scorecard } from '../../types/stock';
import OverallScorecard from '../overview/OverallScorecard';
import ScoreBreakdownView from './ScoreBreakdownView';
import SwingTradeView from './SwingTradeView';
import FundamentalDashboard from '../fundamental/FundamentalDashboard';

interface Props {
  data: Scorecard;
}

export default function ScorecardDashboard({ data }: Props) {
  return (
    <div className="space-y-6">
      <OverallScorecard scorecard={data} />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ScoreBreakdownView breakdown={data.score_breakdown} />
        <SwingTradeView swing={data.swing_trade} />
      </div>
      {data.fundamental && (
        <div>
          <h3 className="text-lg font-medium text-gray-300 mb-3">Fundamental Detail</h3>
          <FundamentalDashboard data={data.fundamental} />
        </div>
      )}
    </div>
  );
}
