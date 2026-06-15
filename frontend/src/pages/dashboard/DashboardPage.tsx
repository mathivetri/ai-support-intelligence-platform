import { useAnalyticsOverview } from '@/hooks/useAnalytics'
import Loader from '@/components/common/Loader'
import StatCard from '@/components/analytics/StatCard'
import PriorityChart from '@/components/analytics/PriorityChart'
import SentimentChart from '@/components/analytics/SentimentChart'

export default function DashboardPage() {
  const { data, isLoading, isError } = useAnalyticsOverview()

  if (isLoading) return <Loader label="Loading analytics…" />
  if (isError || !data)
    return <div className="p-8 text-red-600">Failed to load analytics.</div>

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard label="Total Tickets" value={data.total_tickets} />
        <StatCard label="Open" value={data.open_tickets} />
        <StatCard label="Resolved" value={data.resolved_tickets} />
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <PriorityChart data={data.tickets_by_priority} />
        <SentimentChart data={data.tickets_by_sentiment} />
      </div>
    </div>
  )
}
