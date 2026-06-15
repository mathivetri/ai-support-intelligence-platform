import { apiClient } from '@/services/apiClient'
import type {
  Ticket,
  TicketCreate,
  TicketUpdate,
  TicketListResponse,
} from '@/types/ticket'

async function list(page = 1, size = 10): Promise<TicketListResponse> {
  const { data } = await apiClient.get<TicketListResponse>('/tickets/', {
    params: { page, size },
  })
  return data
}

async function get(id: string): Promise<Ticket> {
  const { data } = await apiClient.get<Ticket>(`/tickets/${id}`)
  return data
}

async function create(payload: TicketCreate): Promise<Ticket> {
  const { data } = await apiClient.post<Ticket>('/tickets/', payload)
  return data
}

async function update(id: string, payload: TicketUpdate): Promise<Ticket> {
  const { data } = await apiClient.patch<Ticket>(`/tickets/${id}`, payload)
  return data
}

async function remove(id: string): Promise<void> {
  await apiClient.delete(`/tickets/${id}`)
}

export const ticketService = { list, get, create, update, remove }
