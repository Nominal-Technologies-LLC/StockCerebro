import { getSignalColor } from '../../utils/grading';

interface Props {
  signal: string;
  size?: 'sm' | 'md' | 'lg';
}

export default function SignalBadge({ signal, size = 'md' }: Props) {
  const colors = getSignalColor(signal);
  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-3 py-1 text-sm',
    lg: 'px-4 py-2 text-base',
  };

  return (
    <span className={`${sizeClasses[size]} ${colors} rounded-full border font-semibold inline-block`}>
      {signal}
    </span>
  );
}
