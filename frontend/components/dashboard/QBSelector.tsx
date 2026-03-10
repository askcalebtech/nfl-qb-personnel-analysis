'use client'

import { useState, useRef, useEffect } from 'react'
import type { QB } from '@/types'

interface Props {
  qbs: QB[]
  selectedId: string
  onChange: (id: string) => void
}

export default function QBSelector({ qbs, selectedId, onChange }: Props) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const [showAll, setShowAll] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  const selected = qbs.find((q) => q.qb_id === selectedId)

  // When searching, look across all QBs so typing a name always finds them.
  // When not searching, respect the showAll toggle.
  const baseList = search.trim() ? qbs : qbs.filter((q) => showAll || q.is_starter)
  const filtered = search.trim()
    ? baseList.filter((q) => (q.qb_name ?? '').toLowerCase().includes(search.toLowerCase()))
    : baseList

  const starterCount = qbs.filter((q) => q.is_starter).length

  useEffect(() => {
    function onMouseDown(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
        setSearch('')
      }
    }
    document.addEventListener('mousedown', onMouseDown)
    return () => document.removeEventListener('mousedown', onMouseDown)
  }, [])

  function select(id: string) {
    onChange(id)
    setOpen(false)
    setSearch('')
  }

  return (
    <div className="flex flex-col gap-1" ref={ref}>
      <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">
        Quarterback
      </label>
      <div className="relative">
        <button
          onClick={() => setOpen((v) => !v)}
          className="w-full min-w-[220px] border border-gray-300 rounded-md px-3 py-2 text-sm bg-white shadow-sm text-left flex items-center justify-between gap-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <span className="text-gray-800">{selected?.qb_name ?? selectedId}</span>
          <span className="text-gray-400 text-xs">▾</span>
        </button>

        {open && (
          <div className="absolute z-50 mt-1 min-w-[220px] w-full bg-white border border-gray-200 rounded-md shadow-lg">
            <div className="p-2 border-b border-gray-100">
              <input
                autoFocus
                type="text"
                placeholder="Search QBs…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full px-2 py-1.5 text-sm border border-gray-200 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <ul className="max-h-64 overflow-y-auto">
              {filtered.map((qb) => (
                <li
                  key={qb.qb_id}
                  onClick={() => select(qb.qb_id)}
                  className={`px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 ${
                    selectedId === qb.qb_id ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-800'
                  }`}
                >
                  {qb.qb_name ?? qb.qb_id}
                  <span className="ml-1 text-gray-400 text-xs">({qb.career_plays ?? 0})</span>
                </li>
              ))}
              {filtered.length === 0 && (
                <li className="px-3 py-2 text-sm text-gray-500">No QBs found</li>
              )}
              {!showAll && !search.trim() && (
                <li
                  onClick={() => setShowAll(true)}
                  className="px-3 py-2 text-xs text-blue-600 cursor-pointer hover:bg-gray-50 border-t border-gray-100 font-medium"
                >
                  Show all QBs ({qbs.length - starterCount} more)
                </li>
              )}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}
