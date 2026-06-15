import type { TicketSentiment } from '@/types/ticket'

const STYLES: Record<TicketSentiment, string> = {
  positive: 'bg-green-100 text-green-800',
  neutral: 'bg-gray-100 text-gray-700',
  negative: 'bg-red-100 text-red-800',
}

export default function SentimentBadge({
  sentiment,
}: {
  sentiment: TicketSentiment | null
}) {
  if (!sentiment) {
    return (
      <span className="inline-block rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-400">
        Unclassified
      </span>
    )
  }
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium capitalize ${STYLES[sentiment]}`}
    >
      {sentiment}
    </span>
  )
}
