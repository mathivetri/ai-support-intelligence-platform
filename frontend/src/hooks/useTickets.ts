import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ticketService } from '@/services/ticketService'
import type { TicketCreate, TicketUpdate } from '@/types/ticket'

// ── Queries ──────────────────────────────────────────────────────────
export function useTickets(page = 1, size = 10) {
  return useQuery({
    queryKey: ['tickets', page, size],
    queryFn: () => ticketService.list(page, size),
  })
}

export function useTicket(id: string) {
  return useQuery({
    queryKey: ['ticket', id],
    queryFn: () => ticketService.get(id),
    enabled: !!id, // don't fire until an id exists
  })
}

// ── Mutations ────────────────────────────────────────────────────────
export function useCreateTicket() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      payload,
      screenshot,
    }: {
      payload: TicketCreate
      screenshot?: File | null
    }) => ticketService.create(payload, screenshot),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tickets'] })
    },
  })
}

export function useUpdateTicket() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: TicketUpdate }) =>
      ticketService.update(id, payload),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ['tickets'] })
      qc.invalidateQueries({ queryKey: ['ticket', variables.id] })
    },
  })
}

export function useDeleteTicket() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => ticketService.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tickets'] })
    },
  })
}
