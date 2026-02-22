import { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { createCheckoutSession } from '../../api/client';

const features = [
  {
    title: 'Overall Scorecard',
    description: 'Composite 0-100 score with letter grade and buy/sell/hold signal',
    included: { trial: true, paid: true },
  },
  {
    title: 'Fundamental Analysis',
    description: 'Valuation, growth, and financial health scoring from multi-source data',
    included: { trial: true, paid: true },
  },
  {
    title: 'Technical Analysis',
    description: 'Candlestick charts, RSI, MACD, moving averages, support/resistance',
    included: { trial: true, paid: true },
  },
  {
    title: 'Earnings Tracker',
    description: 'Quarterly revenue/earnings trends with QoQ and YoY growth rates',
    included: { trial: true, paid: true },
  },
  {
    title: 'News Feed',
    description: 'Real-time financial news with source attribution per ticker',
    included: { trial: true, paid: true },
  },
  {
    title: 'Swing Trade Calculator',
    description: 'Entry zones, stop loss, target prices with risk/reward ratios',
    included: { trial: true, paid: true },
  },
  {
    title: 'AI Macro Analysis',
    description: 'GPT-powered macroeconomic tailwinds & headwinds analysis per stock',
    included: { trial: false, paid: true },
    premium: true,
  },
];

function CheckIcon() {
  return (
    <svg className="w-5 h-5 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
    </svg>
  );
}

function XIcon() {
  return (
    <svg className="w-5 h-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
    </svg>
  );
}

function LockIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0110 0v4" />
    </svg>
  );
}

interface Props {
  onBack?: () => void;
}

export default function PricingPage({ onBack }: Props) {
  const { isAuthenticated, subscription } = useAuth();
  const [loading, setLoading] = useState(false);

  const handleSubscribe = async () => {
    if (!isAuthenticated) return;
    setLoading(true);
    try {
      const origin = window.location.origin;
      const { checkout_url } = await createCheckoutSession(
        `${origin}?subscription=success`,
        `${origin}?subscription=canceled`,
      );
      window.location.href = checkout_url;
    } catch (error) {
      console.error('Failed to create checkout session:', error);
      alert('Failed to start checkout. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const isPaid = subscription?.status === 'paid' || subscription?.status === 'admin' || subscription?.status === 'override';

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-gray-950/80 backdrop-blur-md border-b border-gray-800/50">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <button
            onClick={onBack}
            className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
            </svg>
            Back
          </button>
          <span className="text-xl font-bold text-white tracking-tight">
            <span className="text-blue-400">Stock</span>Cerebro
          </span>
          <div className="w-16" /> {/* Spacer for centering */}
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-blue-950/40 via-gray-950 to-gray-950 pointer-events-none" />
        <div className="relative max-w-4xl mx-auto px-4 pt-16 pb-12 text-center">
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-white mb-4">
            Simple, Transparent Pricing
          </h1>
          <p className="text-lg text-gray-400 max-w-2xl mx-auto">
            Start with a free 7-day trial. Upgrade to unlock AI-powered macro analysis
            and keep full access to all features.
          </p>
        </div>
      </section>

      {/* Pricing Cards */}
      <section className="max-w-5xl mx-auto px-4 pb-16">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-3xl mx-auto">
          {/* Free Trial Card */}
          <div className="card border-gray-700 relative">
            <div className="p-6">
              <h3 className="text-lg font-semibold text-gray-300 mb-1">Free Trial</h3>
              <div className="flex items-baseline gap-1 mb-1">
                <span className="text-4xl font-bold text-white">$0</span>
              </div>
              <p className="text-sm text-gray-500 mb-6">7 days, no credit card required</p>

              <ul className="space-y-3 mb-6">
                {features.map((f) => (
                  <li key={f.title} className="flex items-start gap-3">
                    <span className="mt-0.5 flex-shrink-0">
                      {f.included.trial ? <CheckIcon /> : <XIcon />}
                    </span>
                    <div>
                      <span className={`text-sm ${f.included.trial ? 'text-gray-200' : 'text-gray-600'}`}>
                        {f.title}
                      </span>
                      {!f.included.trial && f.premium && (
                        <span className="ml-2 inline-flex items-center gap-1 text-xs text-gray-600">
                          <LockIcon /> Paid only
                        </span>
                      )}
                    </div>
                  </li>
                ))}
              </ul>

              {!isAuthenticated && (
                <p className="text-sm text-gray-500 text-center">Sign in to start your free trial</p>
              )}
              {isAuthenticated && subscription?.status === 'trialing' && (
                <div className="text-center">
                  <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-blue-500/10 text-blue-400 text-sm border border-blue-500/20">
                    Currently on trial
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Pro Card */}
          <div className="card border-blue-500/50 relative ring-1 ring-blue-500/20">
            <div className="absolute -top-3 left-1/2 -translate-x-1/2">
              <span className="px-3 py-1 rounded-full bg-blue-500 text-white text-xs font-medium">
                Recommended
              </span>
            </div>
            <div className="p-6">
              <h3 className="text-lg font-semibold text-white mb-1">Pro</h3>
              <div className="flex items-baseline gap-1 mb-1">
                <span className="text-4xl font-bold text-white">$19</span>
                <span className="text-gray-400">/month</span>
              </div>
              <p className="text-sm text-gray-500 mb-6">Full access to everything</p>

              <ul className="space-y-3 mb-6">
                {features.map((f) => (
                  <li key={f.title} className="flex items-start gap-3">
                    <span className="mt-0.5 flex-shrink-0"><CheckIcon /></span>
                    <div>
                      <span className="text-sm text-gray-200">{f.title}</span>
                      {f.premium && (
                        <span className="ml-2 inline-flex items-center gap-1 text-xs text-blue-400 bg-blue-500/10 px-1.5 py-0.5 rounded">
                          AI Powered
                        </span>
                      )}
                    </div>
                  </li>
                ))}
              </ul>

              {isAuthenticated && !isPaid && (
                <button
                  onClick={handleSubscribe}
                  disabled={loading}
                  className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:text-gray-500 text-white font-medium rounded-lg transition-colors"
                >
                  {loading ? 'Redirecting...' : 'Subscribe Now'}
                </button>
              )}
              {isAuthenticated && isPaid && (
                <div className="text-center">
                  <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-green-500/10 text-green-400 text-sm border border-green-500/20">
                    Active subscription
                  </span>
                </div>
              )}
              {!isAuthenticated && (
                <p className="text-sm text-gray-500 text-center">Sign in first, then subscribe</p>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* Feature Details */}
      <section className="max-w-4xl mx-auto px-4 pb-20">
        <h2 className="text-2xl font-bold text-white text-center mb-8">What You Get</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {features.map((f) => (
            <div
              key={f.title}
              className={`card ${f.premium ? 'border-blue-500/30 bg-blue-950/20' : ''}`}
            >
              <div className="flex items-start gap-3">
                <div className="flex-1">
                  <h4 className="text-sm font-medium text-white mb-1">
                    {f.title}
                    {f.premium && (
                      <span className="ml-2 text-xs text-blue-400 bg-blue-500/10 px-1.5 py-0.5 rounded">
                        Pro
                      </span>
                    )}
                  </h4>
                  <p className="text-xs text-gray-400">{f.description}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-800/50 py-8">
        <p className="text-center text-gray-600 text-sm">
          &copy; {new Date().getFullYear()} StockCerebro. All rights reserved.
        </p>
      </footer>
    </div>
  );
}
