import { useParams, useNavigate } from 'react-router-dom'
import { useTicket, useDeleteTicket } from '@/hooks/useTickets'
import Loader from '@/components/common/Loader'
import StatusBadge from '@/components/tickets/StatusBadge'
import PriorityBadge from '@/components/tickets/PriorityBadge'
import SentimentBadge from '@/components/tickets/SentimentBadge'
import { ROUTES } from '@/routes/constants'

export default function TicketDetailPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const { data: ticket, isLoading, isError } = useTicket(id)
  const del = useDeleteTicket()

  if (isLoading) return <Loader label="Loading ticket…" />
  if (isError || !ticket)
    return <div className="p-8 text-red-600">Ticket not found.</div>

  const handleDelete = () => {
    if (!confirm('Delete this ticket?')) return
    del.mutate(id, { onSuccess: () => navigate(ROUTES.TICKETS) })
  }

  const aiPending =
    ticket.ai_summary === null &&
    ticket.priority === null &&
    ticket.sentiment === null

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6">
      <button
        onClick={() => navigate(ROUTES.TICKETS)}
        className="text-sm text-gray-500 hover:underline"
      >
        ← Back to tickets
      </button>

      <div className="flex items-start justify-between gap-4">
        <h1 className="text-2xl font-bold text-gray-900">{ticket.title}</h1>
        <StatusBadge status={ticket.status} />
      </div>

      <p className="whitespace-pre-wrap text-gray-700">{ticket.description}</p>

      {/* AI analysis panel */}
      <section className="rounded-lg border bg-gray-50 p-4">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
          AI Analysis
        </h2>
        {aiPending ? (
          <p className="text-sm text-gray-400">
            Not yet analyzed — AI enrichment runs shortly after creation.
          </p>
        ) : (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <PriorityBadge priority={ticket.priority} />
              <SentimentBadge sentiment={ticket.sentiment} />
            </div>
            {ticket.ai_summary && (
              <p className="text-sm text-gray-700">{ticket.ai_summary}</p>
            )}
          </div>
        )}
      </section>

      <div className="flex gap-3">
        <button
          onClick={handleDelete}
          disabled={del.isPending}
          className="rounded bg-red-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {del.isPending ? 'Deleting…' : 'Delete'}
        </button>
      </div>
    </div>
  )
}
