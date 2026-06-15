import { useQuery } from '@tanstack/react-query'
import { analyticsService } from '@/services/analyticsService'

export function useAnalyticsOverview() {
  return useQuery({
    queryKey: ['analytics', 'overview'],
    queryFn: () => analyticsService.getOverview(),
  })
}

