interface Props {
  activeTab: string;
  onTabChange: (tab: string) => void;
  isEtf?: boolean;
  hasMacroAccess?: boolean;
}

const allTabs = [
  { id: 'overview', label: 'Overview' },
  { id: 'fundamental', label: 'Fundamental' },
  { id: 'technical', label: 'Technical' },
  { id: 'earnings', label: 'Earnings' },
  { id: 'macro', label: 'Macro' },
  { id: 'scorecard', label: 'Scorecard' },
];

function LockIcon() {
  return (
    <svg className="w-3 h-3 inline-block ml-1 opacity-60" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0110 0v4" />
    </svg>
  );
}

export default function TabNavigation({ activeTab, onTabChange, isEtf, hasMacroAccess = true }: Props) {
  const tabs = isEtf ? allTabs.filter((t) => t.id !== 'fundamental' && t.id !== 'earnings') : allTabs;

  return (
    <nav className="flex gap-1 border-b border-gray-800 mb-4">
      {tabs.map((tab) => {
        const isLocked = tab.id === 'macro' && !hasMacroAccess;

        return (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeTab === tab.id
                ? 'text-blue-400 border-blue-400'
                : 'text-gray-500 border-transparent hover:text-gray-300'
            }`}
          >
            {tab.label}
            {isLocked && <LockIcon />}
          </button>
        );
      })}
    </nav>
  );
}
