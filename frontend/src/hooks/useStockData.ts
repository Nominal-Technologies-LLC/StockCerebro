import { useQuery } from '@tanstack/react-query';
import {
  fetchCompanyOverview,
  fetchFundamental,
  fetchTechnical,
  fetchScorecard,
  fetchNews,
  fetchEarnings,
  fetchMacroRisk,
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
