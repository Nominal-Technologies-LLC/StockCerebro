export function formatNumber(value: number | null | undefined): string {
  if (value == null) return 'N/A';
  return value.toLocaleString('en-US', { maximumFractionDigits: 2 });
}

export function formatCurrency(value: number | null | undefined): string {
  if (value == null) return 'N/A';
  return '$' + value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function formatLargeNumber(value: number | null | undefined): string {
  if (value == null) return 'N/A';
  const abs = Math.abs(value);
  if (abs >= 1e12) return (value / 1e12).toFixed(2) + 'T';
  if (abs >= 1e9) return (value / 1e9).toFixed(2) + 'B';
  if (abs >= 1e6) return (value / 1e6).toFixed(2) + 'M';
  if (abs >= 1e3) return (value / 1e3).toFixed(1) + 'K';
  return value.toFixed(2);
}

export function formatPercent(value: number | null | undefined): string {
  if (value == null) return 'N/A';
  return value.toFixed(2) + '%';
}

export function formatRatio(value: number | null | undefined): string {
  if (value == null) return 'N/A';
  return value.toFixed(2);
}
