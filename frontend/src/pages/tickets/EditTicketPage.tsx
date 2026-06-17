import { useEffect, useState, type ChangeEvent, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  useTicket,
  useUpdateTicket,
  useUpdateScreenshot,
  useRemoveScreenshot,
} from '@/hooks/useTickets'
import Loader from '@/components/common/Loader'

const MAX_SCREENSHOT_BYTES = 5 * 1024 * 1024 // 5 MB — matches the backend limit

export default function EditTicketPage() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const { data: ticket, isLoading, isError } = useTicket(id)

  const update = useUpdateTicket()
  const updateShot = useUpdateScreenshot()
  const removeShot = useRemoveScreenshot()

  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [newFile, setNewFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [removeExisting, setRemoveExisting] = useState(false)
  const [fileError, setFileError] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Pre-fill the form once the ticket loads.
  useEffect(() => {
    if (ticket) {
      setTitle(ticket.title)
      setDescription(ticket.description)
    }
  }, [ticket])

  if (isLoading) return <Loader label="Loading ticket…" />
  if (isError || !ticket)
    return <div className="p-8 text-red-600">Ticket not found.</div>

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null
    setFileError(null)
    if (file && file.size > MAX_SCREENSHOT_BYTES) {
      setFileError('Image is too large (max 5 MB).')
      return
    }
    setNewFile(file)
    setPreview(file ? URL.createObjectURL(file) : null)
    if (file) setRemoveExisting(false)
  }

  const saving = update.isPending || updateShot.isPending || removeShot.isPending

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    try {
      // 1. Text fields.
      await update.mutateAsync({
        id,
        payload: { title: title.trim(), description: description.trim() },
      })
      // 2. Screenshot: replace, or remove, or leave unchanged.
      if (newFile) {
        await updateShot.mutateAsync({ id, file: newFile })
      } else if (removeExisting && ticket.screenshot_url) {
        await removeShot.mutateAsync(id)
      }
      navigate(`/tickets/${id}`)
    } catch {
      setError('Could not save changes. Please check your input and try again.')
    }
  }

  // What screenshot (if any) to show as the "current" state.
  const showExisting = ticket.screenshot_url && !newFile && !removeExisting

  return (
    <div className="mx-auto max-w-2xl p-6">
      <button
        onClick={() => navigate(`/tickets/${id}`)}
        className="mb-4 text-sm text-gray-500 hover:underline"
      >
        ← Back to ticket
      </button>

      <h1 className="mb-4 text-2xl font-bold text-gray-900">Edit Ticket</h1>

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
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Description
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            minLength={20}
            maxLength={5000}
            required
            rows={6}
            className="w-full rounded border px-3 py-2"
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">
            Screenshot <span className="font-normal text-gray-400">(optional)</span>
          </label>

          {showExisting && (
            <div className="mb-2">
              <img
                src={ticket.screenshot_url!}
                alt="Current screenshot"
                className="max-h-48 rounded border"
              />
              <button
                type="button"
                onClick={() => setRemoveExisting(true)}
                className="mt-1 text-sm text-red-600 hover:underline"
              >
                Remove screenshot
              </button>
            </div>
          )}

          {removeExisting && !newFile && (
            <p className="mb-2 text-sm text-gray-500">
              Screenshot will be removed on save.{' '}
              <button
                type="button"
                onClick={() => setRemoveExisting(false)}
                className="text-blue-600 hover:underline"
              >
                Undo
              </button>
            </p>
          )}

          <input
            type="file"
            accept="image/png,image/jpeg,image/webp,image/gif"
            onChange={handleFileChange}
            className="block w-full text-sm text-gray-600 file:mr-3 file:rounded file:border-0 file:bg-blue-50 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-blue-700 hover:file:bg-blue-100"
          />
          {fileError && <p className="mt-1 text-sm text-red-600">{fileError}</p>}

          {newFile && preview && (
            <div className="mt-2">
              <p className="mb-1 text-sm text-gray-500">New screenshot:</p>
              <img src={preview} alt="New screenshot preview" className="max-h-48 rounded border" />
              <button
                type="button"
                onClick={() => {
                  setNewFile(null)
                  setPreview(null)
                }}
                className="mt-1 text-sm text-gray-500 hover:underline"
              >
                Cancel
              </button>
            </div>
          )}
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={saving}
            className="rounded bg-blue-600 px-4 py-2 font-medium text-white disabled:opacity-50"
          >
            {saving ? 'Saving…' : 'Save'}
          </button>
          <button
            type="button"
            onClick={() => navigate(`/tickets/${id}`)}
            className="rounded border px-4 py-2 text-sm font-medium text-gray-700"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
