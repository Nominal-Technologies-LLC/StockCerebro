import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  fetchCompanyOverview,
  fetchFundamental,
  fetchTechnical,
  fetchScorecard,
  fetchNews,
  fetchEarnings,
  fetchMacroRisk,
  fetchRecentlyViewed,
  recordRecentlyViewed,
} from '../api/client';
import { getRefreshInterval } from '../utils/marketHours';

export function useCompanyOverview(ticker: string) {
  return useQuery({
    queryKey: ['company', ticker],
    queryFn: () => fetchCompanyOverview(ticker),
    enabled: !!ticker,
    staleTime: getRefreshInterval(),
  });
}

export function useFundamental(ticker: string) {
  return useQuery({
    queryKey: ['fundamental', ticker],
    queryFn: () => fetchFundamental(ticker),
    enabled: !!ticker,
    staleTime: 5 * 60_000,
  });
}

export function useTechnical(ticker: string, timeframe = 'd') {
  return useQuery({
    queryKey: ['technical', ticker, timeframe],
    queryFn: () => fetchTechnical(ticker, timeframe),
    enabled: !!ticker,
    staleTime: getRefreshInterval(),
  });
}

export function useScorecard(ticker: string) {
  return useQuery({
    queryKey: ['scorecard', ticker],
    queryFn: () => fetchScorecard(ticker),
    enabled: !!ticker,
    staleTime: getRefreshInterval(),
  });
}

export function useNews(ticker: string) {
  return useQuery({
    queryKey: ['news', ticker],
    queryFn: () => fetchNews(ticker),
    enabled: !!ticker,
    staleTime: 5 * 60_000,
  });
}

export function useEarnings(ticker: string) {
  return useQuery({
    queryKey: ['earnings', ticker],
    queryFn: () => fetchEarnings(ticker),
    enabled: !!ticker,
    staleTime: 10 * 60_000,
  });
}

export function useMacroRisk(ticker: string, enabled = true) {
  return useQuery({
    queryKey: ['macro', ticker],
    queryFn: () => fetchMacroRisk(ticker),
    enabled: !!ticker && enabled,
    staleTime: 30 * 60_000,
  });
}

export function useRecentlyViewed() {
  return useQuery({
    queryKey: ['recently-viewed'],
    queryFn: fetchRecentlyViewed,
    staleTime: 60_000,
  });
}

export function useRecordView() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (params: {
      ticker: string;
      companyName: string | null;
      grade: string | null;
      signal: string | null;
      score: number | null;
    }) =>
      recordRecentlyViewed(
        params.ticker,
        params.companyName,
        params.grade,
        params.signal,
        params.score,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recently-viewed'] });
    },
  });
}
