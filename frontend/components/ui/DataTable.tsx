'use client'

import { useMemo, useState } from 'react'

export interface Column<T> {
  key: string
  label: string
  align: 'left' | 'right'
  render: (r: T) => React.ReactNode
  /** Columns without sortValue are not sortable. */
  sortValue?: (r: T) => string | number | null
  /** Applied to the body <td> only. */
  cellStyle?: (r: T) => React.CSSProperties
}

type Dir = 'asc' | 'desc'

interface Props<T> {
  rows: T[]
  rowKey: (r: T) => string
  columns: Column<T>[]
  caption: string
  defaultSort: { key: string; dir: Dir }
  stickyFirstColumn?: boolean
}

function compare(a: string | number, b: string | number): number {
  if (typeof a === 'number' && typeof b === 'number') return a - b
  return String(a).localeCompare(String(b))
}

export function DataTable<T>({
  rows,
  rowKey,
  columns,
  caption,
  defaultSort,
  stickyFirstColumn = false,
}: Props<T>) {
  const [sort, setSort] = useState(defaultSort)

  const sorted = useMemo(() => {
    const col = columns.find((c) => c.key === sort.key)
    const get = col?.sortValue
    if (!get) return rows
    const sign = sort.dir === 'asc' ? 1 : -1
    return [...rows].sort((x, y) => {
      const a = get(x)
      const b = get(y)
      const aNull = a === null || a === undefined || (typeof a === 'number' && Number.isNaN(a))
      const bNull = b === null || b === undefined || (typeof b === 'number' && Number.isNaN(b))
      if (aNull && bNull) return 0
      if (aNull) return 1 // nulls last regardless of direction
      if (bNull) return -1
      return sign * compare(a as string | number, b as string | number)
    })
  }, [rows, columns, sort])

  function toggle(key: string) {
    setSort((s) => (s.key === key ? { key, dir: s.dir === 'asc' ? 'desc' : 'asc' } : { key, dir: 'desc' }))
  }

  const stickyHead = (i: number) =>
    stickyFirstColumn && i === 0 ? 'sticky left-0 z-30 bg-gray-50' : ''
  const stickyCell = (i: number) =>
    stickyFirstColumn && i === 0 ? 'sticky left-0 z-10 bg-white' : ''

  return (
    <div className="overflow-auto max-h-[80vh] rounded-lg border border-gray-200">
      <table className="min-w-full text-sm text-gray-900">
        <caption className="sr-only">{caption}</caption>
        <thead className="sticky top-0 z-20 bg-gray-50">
          <tr>
            {columns.map((c, i) => {
              const active = sort.key === c.key && !!c.sortValue
              const ariaSort = active ? (sort.dir === 'asc' ? 'ascending' : 'descending') : undefined
              return (
                <th
                  key={c.key}
                  scope="col"
                  aria-sort={ariaSort}
                  className={`px-3 py-2 font-semibold text-gray-700 whitespace-nowrap bg-gray-50 ${
                    c.align === 'right' ? 'text-right' : 'text-left'
                  } ${stickyHead(i)}`}
                >
                  {c.sortValue ? (
                    <button
                      type="button"
                      onClick={() => toggle(c.key)}
                      className="inline-flex items-center gap-1 hover:text-gray-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
                    >
                      {c.label}
                      <span aria-hidden="true" className="text-xs text-gray-400">
                        {active ? (sort.dir === 'asc' ? '▲' : '▼') : '↕'}
                      </span>
                    </button>
                  ) : (
                    c.label
                  )}
                </th>
              )
            })}
          </tr>
        </thead>
        <tbody>
          {sorted.map((r) => (
            <tr key={rowKey(r)} className="border-t border-gray-100">
              {columns.map((c, i) => (
                <td
                  key={c.key}
                  style={c.cellStyle?.(r)}
                  className={`px-3 py-2 text-gray-900 whitespace-nowrap ${
                    c.align === 'right' ? 'text-right tabular-nums' : 'text-left'
                  } ${stickyCell(i)}`}
                >
                  {c.render(r)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
