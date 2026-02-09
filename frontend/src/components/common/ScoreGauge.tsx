import { getScoreColor } from '../../utils/grading';

interface Props {
  score: number;
  size?: 'sm' | 'md' | 'lg';
  label?: string;
}

export default function ScoreGauge({ score, size = 'md', label }: Props) {
  const color = getScoreColor(score);
  const sizes = {
    sm: { width: 60, stroke: 4, fontSize: 14 },
    md: { width: 90, stroke: 6, fontSize: 20 },
    lg: { width: 130, stroke: 8, fontSize: 28 },
  };
  const { width, stroke, fontSize } = sizes[size];
  const radius = (width - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 100) * circumference;

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width, height: width }}>
        <svg width={width} height={width} className="-rotate-90">
          <circle
            cx={width / 2}
            cy={width / 2}
            r={radius}
            fill="none"
            stroke="#374151"
            strokeWidth={stroke}
          />
          <circle
            cx={width / 2}
            cy={width / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={stroke}
            strokeDasharray={circumference}
            strokeDashoffset={circumference - progress}
            strokeLinecap="round"
            className="transition-all duration-700"
          />
        </svg>
        <span
          className="absolute inset-0 flex items-center justify-center font-bold text-white"
          style={{ fontSize }}
        >
          {Math.round(score)}
        </span>
      </div>
      {label && <span className="text-xs text-gray-400 mt-1">{label}</span>}
    </div>
  );
}
