import { describe, expect, test } from 'vitest'
import { heatStyle } from '@/lib/heat'

function rgb(s: string): [number, number, number] {
  const m = s.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/)
  if (m) return [+m[1], +m[2], +m[3]]
  const h = s.replace('#', '')
  return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16)) as [number, number, number]
}
function lum([r, g, b]: [number, number, number]) {
  const f = (c: number) => {
    const s = c / 255
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4)
  }
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)
}
function contrast(a: string, b: string) {
  const [l1, l2] = [lum(rgb(a)), lum(rgb(b))].sort((x, y) => y - x)
  return (l1 + 0.05) / (l2 + 0.05)
}

describe('heatStyle', () => {
  test('heatStyle: contrast is at least 4.5:1 at -max, 0 and +max', () => {
    for (const v of [-5, -3.7, -2, -0.5, 0, 0.5, 2, 3.7, 5]) {
      const s = heatStyle(v, 5)
      expect(contrast(s.backgroundColor, s.color)).toBeGreaterThanOrEqual(4.5)
    }
  })
  test('heatStyle: never returns plain red or green hues', () => {
    for (const v of [-5, -4, -2.5, -1, 1, 2.5, 4, 5]) {
      const [r, g, b] = rgb(heatStyle(v, 5).backgroundColor)
      expect(g > r && g > b).toBe(false)
      expect(r > 200 && g < 80 && b < 80).toBe(false)
    }
  })
  test('white at zero, neutral when maxAbs is 0', () => {
    expect(rgb(heatStyle(0, 5).backgroundColor)).toEqual([255, 255, 255])
    expect(rgb(heatStyle(3, 0).backgroundColor)).toEqual([255, 255, 255])
  })
  test('positive is bluer, negative is oranger', () => {
    const [pr, , pb] = rgb(heatStyle(5, 5).backgroundColor)
    const [nr, , nb] = rgb(heatStyle(-5, 5).backgroundColor)
    expect(pb).toBeGreaterThan(pr)
    expect(nr).toBeGreaterThan(nb)
  })
})
