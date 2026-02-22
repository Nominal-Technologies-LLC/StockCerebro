import { useState, useRef, useEffect } from 'react';
import { useSymbolSearch } from '../../hooks/useStockData';

interface Props {
  onSearch: (ticker: string) => void;
  isLoading?: boolean;
  onInputChange?: () => void;
}

export default function SearchBar({ onSearch, isLoading, onInputChange }: Props) {
  const [input, setInput] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);
  const [highlightIndex, setHighlightIndex] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const { data: results } = useSymbolSearch(input);
  const suggestions = results ?? [];

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Show dropdown when there are suggestions and input has content
  useEffect(() => {
    if (suggestions.length > 0 && input.trim().length >= 1) {
      setShowDropdown(true);
    }
  }, [suggestions, input]);

  // Reset highlight when suggestions change
  useEffect(() => {
    setHighlightIndex(-1);
  }, [suggestions]);

  const selectSymbol = (symbol: string) => {
    setInput(symbol);
    setShowDropdown(false);
    setHighlightIndex(-1);
    onSearch(symbol.toUpperCase());
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (highlightIndex >= 0 && highlightIndex < suggestions.length) {
      selectSymbol(suggestions[highlightIndex].symbol);
      return;
    }
    const ticker = input.trim().toUpperCase();
    if (ticker) {
      setShowDropdown(false);
      onSearch(ticker);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showDropdown || suggestions.length === 0) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlightIndex((prev) =>
        prev < suggestions.length - 1 ? prev + 1 : 0
      );
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlightIndex((prev) =>
        prev > 0 ? prev - 1 : suggestions.length - 1
      );
    } else if (e.key === 'Escape') {
      setShowDropdown(false);
      setHighlightIndex(-1);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInput(e.target.value);
    onInputChange?.();
  };

  return (
    <div ref={containerRef} className="relative w-full max-w-md">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={handleInputChange}
          onFocus={() => {
            if (suggestions.length > 0 && input.trim().length >= 1) {
              setShowDropdown(true);
            }
          }}
          onKeyDown={handleKeyDown}
          placeholder="Search ticker or company name"
          className="flex-1 px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 uppercase"
          maxLength={20}
          autoComplete="off"
        />
        <button
          type="submit"
          disabled={isLoading || !input.trim()}
          className="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:text-gray-500 text-white font-medium rounded-lg transition-colors"
        >
          {isLoading ? 'Loading...' : 'Analyze'}
        </button>
      </form>

      {/* Autocomplete dropdown */}
      {showDropdown && suggestions.length > 0 && (
        <div className="absolute z-50 mt-1 w-full bg-gray-900 border border-gray-700 rounded-lg shadow-xl overflow-hidden">
          {suggestions.map((item, idx) => (
            <button
              key={item.symbol}
              type="button"
              onMouseDown={(e) => {
                e.preventDefault(); // Prevent input blur
                selectSymbol(item.symbol);
              }}
              onMouseEnter={() => setHighlightIndex(idx)}
              className={`
                w-full text-left px-4 py-2.5 flex items-center gap-3 transition-colors
                ${idx === highlightIndex
                  ? 'bg-blue-600/20 text-white'
                  : 'text-gray-300 hover:bg-gray-800'
                }
                ${idx < suggestions.length - 1 ? 'border-b border-gray-800/50' : ''}
              `}
            >
              <span className="font-bold text-sm text-blue-400 w-16 flex-shrink-0">
                {item.symbol}
              </span>
              <span className="text-sm text-gray-400 truncate flex-1">
                {item.name}
              </span>
              {item.exchange && (
                <span className="text-[10px] text-gray-600 flex-shrink-0">
                  {item.exchange}
                </span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
