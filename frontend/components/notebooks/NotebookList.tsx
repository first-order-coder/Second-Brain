import { createClient } from '@/lib/supabase/server'
import Link from 'next/link'
import { createNotebook } from '@/app/actions/create-notebook'
import NotebookForm from './NotebookForm'

export default async function NotebookList() {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  
  if (!user) {
    return <div>Please sign in</div>
  }

  const { data, error } = await supabase
    .from('notebooks')
    .select('*')
    .order('created_at', { ascending: false })

  if (error) {
    return <div className="text-red-600">Error: {error.message}</div>
  }

  return (
    <div className="space-y-4">
      <NotebookForm />
      
      {data && data.length > 0 ? (
        <ul className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.map((notebook) => (
            <li key={notebook.id}>
              <Link
                href={`/app/notebooks/${notebook.id}`}
                className="block p-4 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition"
              >
                <h3 className="font-semibold">{notebook.title}</h3>
                <p className="text-sm text-gray-500 mt-1">
                  {new Date(notebook.created_at).toLocaleDateString()}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-gray-500">No notebooks yet. Create one to get started!</p>
      )}
    </div>
  )
}




