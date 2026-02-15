import UserMenu from './UserMenu';

export default function Header() {
  return (
    <header className="border-b border-gray-800 bg-gray-950/80 backdrop-blur-sm sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold text-white tracking-tight">
            <span className="text-blue-400">Stock</span>Cerebro
          </h1>
          <span className="text-xs text-gray-500 hidden sm:block">Fundamental + Technical Analysis</span>
        </div>
        <UserMenu />
      </div>
    </header>
  );
}
