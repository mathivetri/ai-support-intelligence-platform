import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'

// positive, neutral, negative, unclassified
const COLORS = ['#22c55e', '#9ca3af', '#ef4444', '#d1d5db']

export default function SentimentChart({ data }: { data: Record<string, number> }) {
  const chartData = Object.entries(data).map(([name, value]) => ({ name, value }))
  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm">
      <h3 className="mb-2 text-sm font-semibold text-gray-700">Tickets by Sentiment</h3>
      <ResponsiveContainer width="100%" height={240}>
        <PieChart>
          <Pie data={chartData} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={50} outerRadius={80}>
            {chartData.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
