import { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { createPortalSession } from '../../api/client';

export default function UserMenu() {
  const { user, subscription, logout } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [portalLoading, setPortalLoading] = useState(false);

  if (!user) return null;

  const handleLogout = async () => {
    setIsOpen(false);
    await logout();
  };

  const handleManageSubscription = async () => {
    setPortalLoading(true);
    try {
      const { portal_url } = await createPortalSession(window.location.href);
      window.location.href = portal_url;
    } catch (error) {
      console.error('Failed to open customer portal:', error);
      alert('Failed to open subscription management. Please try again.');
    } finally {
      setPortalLoading(false);
    }
  };

  const showManageSubscription = subscription?.status === 'paid' || subscription?.status === 'override';

  const statusLabels: Record<string, string> = {
    admin: 'Admin',
    override: 'Full Access',
    paid: 'Pro',
    trialing: 'Free Trial',
    expired: 'Expired',
  };

  const statusColors: Record<string, string> = {
    admin: 'text-purple-400',
    override: 'text-blue-400',
    paid: 'text-green-400',
    trialing: 'text-yellow-400',
    expired: 'text-red-400',
  };

  const statusLabel = subscription?.status ? statusLabels[subscription.status] || subscription.status : null;
  const statusColor = subscription?.status ? statusColors[subscription.status] || 'text-gray-400' : 'text-gray-400';

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 hover:bg-gray-800 rounded-lg p-2 transition-colors"
      >
        {user.picture && (
          <img
            src={user.picture}
            alt={user.name}
            className="w-8 h-8 rounded-full"
          />
        )}
        <span className="text-sm font-medium text-gray-200">{user.name}</span>
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute right-0 mt-2 w-56 bg-gray-900 rounded-lg shadow-lg border border-gray-800 py-1 z-20">
            <div className="px-4 py-2 border-b border-gray-800">
              <p className="text-xs text-gray-500">{user.email}</p>
              {statusLabel && (
                <p className={`text-xs font-medium mt-0.5 ${statusColor}`}>
                  {statusLabel}
                </p>
              )}
            </div>
            {showManageSubscription && (
              <button
                onClick={handleManageSubscription}
                disabled={portalLoading}
                className="w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-gray-800 disabled:text-gray-600"
              >
                {portalLoading ? 'Opening...' : 'Manage Subscription'}
              </button>
            )}
            <button
              onClick={handleLogout}
              className="w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-gray-800"
            >
              Sign Out
            </button>
          </div>
        </>
      )}
    </div>
  );
}
