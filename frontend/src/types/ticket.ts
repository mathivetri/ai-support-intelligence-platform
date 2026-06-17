// types/ticket.ts — Ticket shape + status/priority/sentiment enums (AI fields nullable).
// Enums — mirror backend (stored as strings)
export type TicketStatus = 'open' | 'in_progress' | 'resolved' | 'closed'
export type TicketPriority = 'low' | 'medium' | 'high' | 'critical'
export type TicketSentiment = 'positive' | 'neutral' | 'negative'

// Full ticket — TicketResponse (AI fields are nullable until enriched)
export interface Ticket {
  id: string
  title: string
  description: string
  status: TicketStatus
  priority: TicketPriority | null
  ai_summary: string | null
  sentiment: TicketSentiment | null
  screenshot_url: string | null
  owner_id: string
  created_at: string
  updated_at: string
}

// Create payload — TicketCreate
export interface TicketCreate {
  title: string
  description: string
  status?: TicketStatus   // defaults to "open" on the backend
}

// Update payload — TicketUpdate (all optional)
export interface TicketUpdate {
  title?: string
  description?: string
  status?: TicketStatus
  priority?: TicketPriority
  ai_summary?: string
  sentiment?: TicketSentiment
}

// Paginated list — TicketListResponse
export interface TicketListResponse {
  items: Ticket[]
  total: number
  page: number
  size: number
  pages: number
}
