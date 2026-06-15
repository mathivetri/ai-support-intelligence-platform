import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ROUTES } from '@/routes/constants'
import { useTickets } from '@/hooks/useTickets'
import Loader from '@/components/common/Loader'
import EmptyState from '@/components/common/EmptyState'
import StatusBadge from '@/components/tickets/StatusBadge'
import PriorityBadge from '@/components/tickets/PriorityBadge'
import SentimentBadge from '@/components/tickets/SentimentBadge'
<Link to={ROUTES.TICKET_NEW} className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white">
  New ticket
</Link>

export default function TicketsPage() {
  const [page, setPage] = useState(1)
  const size = 10
  const { data, isLoading, isError } = useTickets(page, size)

  if (isLoading) return <Loader label="Loading tickets…" />
  if (isError) return <div className="p-8 text-red-600">Failed to load tickets.</div>

  const tickets = data?.items ?? []

  if (tickets.length === 0) {
    return (
      <EmptyState
        title="No tickets yet"
        description="Create your first support ticket to get started."
      />
    )
  }

  return (
    <div className="mx-auto max-w-4xl p-6">
      <h1 className="mb-4 text-2xl font-bold text-gray-900">Tickets</h1>

      <ul className="space-y-3">
        {tickets.map((t) => (
          <li key={t.id}>
            <Link
              to={`/tickets/${t.id}`}
              className="block rounded-lg border bg-white p-4 shadow-sm hover:bg-gray-50"
            >
              <div className="flex items-center justify-between">
                <span className="font-medium text-gray-900">{t.title}</span>
                <StatusBadge status={t.status} />
              </div>
              <div className="mt-2 flex items-center gap-2">
                <PriorityBadge priority={t.priority} />
                <SentimentBadge sentiment={t.sentiment} />
                <span className="ml-auto text-xs text-gray-400">
                  {new Date(t.created_at).toLocaleDateString()}
                </span>
              </div>
            </Link>
          </li>
        ))}
      </ul>

      <div className="mt-6 flex items-center justify-center gap-4">
        <button
          onClick={() => setPage((p) => Math.max(1, p - 1))}
          disabled={page <= 1}
          className="rounded border px-3 py-1 text-sm disabled:opacity-50"
        >
          Previous
        </button>
        <span className="text-sm text-gray-600">
          Page {data?.page} of {data?.pages}
        </span>
        <button
          onClick={() => setPage((p) => p + 1)}
          disabled={!!data && page >= data.pages}
          className="rounded border px-3 py-1 text-sm disabled:opacity-50"
        >
          Next
        </button>
      </div>
    </div>
  )
}
