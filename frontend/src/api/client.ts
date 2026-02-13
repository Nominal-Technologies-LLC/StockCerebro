import axios from 'axios';
import type {
  CompanyOverview,
  ChartData,
  FundamentalAnalysis,
  TechnicalAnalysis,
  Scorecard,
  NewsArticle,
  EarningsResponse,
} from '../types/stock';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  timeout: 30000,
});

export async function fetchCompanyOverview(ticker: string): Promise<CompanyOverview> {
  const { data } = await api.get(`/api/stock/${ticker}`);
  return data;
}

export async function fetchChartData(
  ticker: string,
  period = '6mo',
  interval = '1d'
): Promise<ChartData> {
  const { data } = await api.get(`/api/stock/${ticker}/chart`, {
    params: { period, interval },
  });
  return data;
}

export async function fetchFundamental(ticker: string): Promise<FundamentalAnalysis> {
  const { data } = await api.get(`/api/stock/${ticker}/fundamental`);
  return data;
}

export async function fetchTechnical(
  ticker: string,
  timeframe = 'd'
): Promise<TechnicalAnalysis> {
  const { data } = await api.get(`/api/stock/${ticker}/technical`, {
    params: { timeframe },
  });
  return data;
}

export async function fetchScorecard(ticker: string): Promise<Scorecard> {
  const { data } = await api.get(`/api/stock/${ticker}/scorecard`);
  return data;
}

export async function fetchNews(ticker: string): Promise<NewsArticle[]> {
  const { data } = await api.get(`/api/stock/${ticker}/news`);
  return data;
}

export async function fetchEarnings(ticker: string): Promise<EarningsResponse> {
  const { data } = await api.get(`/api/stock/${ticker}/earnings`);
  return data;
}

export async function healthCheck(): Promise<{ status: string }> {
  const { data } = await api.get('/api/health');
  return data;
}
