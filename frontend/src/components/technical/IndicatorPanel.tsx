import type { TechnicalAnalysis } from '../../types/stock';

interface Props {
  data: TechnicalAnalysis;
}

function formatVolume(v: number | null): string {
  if (v == null) return 'N/A';
  if (v >= 1_000_000_000) return `${(v / 1_000_000_000).toFixed(1)}B`;
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(1)}K`;
  return v.toString();
}

function confirmLabel(c: string): string {
  switch (c) {
    case 'bullish': return 'Bullish';
    case 'bearish': return 'Bearish';
    case 'weak_bullish': return 'Weak Bullish';
    case 'weak_bearish': return 'Weak Bearish';
    default: return 'Neutral';
  }
}

function confirmColor(c: string): string {
  if (c.includes('bullish')) return 'text-green-400';
  if (c.includes('bearish')) return 'text-red-400';
  return 'text-gray-400';
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

      {/* Volume Analysis */}
      {data.volume_analysis && (
        <div className="card">
          <h4 className="card-header">Volume Analysis (Score: {data.volume_analysis.score.toFixed(0)})</h4>
          <div className="grid grid-cols-3 gap-3 text-sm">
            <div>
              <div className="text-gray-500">Current</div>
              <div className="font-medium text-white">{formatVolume(data.volume_analysis.current_volume)}</div>
            </div>
            <div>
              <div className="text-gray-500">20-Avg</div>
              <div className="font-medium text-white">{formatVolume(data.volume_analysis.avg_volume_20)}</div>
            </div>
            <div>
              <div className="text-gray-500">Relative</div>
              <div className={`font-medium ${
                (data.volume_analysis.relative_volume ?? 1) > 1.2 ? 'text-yellow-400' :
                (data.volume_analysis.relative_volume ?? 1) < 0.8 ? 'text-gray-500' : 'text-white'
              }`}>
                {data.volume_analysis.relative_volume?.toFixed(2) ?? 'N/A'}x
              </div>
            </div>
          </div>
          <div className="mt-2 grid grid-cols-3 gap-3 text-sm">
            <div>
              <div className="text-gray-500">Trend</div>
              <div className={`font-medium ${
                data.volume_analysis.volume_trend === 'increasing' ? 'text-yellow-400' :
                data.volume_analysis.volume_trend === 'decreasing' ? 'text-gray-500' : 'text-white'
              }`}>
                {data.volume_analysis.volume_trend.charAt(0).toUpperCase() + data.volume_analysis.volume_trend.slice(1)}
              </div>
            </div>
            <div>
              <div className="text-gray-500">Price-Vol</div>
              <div className={`font-medium ${confirmColor(data.volume_analysis.price_volume_confirmation)}`}>
                {confirmLabel(data.volume_analysis.price_volume_confirmation)}
              </div>
            </div>
            <div>
              <div className="text-gray-500">OBV</div>
              <div className={`font-medium ${
                data.volume_analysis.obv_trend === 'rising' ? 'text-green-400' :
                data.volume_analysis.obv_trend === 'falling' ? 'text-red-400' : 'text-gray-400'
              }`}>
                {data.volume_analysis.obv_trend.charAt(0).toUpperCase() + data.volume_analysis.obv_trend.slice(1)}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Chart Patterns */}
      {data.patterns && data.patterns.length > 0 && (
        <div className="card">
          <h4 className="card-header">Chart Patterns (Score: {data.pattern_score.toFixed(0)})</h4>
          <div className="space-y-2">
            {data.patterns.map((p, i) => (
              <div key={i} className="flex items-start justify-between text-sm">
                <div className="flex-1">
                  <span className="font-medium text-white">{p.name}</span>
                  <p className="text-xs text-gray-500 mt-0.5">{p.description}</p>
                </div>
                <span className={`ml-3 text-xs px-2 py-0.5 rounded whitespace-nowrap ${
                  p.signal === 'bullish' ? 'bg-green-500/20 text-green-400' :
                  p.signal === 'bearish' ? 'bg-red-500/20 text-red-400' :
                  'bg-gray-500/20 text-gray-400'
                }`}>
                  {p.signal.toUpperCase()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

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
