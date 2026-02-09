export function isMarketOpen(): boolean {
  const now = new Date();
  const utcDay = now.getUTCDay();
  const utcHour = now.getUTCHours();

  // Weekend
  if (utcDay === 0 || utcDay === 6) return false;

  // US market: 9:30-16:00 ET = ~14:30-21:00 UTC
  return utcHour >= 14 && utcHour < 21;
}

export function getRefreshInterval(): number {
  return isMarketOpen() ? 60_000 : 300_000; // 1min market, 5min off
}
