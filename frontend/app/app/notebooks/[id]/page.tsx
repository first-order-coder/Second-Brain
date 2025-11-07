import { createClient } from '@/lib/supabase/server'
import { redirect } from 'next/navigation'
import NotebookDetail from '@/components/notebooks/NotebookDetail'

export default async function NotebookDetailPage({
  params,
}: {
  params: { id: string }
}) {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  
  if (!user) {
    redirect('/auth/signin')
  }

  return <NotebookDetail notebookId={params.id} />
}




