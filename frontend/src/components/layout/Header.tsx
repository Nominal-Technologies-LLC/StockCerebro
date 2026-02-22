import { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { createCheckoutSession } from '../../api/client';
import UserMenu from './UserMenu';

interface Props {
  showAdmin?: boolean;
  onToggleAdmin?: () => void;
}

function TrialBanner() {
  const { subscription } = useAuth();
  const [loading, setLoading] = useState(false);

  if (subscription?.status !== 'trialing' || !subscription.trial_ends_at) {
    return null;
  }

  const daysLeft = Math.max(
    0,
    Math.ceil((new Date(subscription.trial_ends_at).getTime() - Date.now()) / (1000 * 60 * 60 * 24))
  );

  const handleUpgrade = async () => {
    setLoading(true);
    try {
      const origin = window.location.origin;
      const { checkout_url } = await createCheckoutSession(
        `${origin}?subscription=success`,
        `${origin}?subscription=canceled`,
      );
      window.location.href = checkout_url;
    } catch {
      alert('Failed to start checkout. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-blue-950/50 border-b border-blue-800/30">
      <div className="max-w-7xl mx-auto px-4 py-1.5 flex items-center justify-center gap-3 text-xs">
        <span className="text-blue-300">
          {daysLeft > 0
            ? `Free trial: ${daysLeft} day${daysLeft === 1 ? '' : 's'} remaining`
            : 'Free trial ends today'
          }
        </span>
        <button
          onClick={handleUpgrade}
          disabled={loading}
          className="px-2.5 py-0.5 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 text-white rounded text-xs font-medium transition-colors"
        >
          {loading ? '...' : 'Upgrade'}
        </button>
      </div>
    </div>
  );
}

export default function Header({ showAdmin, onToggleAdmin }: Props) {
  const { user } = useAuth();

  return (
    <header className="border-b border-gray-800 bg-gray-950/80 backdrop-blur-sm sticky top-0 z-50">
      <TrialBanner />
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1
            className="text-xl font-bold text-white tracking-tight cursor-pointer"
            onClick={showAdmin ? onToggleAdmin : undefined}
          >
            <span className="text-blue-400">Stock</span>Cerebro
          </h1>
          <span className="text-xs text-gray-500 hidden sm:block">Fundamental + Technical Analysis</span>
        </div>
        <div className="flex items-center gap-3">
          {user?.is_admin && (
            <button
              onClick={onToggleAdmin}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                showAdmin
                  ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
              }`}
            >
              Admin
            </button>
          )}
          <UserMenu />
        </div>
      </div>
    </header>
  );
}
