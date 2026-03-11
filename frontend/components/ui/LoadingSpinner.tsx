export default function LoadingSpinner() {
  return (
    <div className="flex flex-col items-center justify-center py-24 gap-4">
      <div className="w-8 h-8 border-4 border-gray-200 border-t-blue-500 rounded-full animate-spin" />
      <p className="text-sm text-gray-500 text-center">
        Loading data... (first load may take up to 60 seconds while the server wakes up)
      </p>
    </div>
  )
}
