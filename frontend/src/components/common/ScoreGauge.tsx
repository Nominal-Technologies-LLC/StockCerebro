import { getScoreColor } from '../../utils/grading';

interface Props {
  score: number;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  label?: string;
  showGlow?: boolean;
}

export default function ScoreGauge({ score, size = 'md', label, showGlow = false }: Props) {
  const color = getScoreColor(score);
  const sizes = {
    sm: { width: 60, stroke: 4, fontSize: 14 },
    md: { width: 90, stroke: 6, fontSize: 20 },
    lg: { width: 130, stroke: 8, fontSize: 28 },
    xl: { width: 160, stroke: 10, fontSize: 36 },
  };
  const { width, stroke, fontSize } = sizes[size];
  const radius = (width - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = (score / 100) * circumference;

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width, height: width }}>
        {showGlow && (
          <div
            className="absolute inset-0 rounded-full blur-xl opacity-30 transition-all duration-700"
            style={{ background: color }}
          />
        )}
        <svg width={width} height={width} className="-rotate-90">
          <defs>
            <linearGradient id={`gauge-gradient-${score}`} x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" style={{ stopColor: color, stopOpacity: 1 }} />
              <stop offset="100%" style={{ stopColor: color, stopOpacity: 0.6 }} />
            </linearGradient>
          </defs>
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
            stroke={`url(#gauge-gradient-${score})`}
            strokeWidth={stroke}
            strokeDasharray={circumference}
            strokeDashoffset={circumference - progress}
            strokeLinecap="round"
            className="transition-all duration-700 drop-shadow-lg"
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
