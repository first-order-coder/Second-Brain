'use server'

import { createClient } from '@/lib/supabase/server'
import { revalidatePath } from 'next/cache'

export async function createNotebook(title: string) {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  
  if (!user) {
    throw new Error('Not authenticated')
  }

  const { error } = await supabase.from('notebooks').insert({
    title,
    owner: user.id
  })
  
  if (error) {
    throw error
  }

  revalidatePath('/app')
}




