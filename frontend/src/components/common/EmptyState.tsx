import type { ReactNode } from 'react'

export default function EmptyState({
  title = 'Nothing here yet',
  description,
  action,
}: {
  title?: string
  description?: string
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 p-12 text-center">
      <p className="text-lg font-medium text-gray-700">{title}</p>
      {description && <p className="text-sm text-gray-500">{description}</p>}
      {action}
    </div>
  )
}
