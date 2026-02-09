import type { CompanyOverview } from '../../types/stock';
import { formatCurrency, formatLargeNumber, formatPercent } from '../../utils/formatting';

interface Props {
  company: CompanyOverview;
}

export default function CompanyHeader({ company }: Props) {
  const isPositive = (company.change ?? 0) >= 0;

  return (
    <div className="card mb-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-bold text-white">{company.ticker}</h2>
            <span className="text-gray-400 text-lg">{company.name}</span>
          </div>
          <div className="flex items-center gap-3 mt-1 text-sm text-gray-500">
            {company.sector && <span>{company.sector}</span>}
            {company.industry && (
              <>
                <span>|</span>
                <span>{company.industry}</span>
              </>
            )}
          </div>
        </div>
        <div className="text-right">
          <div className="text-3xl font-bold text-white">
            {formatCurrency(company.price)}
          </div>
          <div className={`text-lg font-medium ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
            {isPositive ? '+' : ''}{formatCurrency(company.change)}{' '}
            ({isPositive ? '+' : ''}{formatPercent(company.change_percent)})
          </div>
        </div>
      </div>
    </div>
  );
}
