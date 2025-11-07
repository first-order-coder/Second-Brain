import { createClient } from '@/lib/supabase/server'
import { createNote } from '@/app/actions/create-note'
import NotesList from './NotesList'
import TasksList from './TasksList'
import NoteForm from './NoteForm'
import TaskForm from './TaskForm'

export default async function NotebookDetail({ notebookId }: { notebookId: string }) {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  
  if (!user) {
    return <div>Please sign in</div>
  }

  const { data: notebook, error: notebookError } = await supabase
    .from('notebooks')
    .select('*')
    .eq('id', notebookId)
    .single()

  if (notebookError || !notebook) {
    return <div className="text-red-600">Notebook not found</div>
  }

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">{notebook.title}</h1>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          <h2 className="text-2xl font-semibold mb-4">Notes</h2>
          <NoteForm notebookId={notebookId} />
          <NotesList notebookId={notebookId} />
        </div>
        
        <div>
          <h2 className="text-2xl font-semibold mb-4">Tasks</h2>
          <TaskForm notebookId={notebookId} />
          <TasksList notebookId={notebookId} />
        </div>
      </div>
    </div>
  )
}




