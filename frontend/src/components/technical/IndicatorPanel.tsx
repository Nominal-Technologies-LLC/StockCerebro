import type { TechnicalAnalysis } from '../../types/stock';
import LetterGrade from '../common/LetterGrade';
import SignalBadge from '../common/SignalBadge';

interface Props {
  data: TechnicalAnalysis;
}

export default function IndicatorPanel({ data }: Props) {
  return (
    <div className="space-y-4">
      {/* RSI */}
      <div className="card">
        <h4 className="card-header">RSI (14)</h4>
        <div className="flex items-center justify-between">
          <div>
            <span className="text-2xl font-bold text-white">
              {data.rsi.value?.toFixed(1) ?? 'N/A'}
            </span>
            <span className={`ml-2 text-sm ${
              data.rsi.signal === 'oversold' ? 'text-green-400' :
              data.rsi.signal === 'overbought' ? 'text-red-400' : 'text-gray-400'
            }`}>
              {data.rsi.signal.toUpperCase()}
            </span>
          </div>
          <div className="text-sm text-gray-400">Score: {data.rsi.score.toFixed(0)}</div>
        </div>
        {/* RSI bar */}
        {data.rsi.value != null && (
          <div className="mt-2">
            <div className="w-full h-2 bg-gray-800 rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-green-500 via-yellow-500 to-red-500" />
            </div>
            <div className="relative" style={{ width: '100%' }}>
              <div
                className="absolute -top-1 w-2 h-4 bg-white rounded-sm"
                style={{ left: `${data.rsi.value}%`, transform: 'translateX(-50%)' }}
              />
            </div>
            <div className="flex justify-between text-xs text-gray-600 mt-2">
              <span>Oversold (30)</span>
              <span>Overbought (70)</span>
            </div>
          </div>
        )}
      </div>

      {/* MACD */}
      <div className="card">
        <h4 className="card-header">MACD</h4>
        <div className="grid grid-cols-3 gap-3 text-sm">
          <div>
            <div className="text-gray-500">MACD</div>
            <div className="font-medium text-white">{data.macd.macd_line?.toFixed(4) ?? 'N/A'}</div>
          </div>
          <div>
            <div className="text-gray-500">Signal</div>
            <div className="font-medium text-white">{data.macd.signal_line?.toFixed(4) ?? 'N/A'}</div>
          </div>
          <div>
            <div className="text-gray-500">Histogram</div>
            <div className={`font-medium ${
              (data.macd.histogram ?? 0) >= 0 ? 'text-green-400' : 'text-red-400'
            }`}>
              {data.macd.histogram?.toFixed(4) ?? 'N/A'}
            </div>
          </div>
        </div>
        <div className="mt-2 flex items-center justify-between">
          <span className={`text-sm ${
            data.macd.signal === 'bullish' ? 'text-green-400' :
            data.macd.signal === 'bearish' ? 'text-red-400' : 'text-gray-400'
          }`}>
            {data.macd.signal.toUpperCase()}
            {data.macd.crossover_recent && ' (Recent Crossover)'}
          </span>
          <span className="text-sm text-gray-400">Score: {data.macd.score.toFixed(0)}</span>
        </div>
      </div>

      {/* Moving Averages */}
      <div className="card">
        <h4 className="card-header">Moving Averages (Score: {data.ma_score.toFixed(0)})</h4>
        <div className="space-y-1">
          {data.moving_averages.map((ma) => (
            <div key={`${ma.type}-${ma.period}`} className="flex items-center justify-between text-sm">
              <span className="text-gray-400">{ma.type} {ma.period}</span>
              <div className="flex items-center gap-3">
                <span className="text-white">{ma.value?.toFixed(2)}</span>
                <span className={`text-xs px-2 py-0.5 rounded ${
                  ma.signal === 'bullish' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                }`}>
                  {ma.signal.toUpperCase()}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Support/Resistance */}
      <div className="card">
        <h4 className="card-header">Support & Resistance (Score: {data.support_resistance.score.toFixed(0)})</h4>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <div className="text-green-400 text-xs uppercase mb-1">Support</div>
            {data.support_resistance.support_levels.length > 0 ? (
              data.support_resistance.support_levels.map((s, i) => (
                <div key={i} className="text-white">
                  ${s.toFixed(2)}
                  {i === 0 && <span className="text-xs text-gray-500 ml-1">(nearest)</span>}
                </div>
              ))
            ) : (
              <div className="text-gray-500">None detected</div>
            )}
          </div>
          <div>
            <div className="text-red-400 text-xs uppercase mb-1">Resistance</div>
            {data.support_resistance.resistance_levels.length > 0 ? (
              data.support_resistance.resistance_levels.map((r, i) => (
                <div key={i} className="text-white">
                  ${r.toFixed(2)}
                  {i === 0 && <span className="text-xs text-gray-500 ml-1">(nearest)</span>}
                </div>
              ))
            ) : (
              <div className="text-gray-500">None detected</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
