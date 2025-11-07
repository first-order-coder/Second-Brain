'use client'

import { useState } from 'react'
import { createTask } from '@/app/actions/tasks'
import { useRouter } from 'next/navigation'

export default function TaskForm({ notebookId }: { notebookId: string }) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [dueAt, setDueAt] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      await createTask(
        notebookId,
        title,
        description || undefined,
        dueAt || undefined
      )
      setTitle('')
      setDescription('')
      setDueAt('')
      router.refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create task')
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
        placeholder="Task title..."
        className="w-full mb-2 px-3 py-2 border rounded-md"
        disabled={loading}
        required
      />
      <textarea
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        placeholder="Description (optional)..."
        className="w-full mb-2 px-3 py-2 border rounded-md"
        rows={2}
        disabled={loading}
      />
      <input
        type="datetime-local"
        value={dueAt}
        onChange={(e) => setDueAt(e.target.value)}
        className="w-full mb-2 px-3 py-2 border rounded-md"
        disabled={loading}
      />
      <button
        type="submit"
        disabled={loading || !title.trim()}
        className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
      >
        {loading ? 'Creating...' : 'Create Task'}
      </button>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </form>
  )
}




