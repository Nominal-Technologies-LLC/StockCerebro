import { useEffect, useRef, useMemo } from 'react';
import { createChart, ColorType, type IChartApi } from 'lightweight-charts';
import type { ChartData, TechnicalAnalysis } from '../../types/stock';

interface Props {
  chartData: ChartData;
  technical?: TechnicalAnalysis | null;
}

export default function PriceChart({ chartData, technical }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  const isIntraday = useMemo(() => {
    const iv = chartData.interval;
    return iv.includes('h') || iv.includes('m');
  }, [chartData.interval]);

  useEffect(() => {
    if (!containerRef.current || chartData.bars.length === 0) return;

    // Clean up previous chart
    if (chartRef.current) {
      chartRef.current.remove();
    }

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#111827' },
        textColor: '#9CA3AF',
      },
      grid: {
        vertLines: { color: '#1F2937' },
        horzLines: { color: '#1F2937' },
      },
      width: containerRef.current.clientWidth,
      height: 400,
      crosshair: {
        mode: 0,
      },
      timeScale: {
        borderColor: '#374151',
        timeVisible: isIntraday,
        secondsVisible: false,
      },
      rightPriceScale: {
        borderColor: '#374151',
      },
    });
    chartRef.current = chart;

    // Candlestick series
    const candlestickData = chartData.bars.map((bar) => {
      const time = parseTime(bar.time, isIntraday);
      return { time, open: bar.open, high: bar.high, low: bar.low, close: bar.close };
    });

    const candleSeries = chart.addCandlestickSeries({
      upColor: '#22c55e',
      downColor: '#ef4444',
      borderDownColor: '#ef4444',
      borderUpColor: '#22c55e',
      wickDownColor: '#ef4444',
      wickUpColor: '#22c55e',
    });
    candleSeries.setData(candlestickData as any);

    // Volume
    const volumeData = chartData.bars.map((bar) => ({
      time: parseTime(bar.time, isIntraday),
      value: bar.volume,
      color: bar.close >= bar.open ? 'rgba(34,197,94,0.3)' : 'rgba(239,68,68,0.3)',
    }));
    const volumeSeries = chart.addHistogramSeries({
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    });
    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    });
    volumeSeries.setData(volumeData as any);

    // Moving average overlays
    if (technical?.moving_averages) {
      const maColors: Record<string, string> = {
        'SMA-20': '#f59e0b', 'SMA-50': '#3b82f6', 'SMA-100': '#8b5cf6',
        'SMA-120': '#a855f7', 'SMA-200': '#ef4444',
        'EMA-12': '#06b6d4', 'EMA-26': '#d946ef', 'EMA-50': '#14b8a6',
      };

      for (const ma of technical.moving_averages) {
        if (ma.value == null) continue;
        const key = `${ma.type}-${ma.period}`;
        const color = maColors[key] || '#6b7280';

        candleSeries.createPriceLine({
          price: ma.value,
          color,
          lineWidth: 1,
          lineStyle: 2,
          axisLabelVisible: true,
          title: key,
        });
      }
    }

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (containerRef.current && chartRef.current) {
        chartRef.current.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
      chartRef.current = null;
    };
  }, [chartData, technical, isIntraday]);

  return <div ref={containerRef} className="w-full rounded-lg overflow-hidden" />;
}

/**
 * For intraday data: return unix timestamp (seconds) so Lightweight Charts
 * can distinguish multiple bars within the same day.
 * For daily/weekly: return "YYYY-MM-DD" business day string.
 */
function parseTime(timeStr: string, intraday: boolean): string | number {
  if (intraday) {
    const d = new Date(timeStr);
    if (!isNaN(d.getTime())) {
      return Math.floor(d.getTime() / 1000);
    }
  }
  // Daily / weekly: extract date portion
  if (timeStr.includes('T')) {
    return timeStr.split('T')[0];
  }
  if (/^\d{4}-\d{2}-\d{2}$/.test(timeStr)) {
    return timeStr;
  }
  const date = new Date(timeStr);
  if (!isNaN(date.getTime())) {
    return date.toISOString().split('T')[0];
  }
  return timeStr;
}
