// Colorblind-safe diverging scale: orange (negative) <- white (0) -> blue (positive).
const BLUE: [number, number, number] = [33, 102, 172]
const ORANGE: [number, number, number] = [230, 97, 1]
const WHITE: [number, number, number] = [255, 255, 255]

function lum([r, g, b]: [number, number, number]): number {
  const f = (c: number) => {
    const s = c / 255
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4)
  }
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
}

function contrast(a: [number, number, number], b: [number, number, number]): number {
  const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x)
  return (hi + 0.05) / (lo + 0.05)
}

export function heatStyle(value: number, maxAbs: number): { backgroundColor: string; color: string } {
  const t = maxAbs > 0 ? Math.max(-1, Math.min(1, value / maxAbs)) : 0
  const target = t >= 0 ? BLUE : ORANGE
  const a = Math.abs(t)
  const bg = WHITE.map((w, i) => Math.round(w + (target[i] - w) * a)) as [number, number, number]
  const black: [number, number, number] = [0, 0, 0]
  const color = contrast(bg, black) >= contrast(bg, WHITE) ? '#000000' : '#ffffff'
  return { backgroundColor: `rgb(${bg[0]}, ${bg[1]}, ${bg[2]})`, color }
}
