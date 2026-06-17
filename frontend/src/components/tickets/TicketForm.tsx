import { useState, type FormEvent, type ChangeEvent } from 'react'
import type { TicketCreate } from '@/types/ticket'

const MAX_SCREENSHOT_BYTES = 5 * 1024 * 1024 // 5 MB — matches the backend limit

export default function TicketForm({
  onSubmit,
  isSubmitting,
  error,
}: {
  onSubmit: (payload: TicketCreate, screenshot: File | null) => void
  isSubmitting: boolean
  error?: string
}) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [screenshot, setScreenshot] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [fileError, setFileError] = useState<string | null>(null)

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null
    setFileError(null)

    if (file && file.size > MAX_SCREENSHOT_BYTES) {
      setFileError('Image is too large (max 5 MB).')
      setScreenshot(null)
      setPreview(null)
      return
    }

    setScreenshot(file)
    setPreview(file ? URL.createObjectURL(file) : null)
  }

  const clearFile = () => {
    setScreenshot(null)
    setPreview(null)
    setFileError(null)
  }

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    onSubmit({ title: title.trim(), description: description.trim() }, screenshot)
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

      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700">
          Screenshot <span className="font-normal text-gray-400">(optional)</span>
        </label>
        <input
          type="file"
          accept="image/png,image/jpeg,image/webp,image/gif"
          onChange={handleFileChange}
          className="block w-full text-sm text-gray-600 file:mr-3 file:rounded file:border-0 file:bg-blue-50 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-blue-700 hover:file:bg-blue-100"
        />
        {fileError && <p className="mt-1 text-sm text-red-600">{fileError}</p>}

        {preview && (
          <div className="mt-3">
            <img
              src={preview}
              alt="Screenshot preview"
              className="max-h-48 rounded border"
            />
            <button
              type="button"
              onClick={clearFile}
              className="mt-1 text-sm text-gray-500 hover:underline"
            >
              Remove
            </button>
          </div>
        )}
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
