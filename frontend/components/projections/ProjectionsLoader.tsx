'use client'

import { useCallback, useEffect, useState } from 'react'
import { ProjectionsView } from './ProjectionsView'
import type { ProjectionsData } from '@/types'

export function ProjectionsLoader() {
  const [data, setData] = useState<ProjectionsData | null>(null)
  const [failed, setFailed] = useState(false)

  const load = useCallback(() => {
    setFailed(false)
    setData(null)
    fetch('/data/projections.json', { cache: 'no-cache' })
      .then((r) => {
        if (!r.ok) throw new Error(String(r.status))
        return r.json() as Promise<ProjectionsData>
      })
      .then(setData)
      .catch(() => setFailed(true))
  }, [])

  useEffect(load, [load])

  if (failed) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div role="alert" className="rounded border border-red-300 bg-red-50 p-4 text-sm text-red-900">
          <p className="mb-2">The projections couldn&apos;t be loaded.</p>
          <button
            type="button"
            onClick={load}
            className="rounded bg-red-800 px-3 py-1.5 font-medium text-white hover:bg-red-900"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }
  if (!data) {
    return (
      <div role="status" className="py-24 text-center text-sm text-gray-700">
        Loading projections...
      </div>
    )
  }
  return <ProjectionsView data={data} />
}
