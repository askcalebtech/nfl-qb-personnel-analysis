import { describe, expect, test } from 'vitest'
import { fmt, pct, marginLabel } from '@/lib/format'

describe('format', () => {
  test('pct: 0.003 shows <1%, null shows —', () => {
    expect(pct(0.003)).toBe('<1%')
    expect(pct(null)).toBe('—')
    expect(pct(0)).toBe('0%')
    expect(pct(0.373)).toBe('37%')
  })
  test('marginLabel uses one decimal', () => {
    expect(marginLabel('Packers', 2.84)).toBe('Packers by 2.8')
    expect(marginLabel('Packers', -2.84)).toBe('Packers by 2.8')
  })
  test('fmt handles null, decimals and sign', () => {
    expect(fmt(null)).toBe('—')
    expect(fmt(1.234, 1)).toBe('1.2')
    expect(fmt(1.234, 2, true)).toBe('+1.23')
    expect(fmt(-1.234, 1, true)).toBe('-1.2')
  })
})
