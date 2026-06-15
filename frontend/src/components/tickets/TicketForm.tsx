import { useState, type FormEvent } from 'react'
import type { TicketCreate } from '@/types/ticket'

export default function TicketForm({
  onSubmit,
  isSubmitting,
  error,
}: {
  onSubmit: (payload: TicketCreate) => void
  isSubmitting: boolean
  error?: string
}) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    onSubmit({ title: title.trim(), description: description.trim() })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">Title</label>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          minLength={5}
          maxLength={255}
          required
          className="w-full rounded border px-3 py-2"
          placeholder="Short summary (5–255 chars)"
        />
      </div>

      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">Description</label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          minLength={20}
          maxLength={5000}
          required
          rows={6}
          className="w-full rounded border px-3 py-2"
          placeholder="Full description (20–5000 chars)"
        />
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <button
        type="submit"
        disabled={isSubmitting}
        className="rounded bg-blue-600 px-4 py-2 font-medium text-white disabled:opacity-50"
      >
        {isSubmitting ? 'Creating…' : 'Create ticket'}
      </button>
    </form>
  )
}
