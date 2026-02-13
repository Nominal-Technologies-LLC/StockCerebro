import type { MetricScore } from '../../types/stock';
import LetterGrade from './LetterGrade';

interface Props {
  label: string;
  metric: MetricScore;
  format?: (v: number) => string;
}

export default function MetricCard({ label, metric, format }: Props) {
  let displayValue: string;

  if (metric.value == null) {
    displayValue = 'N/A';
  } else if (format) {
    try {
      displayValue = format(metric.value);
    } catch (error) {
      console.error(`Error formatting metric "${label}":`, error);
      displayValue = metric.value.toString();
    }
  } else {
    displayValue = metric.value.toFixed(2);
  }

  return (
    <div className="card flex items-center justify-between">
      <div className="flex-1">
        <div className="text-xs text-gray-500 uppercase tracking-wide">{label}</div>
        <div className="text-lg font-semibold text-white mt-0.5">{displayValue}</div>
        {metric.description && (
          <div className="text-xs text-gray-400 mt-0.5">{metric.description}</div>
        )}
      </div>
      <div className="flex items-center gap-2">
        <div className="text-right">
          <div className="text-xs text-gray-500">Score</div>
          <div className="text-sm font-medium text-gray-300">{Math.round(metric.score)}</div>
        </div>
        <LetterGrade grade={metric.grade} size="sm" />
      </div>
    </div>
  );
}
