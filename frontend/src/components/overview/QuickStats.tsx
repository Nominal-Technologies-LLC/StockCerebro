import type { CompanyOverview } from '../../types/stock';
import { formatLargeNumber, formatCurrency, formatNumber, formatPercent } from '../../utils/formatting';

interface Props {
  company: CompanyOverview;
}

interface StatItem {
  label: string;
  value: string;
  highlight?: 'primary' | 'success' | 'warning';
  size?: 'normal' | 'large';
}

export default function QuickStats({ company }: Props) {
  // Color code PE ratio (good < 25, warning 25-40, high > 40)
  const getPERating = (pe: number | null | undefined): 'success' | 'warning' | undefined => {
    if (pe == null) return undefined;
    if (pe < 25) return 'success';
    if (pe > 40) return 'warning';
    return undefined;
  };

  // Color code beta (low volatility < 1, high > 1.5)
  const getBetaRating = (beta: number | null | undefined): 'success' | 'warning' | undefined => {
    if (beta == null) return undefined;
    if (beta < 1) return 'success';
    if (beta > 1.5) return 'warning';
    return undefined;
  };

  const stats: StatItem[] = [
    {
      label: 'Market Cap',
      value: formatLargeNumber(company.market_cap),
      highlight: 'primary',
      size: 'large'
    },
    {
      label: 'P/E Ratio',
      value: company.pe_ratio?.toFixed(2) ?? 'N/A',
      highlight: getPERating(company.pe_ratio)
    },
    {
      label: 'Forward P/E',
      value: company.forward_pe?.toFixed(2) ?? 'N/A',
      highlight: getPERating(company.forward_pe)
    },
    {
      label: 'Volume',
      value: formatLargeNumber(company.volume)
    },
    {
      label: 'Avg Volume',
      value: formatLargeNumber(company.avg_volume)
    },
    {
      label: 'Day Range',
      value: company.day_low && company.day_high
        ? `${formatCurrency(company.day_low)} - ${formatCurrency(company.day_high)}`
        : 'N/A'
    },
    {
      label: '52-Week Range',
      value: company.fifty_two_week_low && company.fifty_two_week_high
        ? `${formatCurrency(company.fifty_two_week_low)} - ${formatCurrency(company.fifty_two_week_high)}`
        : 'N/A',
      size: 'large'
    },
    {
      label: 'Beta',
      value: company.beta?.toFixed(2) ?? 'N/A',
      highlight: getBetaRating(company.beta)
    },
    {
      label: 'Dividend Yield',
      value: company.dividend_yield != null
        ? formatPercent(company.dividend_yield * 100)
        : 'N/A',
      highlight: company.dividend_yield && company.dividend_yield > 0.02 ? 'success' : undefined
    },
  ];

  const getHighlightClasses = (highlight?: string, size?: string) => {
    let classes = 'text-white';

    if (highlight === 'primary') {
      classes = 'text-blue-400';
    } else if (highlight === 'success') {
      classes = 'text-green-400';
    } else if (highlight === 'warning') {
      classes = 'text-orange-400';
    }

    if (size === 'large') {
      classes += ' text-lg font-bold';
    } else {
      classes += ' text-base font-semibold';
    }

    return classes;
  };

  return (
    <div className="card p-6">
      <h3 className="text-lg font-semibold text-white mb-4">Quick Stats</h3>
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        {stats.map((stat) => (
          <div
            key={stat.label}
            className="p-4 rounded-lg bg-gray-800/50 hover:bg-gray-800 transition-all duration-300 border border-gray-700/50 hover:border-gray-600"
          >
            <div className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">
              {stat.label}
            </div>
            <div className={`${getHighlightClasses(stat.highlight, stat.size)} transition-colors duration-300`}>
              {stat.value}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
