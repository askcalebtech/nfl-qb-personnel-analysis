'use client'

import { scopeToParam, type Scope } from '@/lib/projections'
import type { ProjectionTeam } from '@/types'

interface Props {
  teams: ProjectionTeam[]
  scope: Scope
  onChange: (param: string | null) => void
}

const uniq = (xs: string[]) => Array.from(new Set(xs)).sort()

export function ScopeFilter({ teams, scope, onChange }: Props) {
  return (
    <div>
      <label htmlFor="scope-select" className="mb-1 block text-sm font-medium text-gray-700">
        Show
      </label>
      <select
        id="scope-select"
        value={scopeToParam(scope) ?? ''}
        onChange={(e) => onChange(e.target.value || null)}
        className="w-full max-w-sm rounded border border-gray-300 bg-white px-3 py-2 text-gray-900"
      >
        <option value="">All teams</option>
        <optgroup label="Conferences">
          {uniq(teams.map((t) => t.conference)).map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </optgroup>
        <optgroup label="Divisions">
          {uniq(teams.map((t) => t.division)).map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </optgroup>
        <optgroup label="Teams">
          {[...teams].sort((a, b) => a.name.localeCompare(b.name)).map((t) => (
            <option key={t.team} value={t.team}>{t.name}</option>
          ))}
        </optgroup>
      </select>
    </div>
  )
}
