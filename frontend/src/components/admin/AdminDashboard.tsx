import { useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchAdminUsers, overrideUserSubscription, removeUserOverride } from '../../api/client';
import type { AdminUser } from '../../types/auth';
import LoadingSpinner from '../common/LoadingSpinner';
import { useState } from 'react';

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function timeAgo(iso: string): string {
  const seconds = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  return `${months}mo ago`;
}

function StatusBadge({ status }: { status: string | null }) {
  const colors: Record<string, string> = {
    admin: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
    paid: 'bg-green-500/20 text-green-400 border-green-500/30',
    active: 'bg-green-500/20 text-green-400 border-green-500/30',
    override: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    trialing: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    expired: 'bg-red-500/20 text-red-400 border-red-500/30',
    canceled: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
    past_due: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  };

  const label = status || 'unknown';
  const colorClass = colors[label] || 'bg-gray-500/20 text-gray-400 border-gray-500/30';

  return (
    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium border ${colorClass}`}>
      {label}
    </span>
  );
}

function OverrideButton({ user, onToggle }: { user: AdminUser; onToggle: (userId: number, grant: boolean) => void }) {
  // Don't show override button for admins
  if (user.subscription_status === 'admin') {
    return null;
  }

  return (
    <button
      onClick={() => onToggle(user.id, !user.subscription_override)}
      className={`px-2 py-1 text-xs font-medium rounded transition-colors ${
        user.subscription_override
          ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30 hover:bg-red-500/20 hover:text-red-400 hover:border-red-500/30'
          : 'text-gray-500 hover:text-blue-400 hover:bg-blue-500/10 border border-gray-700 hover:border-blue-500/30'
      }`}
      title={user.subscription_override ? 'Remove free access override' : 'Grant free access override'}
    >
      {user.subscription_override ? 'Remove Override' : 'Grant Override'}
    </button>
  );
}

export default function AdminDashboard() {
  const queryClient = useQueryClient();
  const [pendingAction, setPendingAction] = useState<number | null>(null);

  const { data: users, isLoading, error } = useQuery<AdminUser[]>({
    queryKey: ['admin', 'users'],
    queryFn: fetchAdminUsers,
    staleTime: 30_000,
  });

  const handleOverrideToggle = async (userId: number, grant: boolean) => {
    setPendingAction(userId);
    try {
      if (grant) {
        await overrideUserSubscription(userId);
      } else {
        await removeUserOverride(userId);
      }
      queryClient.invalidateQueries({ queryKey: ['admin', 'users'] });
    } catch (err) {
      console.error('Failed to toggle override:', err);
      alert('Failed to update subscription override.');
    } finally {
      setPendingAction(null);
    }
  };

  if (isLoading) {
    return <LoadingSpinner message="Loading users..." />;
  }

  if (error) {
    return (
      <div className="card border-red-500/30 text-center py-8">
        <p className="text-red-400 font-medium">Failed to load users</p>
        <p className="text-gray-500 text-sm mt-1">
          {error instanceof Error ? error.message : 'Unknown error'}
        </p>
      </div>
    );
  }

  if (!users || users.length === 0) {
    return (
      <div className="card text-center py-8">
        <p className="text-gray-500">No users found</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-300">
          Registered Users ({users.length})
        </h3>
      </div>

      <div className="card overflow-hidden !p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-left">
                <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                  User
                </th>
                <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Email
                </th>
                <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Subscription
                </th>
                <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Trial Ends
                </th>
                <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Joined
                </th>
                <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Last Login
                </th>
                <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/50">
              {users.map((user) => (
                <tr
                  key={user.id}
                  className={`hover:bg-gray-800/30 transition-colors ${pendingAction === user.id ? 'opacity-50' : ''}`}
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      {user.picture ? (
                        <img
                          src={user.picture}
                          alt={user.name}
                          className="w-8 h-8 rounded-full"
                        />
                      ) : (
                        <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center">
                          <span className="text-xs font-medium text-gray-400">
                            {user.name.charAt(0).toUpperCase()}
                          </span>
                        </div>
                      )}
                      <span className="font-medium text-gray-200">{user.name}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-400">{user.email}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={user.subscription_status} />
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-xs">
                    {user.trial_ends_at ? formatDate(user.trial_ends_at) : '—'}
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-gray-400" title={formatDate(user.created_at)}>
                      {formatDate(user.created_at)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-gray-400" title={formatDate(user.last_login)}>
                      {timeAgo(user.last_login)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <OverrideButton
                      user={user}
                      onToggle={handleOverrideToggle}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
