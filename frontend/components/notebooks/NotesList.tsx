import { createClient } from '@/lib/supabase/server'
import { deleteNote } from '@/app/actions/delete-note'
import DeleteButton from './DeleteButton'

export default async function NotesList({ notebookId }: { notebookId: string }) {
  const supabase = createClient()
  
  const { data: notes, error } = await supabase
    .from('notes')
    .select('*')
    .eq('notebook_id', notebookId)
    .order('created_at', { ascending: false })

  if (error) {
    return <div className="text-red-600">Error: {error.message}</div>
  }

  if (!notes || notes.length === 0) {
    return <p className="text-gray-500">No notes yet.</p>
  }

  return (
    <div className="space-y-2">
      {notes.map((note) => (
        <div key={note.id} className="p-4 border rounded-lg">
          <div className="flex justify-between items-start">
            <div className="flex-1">
              <h3 className="font-semibold">{note.title || 'Untitled'}</h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1 whitespace-pre-wrap">
                {note.content}
              </p>
              <p className="text-xs text-gray-500 mt-2">
                {new Date(note.updated_at).toLocaleString()}
              </p>
            </div>
            <DeleteButton noteId={note.id} />
          </div>
        </div>
      ))}
    </div>
  )
}




