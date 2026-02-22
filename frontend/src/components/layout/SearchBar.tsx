import { useState } from 'react';

interface Props {
  onSearch: (ticker: string) => void;
  isLoading?: boolean;
  onInputChange?: () => void;
}

export default function SearchBar({ onSearch, isLoading, onInputChange }: Props) {
  const [input, setInput] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const ticker = input.trim().toUpperCase();
    if (ticker) {
      onSearch(ticker);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-2 w-full max-w-md">
      <input
        type="text"
        value={input}
        onChange={(e) => { setInput(e.target.value); onInputChange?.(); }}
        placeholder="Enter ticker (e.g. AAPL)"
        className="flex-1 px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 uppercase"
        maxLength={10}
      />
      <button
        type="submit"
        disabled={isLoading || !input.trim()}
        className="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:text-gray-500 text-white font-medium rounded-lg transition-colors"
      >
        {isLoading ? 'Loading...' : 'Analyze'}
      </button>
    </form>
  );
}
