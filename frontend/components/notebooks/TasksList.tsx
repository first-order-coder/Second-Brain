import { createClient } from '@/lib/supabase/server'
import { updateTask, deleteTask } from '@/app/actions/tasks'
import TaskItem from './TaskItem'

export default async function TasksList({ notebookId }: { notebookId: string }) {
  const supabase = createClient()
  
  const { data: tasks, error } = await supabase
    .from('tasks')
    .select('*')
    .eq('notebook_id', notebookId)
    .order('due_at', { ascending: true, nullsFirst: false })

  if (error) {
    return <div className="text-red-600">Error: {error.message}</div>
  }

  if (!tasks || tasks.length === 0) {
    return <p className="text-gray-500">No tasks yet.</p>
  }

  return (
    <div className="space-y-2">
      {tasks.map((task) => (
        <TaskItem key={task.id} task={task} />
      ))}
    </div>
  )
}

