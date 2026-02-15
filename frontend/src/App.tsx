import { useState } from 'react';
import Header from './components/layout/Header';
import SearchBar from './components/layout/SearchBar';
import TabNavigation from './components/layout/TabNavigation';
import CompanyHeader from './components/overview/CompanyHeader';
import QuickStats from './components/overview/QuickStats';
import OverallScorecard from './components/overview/OverallScorecard';
import NewsFeed from './components/overview/NewsFeed';
import FundamentalDashboard from './components/fundamental/FundamentalDashboard';
import EarningsDashboard from './components/earnings/EarningsDashboard';
import TechnicalDashboard from './components/technical/TechnicalDashboard';
import ScorecardDashboard from './components/scorecard/ScorecardDashboard';
import LoadingSpinner from './components/common/LoadingSpinner';
import ErrorBoundary from './components/common/ErrorBoundary';
import LandingPage from './components/auth/LandingPage';
import { useAuth } from './context/AuthContext';
import { useCompanyOverview, useFundamental, useEarnings, useScorecard, useNews } from './hooks/useStockData';

function AppContent() {
  const [ticker, setTicker] = useState('');
  const [activeTab, setActiveTab] = useState('overview');

  const { data: company, isLoading: companyLoading, error: companyError } = useCompanyOverview(ticker);
  const isEtf = company?.is_etf ?? false;
  const { data: fundamental, isLoading: fundLoading } = useFundamental(isEtf ? '' : ticker);
  const { data: earnings, isLoading: earningsLoading } = useEarnings(isEtf ? '' : ticker);
  const { data: scorecard, isLoading: scorecardLoading } = useScorecard(ticker);
  const { data: news } = useNews(ticker);

  const handleSearch = (t: string) => {
    setTicker(t);
    setActiveTab('overview');
  };

  const isLoading = companyLoading;

  return (
    <div className="min-h-screen bg-gray-950">
      <Header />
      <main className="max-w-7xl mx-auto px-4 py-6">
        {/* Search */}
        <div className="flex justify-center mb-8">
          <SearchBar onSearch={handleSearch} isLoading={isLoading} />
        </div>

        {/* No ticker state */}
        {!ticker && (
          <div className="text-center py-20">
            <h2 className="text-2xl font-bold text-gray-600 mb-2">Enter a ticker to begin</h2>
            <p className="text-gray-700 text-sm">
              Get comprehensive fundamental + technical analysis with buy/sell/hold signals
            </p>
          </div>
        )}

        {/* Loading */}
        {ticker && isLoading && !companyError && (
          <LoadingSpinner message={`Analyzing ${ticker}...`} />
        )}

        {/* Error */}
        {ticker && companyError && !isLoading && (
          <div className="card border-red-500/30 text-center py-8">
            <p className="text-red-400 font-medium">
              Could not find ticker &quot;{ticker}&quot;
            </p>
            <p className="text-gray-500 text-sm mt-1">
              Check the symbol and try again
            </p>
          </div>
        )}

        {/* Content */}
        {company && !companyError && (
          <>
            <CompanyHeader company={company} />
            <TabNavigation activeTab={activeTab} onTabChange={setActiveTab} isEtf={isEtf} />

            {activeTab === 'overview' && (
              <ErrorBoundary>
                <div className="space-y-6">
                  {scorecard && <OverallScorecard scorecard={scorecard} />}
                  {scorecardLoading && <LoadingSpinner message="Computing scorecard..." />}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <QuickStats company={company} />
                    <NewsFeed articles={news ?? []} />
                  </div>
                </div>
              </ErrorBoundary>
            )}

            {activeTab === 'fundamental' && !isEtf && (
              <ErrorBoundary>
                {fundLoading && <LoadingSpinner message="Analyzing fundamentals..." />}
                {fundamental && <FundamentalDashboard data={fundamental} />}
              </ErrorBoundary>
            )}

            {activeTab === 'earnings' && !isEtf && (
              <ErrorBoundary>
                {earningsLoading && <LoadingSpinner message="Loading earnings..." />}
                {earnings && <EarningsDashboard data={earnings} />}
              </ErrorBoundary>
            )}

            {activeTab === 'technical' && (
              <ErrorBoundary>
                <TechnicalDashboard ticker={ticker} />
              </ErrorBoundary>
            )}

            {activeTab === 'scorecard' && (
              <ErrorBoundary>
                {scorecardLoading && <LoadingSpinner message="Generating scorecard..." />}
                {scorecard && <ScorecardDashboard data={scorecard} />}
              </ErrorBoundary>
            )}
          </>
        )}
      </main>
    </div>
  );
}

export default function App() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <LoadingSpinner message="Loading..." />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LandingPage />;
  }

  return <AppContent />;
}
