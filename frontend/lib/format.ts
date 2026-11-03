export function fmt(v: number | null, decimals = 1, sign = false): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '—'
  const s = v.toFixed(decimals)
  return sign && v > 0 ? `+${s}` : s
}

/** Probability (0-1) as a whole percent. */
export function pct(p: number | null): string {
  if (p === null || p === undefined || Number.isNaN(p)) return '—'
  if (p > 0 && p < 0.005) return '<1%'
  return `${Math.round(p * 100)}%`
}

/** "Packers by 2.8"; the caller picks the favorite's name. */
export function marginLabel(name: string, margin: number): string {
  return `${name} by ${Math.abs(margin).toFixed(1)}`
}
