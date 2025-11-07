'use client'

import { useState } from 'react'
import { createNotebook } from '@/app/actions/create-notebook'
import { useRouter } from 'next/navigation'

export default function NotebookForm() {
  const [title, setTitle] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      await createNotebook(title)
      setTitle('')
      router.refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create notebook')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="mb-6 p-4 border rounded-lg">
      <div className="flex gap-2">
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="New notebook name..."
          className="flex-1 px-3 py-2 border rounded-md"
          disabled={loading}
          required
        />
        <button
          type="submit"
          disabled={loading || !title.trim()}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Creating...' : 'Create'}
        </button>
      </div>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </form>
  )
}




