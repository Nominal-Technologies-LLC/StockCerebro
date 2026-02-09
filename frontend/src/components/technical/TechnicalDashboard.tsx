import { useState } from 'react';
import type { ChartData, TechnicalAnalysis } from '../../types/stock';
import { useTechnical } from '../../hooks/useStockData';
import { useChartData } from '../../hooks/useChartData';
import PriceChart from './PriceChart';
import IndicatorPanel from './IndicatorPanel';
import TimeframeSelector from './TimeframeSelector';
import ScoreGauge from '../common/ScoreGauge';
import SignalBadge from '../common/SignalBadge';
import LoadingSpinner from '../common/LoadingSpinner';

interface Props {
  ticker: string;
}

const chartParams: Record<string, { period: string; interval: string }> = {
  h: { period: '5d', interval: '1h' },
  d: { period: '6mo', interval: '1d' },
  w: { period: '2y', interval: '1wk' },
};

export default function TechnicalDashboard({ ticker }: Props) {
  const [timeframe, setTimeframe] = useState('d');
  const { period, interval } = chartParams[timeframe];

  const { data: technical, isLoading: techLoading } = useTechnical(ticker, timeframe);
  const { data: chartData, isLoading: chartLoading } = useChartData(ticker, period, interval);

  if (techLoading || chartLoading) {
    return <LoadingSpinner message="Computing technical analysis..." />;
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          {technical && (
            <>
              <ScoreGauge score={technical.overall_score} size="sm" />
              <div>
                <SignalBadge signal={technical.signal} size="sm" />
                <div className="text-xs text-gray-500 mt-1">{technical.timeframe} timeframe</div>
              </div>
            </>
          )}
        </div>
        <TimeframeSelector active={timeframe} onChange={setTimeframe} />
      </div>

      {/* Chart */}
      {chartData && (
        <div className="card p-2">
          <PriceChart chartData={chartData} technical={technical} />
        </div>
      )}

      {/* Indicators */}
      {technical && <IndicatorPanel data={technical} />}
    </div>
  );
}
