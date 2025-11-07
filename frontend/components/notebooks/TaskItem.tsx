'use client'

import { useState } from 'react'
import { updateTask, deleteTask } from '@/app/actions/tasks'
import { useRouter } from 'next/navigation'

export default function TaskItem({ task }: { task: any }) {
  const [loading, setLoading] = useState(false)
  const router = useRouter()

  const handleToggle = async () => {
    setLoading(true)
    try {
      await updateTask(task.id, { is_done: !task.is_done })
      router.refresh()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to update task')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this task?')) {
      return
    }

    setLoading(true)
    try {
      await deleteTask(task.id)
      router.refresh()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete task')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={`p-4 border rounded-lg ${task.is_done ? 'opacity-60' : ''}`}>
      <div className="flex items-start gap-2">
        <input
          type="checkbox"
          checked={task.is_done}
          onChange={handleToggle}
          disabled={loading}
          className="mt-1"
        />
        <div className="flex-1">
          <h3 className={`font-semibold ${task.is_done ? 'line-through' : ''}`}>
            {task.title}
          </h3>
          {task.description && (
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              {task.description}
            </p>
          )}
          {task.due_at && (
            <p className="text-xs text-gray-500 mt-1">
              Due: {new Date(task.due_at).toLocaleString()}
            </p>
          )}
        </div>
        <button
          onClick={handleDelete}
          disabled={loading}
          className="px-2 py-1 text-sm text-red-600 hover:text-red-800 disabled:opacity-50"
        >
          Delete
        </button>
      </div>
    </div>
  )
}




