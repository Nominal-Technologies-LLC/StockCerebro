import { getSignalColor } from '../../utils/grading';

interface Props {
  signal: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
}

export default function SignalBadge({ signal, size = 'md' }: Props) {
  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-3 py-1 text-sm',
    lg: 'px-4 py-2 text-base',
    xl: 'px-6 py-3 text-lg font-bold',
  };

  const signalStyles: Record<string, string> = {
    'STRONG BUY': 'text-green-400 bg-gradient-to-br from-green-500/30 to-green-600/15 border-green-500/50 shadow-green-500/15',
    'BUY': 'text-emerald-400 bg-gradient-to-br from-emerald-500/30 to-emerald-600/15 border-emerald-500/50 shadow-emerald-500/15',
    'HOLD': 'text-yellow-400 bg-gradient-to-br from-yellow-500/35 to-yellow-600/15 border-yellow-500/50 shadow-yellow-500/15',
    'SELL': 'text-orange-400 bg-gradient-to-br from-orange-500/35 to-orange-600/15 border-orange-500/50 shadow-orange-500/15',
    'STRONG SELL': 'text-red-400 bg-gradient-to-br from-red-500/35 to-red-600/15 border-red-500/50 shadow-red-500/15',
  };

  const styles = signalStyles[signal] || 'text-gray-400 bg-gradient-to-br from-gray-500/30 to-gray-600/15 border-gray-500/50 shadow-gray-500/15';

  return (
    <span
      className={`
        ${sizeClasses[size]}
        ${styles}
        rounded-full border-2
        shadow-md
        font-semibold uppercase tracking-wide
        transition-all duration-300
        inline-block
      `}
    >
      {signal}
    </span>
  );
}
