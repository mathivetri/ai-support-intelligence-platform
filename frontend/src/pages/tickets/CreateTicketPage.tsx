import { useNavigate } from 'react-router-dom'
import { useCreateTicket } from '@/hooks/useTickets'
import TicketForm from '@/components/tickets/TicketForm'
import type { TicketCreate } from '@/types/ticket'

export default function CreateTicketPage() {
  const navigate = useNavigate()
  const create = useCreateTicket()

  const handleSubmit = (payload: TicketCreate) => {
    create.mutate(payload, {
      onSuccess: (ticket) => navigate(`/tickets/${ticket.id}`),
    })
  }

  return (
    <div className="mx-auto max-w-2xl p-6">
      <h1 className="mb-4 text-2xl font-bold text-gray-900">New Ticket</h1>
      <TicketForm
        onSubmit={handleSubmit}
        isSubmitting={create.isPending}
        error={create.isError ? 'Failed to create ticket. Check your input.' : undefined}
      />
    </div>
  )
}
