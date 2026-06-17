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

async function create(
  payload: TicketCreate,
  screenshot?: File | null,
): Promise<Ticket> {
  // The create endpoint accepts multipart/form-data so an optional screenshot
  // can ride along. Axios sets the multipart boundary automatically for FormData.
  const form = new FormData()
  form.append('title', payload.title)
  form.append('description', payload.description)
  if (screenshot) form.append('screenshot', screenshot)

  const { data } = await apiClient.post<Ticket>('/tickets/', form)
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
