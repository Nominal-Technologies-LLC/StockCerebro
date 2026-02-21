import { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { createCheckoutSession } from '../../api/client';

interface Props {
  onViewPricing: () => void;
}

export default function PaywallGate({ onViewPricing }: Props) {
  const { subscription, logout } = useAuth();
  const [loading, setLoading] = useState(false);

  const handleSubscribe = async () => {
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

  const trialEnded = subscription?.status === 'expired' && subscription?.trial_ends_at;

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <div className="max-w-md w-full text-center">
        <div className="card border-gray-700 p-8">
          {/* Icon */}
          <div className="flex justify-center mb-6">
            <div className="w-16 h-16 rounded-full bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
              <svg className="w-8 h-8 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0110 0v4" />
              </svg>
            </div>
          </div>

          <h2 className="text-2xl font-bold text-white mb-2">
            {trialEnded ? 'Your Trial Has Ended' : 'Subscription Required'}
          </h2>
          <p className="text-gray-400 mb-6">
            {trialEnded
              ? 'Your 7-day free trial has expired. Subscribe to continue using StockCerebro with full access to all features.'
              : 'An active subscription is required to use StockCerebro. Subscribe to get started.'
            }
          </p>

          <div className="space-y-3">
            <button
              onClick={handleSubscribe}
              disabled={loading}
              className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:text-gray-500 text-white font-medium rounded-lg transition-colors"
            >
              {loading ? 'Redirecting to checkout...' : 'Subscribe Now — $19/mo'}
            </button>

            <button
              onClick={onViewPricing}
              className="w-full py-2.5 px-4 text-gray-400 hover:text-white hover:bg-gray-800 font-medium rounded-lg transition-colors text-sm"
            >
              View Pricing Details
            </button>

            <button
              onClick={logout}
              className="w-full py-2 px-4 text-gray-600 hover:text-gray-400 text-sm transition-colors"
            >
              Sign out
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
