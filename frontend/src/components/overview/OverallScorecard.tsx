import type { Scorecard } from '../../types/stock';
import ScoreGauge from '../common/ScoreGauge';
import SignalBadge from '../common/SignalBadge';
import LetterGrade from '../common/LetterGrade';

interface Props {
  scorecard: Scorecard;
}

export default function OverallScorecard({ scorecard }: Props) {
  const bd = scorecard.score_breakdown;

  return (
    <div className="card">
      <div className="flex flex-wrap items-center justify-between gap-6">
        <div className="flex items-center gap-6">
          <ScoreGauge score={scorecard.overall_score} size="lg" label="Overall" />
          <div>
            <SignalBadge signal={scorecard.signal} size="lg" />
            <div className="mt-2 flex items-center gap-2">
              <LetterGrade grade={scorecard.grade} size="md" />
              <span className="text-sm text-gray-400">
                Confidence: {Math.round(scorecard.confidence * 100)}%
              </span>
            </div>
            {scorecard.override_applied && (
              <div className="text-xs text-yellow-400 mt-1">{scorecard.override_reason}</div>
            )}
          </div>
        </div>
        <div className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
          <div>
            <span className="text-gray-500">Fundamental</span>
            <span className="ml-2 font-medium text-white">{bd.fundamental_score.toFixed(0)}</span>
          </div>
          <div>
            <span className="text-gray-500">Tech Consensus</span>
            <span className="ml-2 font-medium text-white">{bd.technical_consensus.toFixed(0)}</span>
          </div>
          <div>
            <span className="text-gray-500">Daily</span>
            <span className="ml-2 font-medium text-gray-300">{bd.technical_daily_score.toFixed(0)}</span>
          </div>
          <div>
            <span className="text-gray-500">Weekly</span>
            <span className="ml-2 font-medium text-gray-300">{bd.technical_weekly_score.toFixed(0)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
