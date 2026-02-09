import type { Scorecard } from '../../types/stock';
import ScoreGauge from '../common/ScoreGauge';
import SignalBadge from '../common/SignalBadge';
import LetterGrade from '../common/LetterGrade';
import { getScoreColor } from '../../utils/grading';

interface Props {
  scorecard: Scorecard;
}

export default function OverallScorecard({ scorecard }: Props) {
  const bd = scorecard.score_breakdown;

  const breakdownScores = [
    { label: 'Fundamental', value: bd.fundamental_score },
    { label: 'Tech Consensus', value: bd.technical_consensus },
    { label: 'Daily', value: bd.technical_daily_score },
    { label: 'Weekly', value: bd.technical_weekly_score },
  ];

  return (
    <div className="card p-6">
      {/* Hero section: centered gauge + badges */}
      <div className="flex flex-col md:flex-row items-center justify-center gap-8 mb-6">
        <div className="relative">
          <ScoreGauge score={scorecard.overall_score} size="xl" label="Overall" showGlow={true} />
        </div>
        <div className="flex flex-col gap-3 items-center md:items-start">
          <SignalBadge signal={scorecard.signal} size="xl" />
          <div className="flex items-center gap-3">
            <LetterGrade grade={scorecard.grade} size="lg" />
            <span className="text-base text-gray-300">
              Confidence: {Math.round(scorecard.confidence * 100)}%
            </span>
          </div>
          {scorecard.override_applied && (
            <div className="text-xs text-yellow-400">{scorecard.override_reason}</div>
          )}
        </div>
      </div>

      {/* Breakdown scores: horizontal row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 pt-4 border-t border-gray-800">
        {breakdownScores.map((score) => (
          <div
            key={score.label}
            className="text-center p-3 rounded-lg bg-gray-800/50 hover:bg-gray-800 transition-all duration-300 cursor-default"
          >
            <div className="text-xs uppercase text-gray-400 mb-1 font-medium tracking-wide">
              {score.label}
            </div>
            <div
              className="text-2xl font-bold transition-colors duration-300"
              style={{ color: getScoreColor(score.value) }}
            >
              {score.value.toFixed(0)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
