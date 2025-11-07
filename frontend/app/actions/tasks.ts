'use server'

import { createClient } from '@/lib/supabase/server'
import { revalidatePath } from 'next/cache'

export async function createTask(
  notebookId: string,
  title: string,
  description?: string,
  dueAt?: string
) {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  
  if (!user) {
    throw new Error('Not authenticated')
  }

  const { error } = await supabase.from('tasks').insert({
    notebook_id: notebookId,
    owner: user.id,
    title,
    description,
    due_at: dueAt
  })
  
  if (error) {
    throw error
  }

  revalidatePath(`/app/notebooks/${notebookId}`)
}

export async function updateTask(
  taskId: string,
  patch: {
    title?: string
    description?: string
    due_at?: string
    is_done?: boolean
  }
) {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  
  if (!user) {
    throw new Error('Not authenticated')
  }

  const { error } = await supabase
    .from('tasks')
    .update({ ...patch, updated_at: new Date().toISOString() })
    .eq('id', taskId)
  
  if (error) {
    throw error
  }
  
  revalidatePath('/app')
}

export async function deleteTask(taskId: string) {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  
  if (!user) {
    throw new Error('Not authenticated')
  }

  const { error } = await supabase.from('tasks').delete().eq('id', taskId)
  
  if (error) {
    throw error
  }
  
  revalidatePath('/app')
}

