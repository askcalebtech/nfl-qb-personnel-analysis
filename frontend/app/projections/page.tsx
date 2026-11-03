import { Suspense } from 'react'
import { ProjectionsLoader } from '@/components/projections/ProjectionsLoader'

export default function ProjectionsPage() {
  return (
    <Suspense fallback={<div role="status" className="py-24 text-center text-sm text-gray-700">Loading projections...</div>}>
      <ProjectionsLoader />
    </Suspense>
  )
}
