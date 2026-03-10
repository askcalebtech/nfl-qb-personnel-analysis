'use client'

export type Season = '2022' | '2023' | '2024' | '2025' | '2022–25'

const SEASONS: Season[] = ['2022', '2023', '2024', '2025', '2022–25']

interface Props {
  selected: Season
  onChange: (s: Season) => void
}

export default function SeasonFilter({ selected, onChange }: Props) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Season</label>
      <div className="flex gap-1">
        {SEASONS.map((s) => (
          <button
            key={s}
            onClick={() => onChange(s)}
            className={`px-3 py-1.5 rounded text-sm font-medium border transition-colors ${
              selected === s
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
            }`}
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  )
}
