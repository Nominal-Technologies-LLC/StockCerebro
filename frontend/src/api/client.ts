import axios from 'axios';
import type {
  CompanyOverview,
  ChartData,
  FundamentalAnalysis,
  TechnicalAnalysis,
  Scorecard,
  NewsArticle,
  EarningsResponse,
  MacroRiskResponse,
  RecentlyViewedItem,
  SymbolSearchResult,
} from '../types/stock';
import type { AdminUser, SubscriptionInfo, TokenResponse, User } from '../types/auth';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  timeout: 30000,
  withCredentials: true,  // Send HTTP-only cookies with requests
});

export async function searchSymbols(query: string): Promise<SymbolSearchResult[]> {
  const { data } = await api.get('/api/stock/search', { params: { q: query } });
  return data;
}

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

export async function fetchMacroRisk(ticker: string): Promise<MacroRiskResponse> {
  const { data } = await api.get(`/api/stock/${ticker}/macro`);
  return data;
}

export async function validateTicker(ticker: string): Promise<boolean> {
  try {
    await api.get(`/api/stock/${ticker}/validate`);
    return true;
  } catch {
    return false;
  }
}

export async function healthCheck(): Promise<{ status: string }> {
  const { data } = await api.get('/api/health');
  return data;
}

// Auth API functions
export async function googleLogin(credential: string): Promise<TokenResponse> {
  const { data } = await api.post('/api/auth/google/login', { credential });
  return data;
}

export async function logout(): Promise<void> {
  await api.post('/api/auth/logout');
}

export async function getCurrentUser(): Promise<User> {
  const { data } = await api.get('/api/auth/me');
  return data;
}

// Subscription API functions
export async function fetchSubscriptionStatus(): Promise<SubscriptionInfo> {
  const { data } = await api.get('/api/subscription/status');
  return data;
}

export async function createCheckoutSession(successUrl: string, cancelUrl: string): Promise<{ checkout_url: string }> {
  const { data } = await api.post('/api/subscription/create-checkout-session', {
    success_url: successUrl,
    cancel_url: cancelUrl,
  });
  return data;
}

export async function createPortalSession(returnUrl: string): Promise<{ portal_url: string }> {
  const { data } = await api.post('/api/subscription/create-portal-session', {
    return_url: returnUrl,
  });
  return data;
}

// Recently viewed API functions
export async function fetchRecentlyViewed(): Promise<RecentlyViewedItem[]> {
  const { data } = await api.get('/api/recently-viewed');
  return data;
}

export async function recordRecentlyViewed(
  ticker: string,
  companyName: string | null,
  grade: string | null,
  signal: string | null,
  score: number | null,
): Promise<RecentlyViewedItem> {
  const { data } = await api.post('/api/recently-viewed', {
    ticker,
    company_name: companyName,
    grade,
    signal,
    score,
  });
  return data;
}

// Admin API functions
export async function fetchAdminUsers(): Promise<AdminUser[]> {
  const { data } = await api.get('/api/admin/users');
  return data;
}

export async function overrideUserSubscription(userId: number): Promise<void> {
  await api.post(`/api/admin/users/${userId}/override-subscription`);
}

export async function removeUserOverride(userId: number): Promise<void> {
  await api.post(`/api/admin/users/${userId}/remove-override`);
}
