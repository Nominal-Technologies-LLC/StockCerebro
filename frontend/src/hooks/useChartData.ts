import { useQuery } from '@tanstack/react-query';
import { fetchChartData } from '../api/client';
import { getRefreshInterval } from '../utils/marketHours';

export function useChartData(ticker: string, period = '6mo', interval = '1d') {
  return useQuery({
    queryKey: ['chart', ticker, period, interval],
    queryFn: () => fetchChartData(ticker, period, interval),
    enabled: !!ticker,
    staleTime: getRefreshInterval(),
  });
}
