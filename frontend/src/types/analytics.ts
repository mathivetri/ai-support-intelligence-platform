// types/analytics.ts — analytics overview/sentiment/priority shapes.
// Mirrors backend TicketAnalytics (GET /api/v1/analytics/overview)
export interface TicketAnalytics {
  total_tickets: number
  open_tickets: number
  resolved_tickets: number
  // keyed by priority/sentiment value, plus an "unclassified" bucket; always present, default 0
  tickets_by_priority: Record<string, number>
  tickets_by_sentiment: Record<string, number>
}
