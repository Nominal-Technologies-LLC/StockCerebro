import type { RecentlyViewedItem } from '../../types/stock';
import LetterGrade from '../common/LetterGrade';
import { getSignalColor } from '../../utils/grading';

interface Props {
  items: RecentlyViewedItem[];
  currentTicker: string;
  onSelect: (ticker: string) => void;
}

function timeAgo(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffMs = now - then;
  const mins = Math.floor(diffMs / 60_000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function getSignalAbbrev(signal: string): string {
  switch (signal) {
    case 'STRONG BUY': return 'S.BUY';
    case 'STRONG SELL': return 'S.SELL';
    default: return signal;
  }
}

export default function RecentlyViewedSidebar({ items, currentTicker, onSelect }: Props) {
  if (items.length === 0) return null;

  return (
    <div className="w-full">
      <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3 px-1">
        Recently Viewed
      </h3>
      <div className="space-y-1.5">
        {items.map((item) => {
          const isActive = item.ticker === currentTicker;
          return (
            <button
              key={item.ticker}
              onClick={() => onSelect(item.ticker)}
              className={`
                w-full text-left rounded-lg px-3 py-2.5
                border transition-all duration-200
                ${isActive
                  ? 'bg-brand-500/15 border-brand-500/40 shadow-sm shadow-brand-500/10'
                  : 'bg-gray-900/60 border-gray-800/60 hover:bg-gray-800/80 hover:border-gray-700/60'
                }
              `}
            >
              <div className="flex items-center gap-2.5">
                {/* Grade */}
                {item.grade ? (
                  <LetterGrade grade={item.grade} size="sm" />
                ) : (
                  <div className="w-8 h-8 rounded-lg bg-gray-800 border-2 border-gray-700 flex items-center justify-center text-gray-600 text-xs">
                    --
                  </div>
                )}

                {/* Ticker + Company Name */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={`font-bold text-sm ${isActive ? 'text-brand-400' : 'text-gray-200'}`}>
                      {item.ticker}
                    </span>
                    {item.signal && (
                      <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${getSignalColor(item.signal)}`}>
                        {getSignalAbbrev(item.signal)}
                      </span>
                    )}
                  </div>
                  {item.company_name && (
                    <p className="text-xs text-gray-500 truncate">
                      {item.company_name}
                    </p>
                  )}
                </div>

                {/* Time */}
                <span className="text-[10px] text-gray-600 whitespace-nowrap flex-shrink-0">
                  {timeAgo(item.viewed_at)}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
