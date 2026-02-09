import type { CompanyOverview } from '../../types/stock';
import { formatLargeNumber, formatCurrency, formatNumber, formatPercent } from '../../utils/formatting';

interface Props {
  company: CompanyOverview;
}

export default function QuickStats({ company }: Props) {
  const stats = [
    { label: 'Market Cap', value: formatLargeNumber(company.market_cap) },
    { label: 'P/E Ratio', value: company.pe_ratio?.toFixed(2) ?? 'N/A' },
    { label: 'Fwd P/E', value: company.forward_pe?.toFixed(2) ?? 'N/A' },
    { label: 'Volume', value: formatLargeNumber(company.volume) },
    { label: 'Avg Volume', value: formatLargeNumber(company.avg_volume) },
    { label: 'Day Range', value: company.day_low && company.day_high ? `${formatCurrency(company.day_low)} - ${formatCurrency(company.day_high)}` : 'N/A' },
    { label: '52W Range', value: company.fifty_two_week_low && company.fifty_two_week_high ? `${formatCurrency(company.fifty_two_week_low)} - ${formatCurrency(company.fifty_two_week_high)}` : 'N/A' },
    { label: 'Beta', value: company.beta?.toFixed(2) ?? 'N/A' },
    { label: 'Div Yield', value: company.dividend_yield != null ? formatPercent(company.dividend_yield * 100) : 'N/A' },
  ];

  return (
    <div className="card">
      <h3 className="card-header">Quick Stats</h3>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {stats.map((stat) => (
          <div key={stat.label}>
            <div className="text-xs text-gray-500 uppercase">{stat.label}</div>
            <div className="text-sm font-medium text-white mt-0.5">{stat.value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
