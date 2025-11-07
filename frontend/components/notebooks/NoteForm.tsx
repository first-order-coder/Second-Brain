'use client'

import { useState } from 'react'
import { createNote } from '@/app/actions/create-note'
import { useRouter } from 'next/navigation'

export default function NoteForm({ notebookId }: { notebookId: string }) {
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      await createNote(notebookId, title, content)
      setTitle('')
      setContent('')
      router.refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create note')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="mb-4 p-4 border rounded-lg">
      <input
        type="text"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Note title..."
        className="w-full mb-2 px-3 py-2 border rounded-md"
        disabled={loading}
      />
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="Note content..."
        className="w-full mb-2 px-3 py-2 border rounded-md"
        rows={3}
        disabled={loading}
      />
      <button
        type="submit"
        disabled={loading || !title.trim()}
        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
      >
        {loading ? 'Creating...' : 'Create Note'}
      </button>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </form>
  )
}




