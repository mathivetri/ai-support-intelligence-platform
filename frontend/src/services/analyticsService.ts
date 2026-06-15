import { apiClient } from '@/services/apiClient'
import type { TicketAnalytics } from '@/types/analytics'

async function getOverview(): Promise<TicketAnalytics> {
  const { data } = await apiClient.get<TicketAnalytics>('/analytics/overview')
  return data
}

export const analyticsService = { getOverview }
