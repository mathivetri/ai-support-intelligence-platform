import type { TicketPriority } from '@/types/ticket'

const STYLES: Record<TicketPriority, string> = {
  low: 'bg-gray-100 text-gray-700',
  medium: 'bg-blue-100 text-blue-800',
  high: 'bg-orange-100 text-orange-800',
  critical: 'bg-red-100 text-red-800',
}

export default function PriorityBadge({
  priority,
}: {
  priority: TicketPriority | null
}) {
  if (!priority) {
    return (
      <span className="inline-block rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-400">
        Unclassified
      </span>
    )
  }
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium capitalize ${STYLES[priority]}`}
    >
      {priority}
    </span>
  )
}
