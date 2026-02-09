export function getGradeColor(grade: string): string {
  if (grade.startsWith('A')) return 'text-green-400';
  if (grade.startsWith('B')) return 'text-emerald-400';
  if (grade.startsWith('C')) return 'text-yellow-400';
  if (grade.startsWith('D')) return 'text-orange-400';
  if (grade.startsWith('F')) return 'text-red-400';
  return 'text-gray-400';
}

export function getGradeBgColor(grade: string): string {
  if (grade.startsWith('A')) return 'bg-green-500/20 border-green-500/30';
  if (grade.startsWith('B')) return 'bg-emerald-500/20 border-emerald-500/30';
  if (grade.startsWith('C')) return 'bg-yellow-500/20 border-yellow-500/30';
  if (grade.startsWith('D')) return 'bg-orange-500/20 border-orange-500/30';
  if (grade.startsWith('F')) return 'bg-red-500/20 border-red-500/30';
  return 'bg-gray-500/20 border-gray-500/30';
}

export function getSignalColor(signal: string): string {
  switch (signal) {
    case 'STRONG BUY': return 'text-green-400 bg-green-500/20 border-green-500/40';
    case 'BUY': return 'text-emerald-400 bg-emerald-500/20 border-emerald-500/40';
    case 'HOLD': return 'text-yellow-400 bg-yellow-500/20 border-yellow-500/40';
    case 'SELL': return 'text-orange-400 bg-orange-500/20 border-orange-500/40';
    case 'STRONG SELL': return 'text-red-400 bg-red-500/20 border-red-500/40';
    default: return 'text-gray-400 bg-gray-500/20 border-gray-500/40';
  }
}

export function getScoreColor(score: number): string {
  if (score >= 80) return '#22c55e';
  if (score >= 65) return '#4ade80';
  if (score >= 45) return '#eab308';
  if (score >= 30) return '#f97316';
  return '#ef4444';
}
