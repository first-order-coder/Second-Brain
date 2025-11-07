import { createClient } from '@/lib/supabase/server'
import { redirect } from 'next/navigation'
import NotebookList from '@/components/notebooks/NotebookList'

export default async function NotebooksPage() {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  
  if (!user) {
    redirect('/auth/signin')
  }

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">My Notebooks</h1>
      <NotebookList />
    </div>
  )
}




