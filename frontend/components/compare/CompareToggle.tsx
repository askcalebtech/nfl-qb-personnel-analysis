'use client'

interface Props {
  open: boolean
  onToggle: () => void
}

export default function CompareToggle({ open, onToggle }: Props) {
  return (
    <button
      onClick={onToggle}
      className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium border transition-colors ${
        open
          ? 'bg-blue-600 text-white border-blue-600 hover:bg-blue-700'
          : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
      }`}
    >
      {open ? 'Close Comparison' : 'Compare QBs'}
    </button>
  )
}