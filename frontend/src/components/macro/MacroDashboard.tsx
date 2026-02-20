import type { MacroRiskResponse, MacroFactor } from '../../types/stock';

interface Props {
  data: MacroRiskResponse;
}

const impactColors: Record<string, string> = {
  high: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
  medium: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
  low: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
};

const categoryLabels: Record<string, string> = {
  trade: 'Trade',
  rates: 'Rates',
  regulation: 'Regulation',
  technology: 'Technology',
  geopolitical: 'Geopolitical',
  commodity: 'Commodity',
  consumer: 'Consumer',
  labor: 'Labor',
  other: 'Other',
};

function FactorCard({ factor, variant }: { factor: MacroFactor; variant: 'tailwind' | 'headwind' }) {
  const borderColor = variant === 'tailwind' ? 'border-green-500/20' : 'border-red-500/20';
  const accentColor = variant === 'tailwind' ? 'bg-green-500/5' : 'bg-red-500/5';

  return (
    <div className={`card ${borderColor} ${accentColor}`}>
      <div className="flex items-start justify-between gap-3 mb-2">
        <h4 className="text-sm font-semibold text-gray-200">{factor.title}</h4>
        <div className="flex items-center gap-2 shrink-0">
          <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded border ${impactColors[factor.impact] || impactColors.low}`}>
            {factor.impact.toUpperCase()}
          </span>
        </div>
      </div>
      <p className="text-xs text-gray-400 leading-relaxed mb-2">{factor.explanation}</p>
      <span className="text-[10px] text-gray-500 uppercase tracking-wider">
        {categoryLabels[factor.category] || factor.category}
      </span>
    </div>
  );
}

export default function MacroDashboard({ data }: Props) {
  if (data.error) {
    return (
      <div className="card border-yellow-500/30 bg-yellow-500/5 text-center py-8">
        <p className="text-yellow-400 font-medium mb-1">Macro Analysis Unavailable</p>
        <p className="text-gray-500 text-sm">{data.error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Summary */}
      {data.summary && (
        <div className="card">
          <p className="text-sm text-gray-300">{data.summary}</p>
          <div className="flex items-center gap-3 mt-2 text-[10px] text-gray-600">
            {data.analyzed_at && <span>Analyzed: {new Date(data.analyzed_at).toLocaleString()}</span>}
            {data.model_used && <span>Model: {data.model_used}</span>}
          </div>
        </div>
      )}

      {/* Two-column grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Tailwinds */}
        <div>
          <h3 className="text-sm font-medium text-green-400 mb-3 flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
            </svg>
            Tailwinds ({data.tailwinds.length})
          </h3>
          <div className="space-y-3">
            {data.tailwinds.map((f, i) => (
              <FactorCard key={i} factor={f} variant="tailwind" />
            ))}
          </div>
        </div>

        {/* Headwinds */}
        <div>
          <h3 className="text-sm font-medium text-red-400 mb-3 flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
            </svg>
            Headwinds ({data.headwinds.length})
          </h3>
          <div className="space-y-3">
            {data.headwinds.map((f, i) => (
              <FactorCard key={i} factor={f} variant="headwind" />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
