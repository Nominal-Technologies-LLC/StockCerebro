import { useState, useEffect } from 'react';
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
import MacroDashboard from './components/macro/MacroDashboard';
import AdminDashboard from './components/admin/AdminDashboard';
import LoadingSpinner from './components/common/LoadingSpinner';
import ErrorBoundary from './components/common/ErrorBoundary';
import LandingPage from './components/auth/LandingPage';
import PricingPage from './components/subscription/PricingPage';
import PaywallGate from './components/subscription/PaywallGate';
import MacroUpgradePrompt from './components/subscription/MacroUpgradePrompt';
import { useAuth } from './context/AuthContext';
import { useCompanyOverview, useFundamental, useEarnings, useScorecard, useNews, useMacroRisk } from './hooks/useStockData';
import { validateTicker } from './api/client';

function AppContent() {
  const { hasMacroAccess } = useAuth();
  const [ticker, setTicker] = useState('');
  const [activeTab, setActiveTab] = useState('overview');
  const [showAdmin, setShowAdmin] = useState(false);
  const [tickerError, setTickerError] = useState('');
  const [isValidating, setIsValidating] = useState(false);

  const { data: company, isLoading: companyLoading, error: companyError } = useCompanyOverview(ticker);
  const isEtf = company?.is_etf ?? false;
  const { data: fundamental, isLoading: fundLoading } = useFundamental(isEtf ? '' : ticker);
  const { data: earnings, isLoading: earningsLoading } = useEarnings(isEtf ? '' : ticker);
  const { data: scorecard, isLoading: scorecardLoading } = useScorecard(ticker);
  const { data: news } = useNews(ticker);
  const { data: macroRisk, isLoading: macroLoading } = useMacroRisk(
    ticker,
    activeTab === 'macro' && hasMacroAccess
  );

  const handleSearch = async (t: string) => {
    setTickerError('');
    setIsValidating(true);
    const valid = await validateTicker(t);
    setIsValidating(false);
    if (!valid) {
      setTickerError(`Ticker "${t}" not found. Check the symbol and try again.`);
      return;
    }
    setTicker(t);
    setActiveTab('overview');
    setShowAdmin(false);
  };

  const isLoading = companyLoading || isValidating;

  return (
    <div className="min-h-screen bg-gray-950">
      <Header showAdmin={showAdmin} onToggleAdmin={() => setShowAdmin(!showAdmin)} />
      <main className="max-w-7xl mx-auto px-4 py-6">
        {showAdmin ? (
          <ErrorBoundary>
            <AdminDashboard />
          </ErrorBoundary>
        ) : (
          <>
            {/* Search */}
            <div className="flex flex-col items-center mb-8 gap-2">
              <SearchBar onSearch={handleSearch} isLoading={isLoading} onInputChange={() => setTickerError('')} />
              {tickerError && (
                <p className="text-red-400 text-sm">{tickerError}</p>
              )}
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
                <TabNavigation
                  activeTab={activeTab}
                  onTabChange={setActiveTab}
                  isEtf={isEtf}
                  hasMacroAccess={hasMacroAccess}
                />

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

                {activeTab === 'macro' && (
                  <ErrorBoundary>
                    {hasMacroAccess ? (
                      <>
                        {macroLoading && <LoadingSpinner message="Analyzing macro factors..." />}
                        {macroRisk && <MacroDashboard data={macroRisk} />}
                      </>
                    ) : (
                      <MacroUpgradePrompt />
                    )}
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
          </>
        )}
      </main>
    </div>
  );
}

export default function App() {
  const { isAuthenticated, isLoading, hasAccess, refreshSubscription } = useAuth();
  const [showPricing, setShowPricing] = useState(false);

  // Check for subscription success/canceled query params
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const subscriptionResult = params.get('subscription');
    if (subscriptionResult === 'success') {
      // Refresh subscription status after successful checkout
      refreshSubscription();
      // Clean up URL
      window.history.replaceState({}, '', window.location.pathname);
    } else if (subscriptionResult === 'canceled') {
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, [refreshSubscription]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <LoadingSpinner message="Loading..." />
      </div>
    );
  }

  // Show pricing page (accessible from landing page or paywall)
  if (showPricing) {
    return <PricingPage onBack={() => setShowPricing(false)} />;
  }

  // Not authenticated -> landing page
  if (!isAuthenticated) {
    return <LandingPage onViewPricing={() => setShowPricing(true)} />;
  }

  // Authenticated but no access (trial expired, no subscription) -> paywall
  if (!hasAccess) {
    return <PaywallGate onViewPricing={() => setShowPricing(true)} />;
  }

  // Authenticated with access -> main app
  return <AppContent />;
}
