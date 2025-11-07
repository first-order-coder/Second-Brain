'use server'

import { createClient } from '@/lib/supabase/server'
import { revalidatePath } from 'next/cache'

export async function createNote(notebookId: string, title: string, content: string) {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  
  if (!user) {
    throw new Error('Not authenticated')
  }

  const { error } = await supabase.from('notes').insert({
    notebook_id: notebookId,
    owner: user.id,
    title,
    content
  })
  
  if (error) {
    throw error
  }

  revalidatePath(`/app/notebooks/${notebookId}`)
}




