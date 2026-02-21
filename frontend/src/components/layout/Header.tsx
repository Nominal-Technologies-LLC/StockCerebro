import { useAuth } from '../../context/AuthContext';
import UserMenu from './UserMenu';

interface Props {
  showAdmin?: boolean;
  onToggleAdmin?: () => void;
}

export default function Header({ showAdmin, onToggleAdmin }: Props) {
  const { user } = useAuth();

  return (
    <header className="border-b border-gray-800 bg-gray-950/80 backdrop-blur-sm sticky top-0 z-50">
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
