'use client'

import { useState } from 'react'
import { deleteNote } from '@/app/actions/delete-note'
import { useRouter } from 'next/navigation'

export default function DeleteButton({ noteId }: { noteId: string }) {
  const [loading, setLoading] = useState(false)
  const router = useRouter()

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this note?')) {
      return
    }

    setLoading(true)
    try {
      await deleteNote(noteId)
      router.refresh()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete note')
    } finally {
      setLoading(false)
    }
  }

  return (
    <button
      onClick={handleDelete}
      disabled={loading}
      className="ml-2 px-2 py-1 text-sm text-red-600 hover:text-red-800 disabled:opacity-50"
    >
      {loading ? '...' : 'Delete'}
    </button>
  )
}




