import { useState } from 'react';
import { createCheckoutSession } from '../../api/client';

export default function MacroUpgradePrompt() {
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

  return (
    <div className="card border-blue-500/30 bg-blue-950/10 text-center py-12 px-6">
      <div className="flex justify-center mb-4">
        <div className="w-14 h-14 rounded-full bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
          <svg className="w-7 h-7 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0110 0v4" />
          </svg>
        </div>
      </div>
      <h3 className="text-xl font-bold text-white mb-2">AI Macro Analysis — Pro Feature</h3>
      <p className="text-gray-400 mb-6 max-w-md mx-auto">
        Get AI-powered macroeconomic tailwinds and headwinds analysis for any stock.
        Upgrade to Pro to unlock this feature.
      </p>
      <button
        onClick={handleSubscribe}
        disabled={loading}
        className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:text-gray-500 text-white font-medium rounded-lg transition-colors"
      >
        {loading ? 'Redirecting...' : 'Upgrade to Pro — $19/mo'}
      </button>
    </div>
  );
}
