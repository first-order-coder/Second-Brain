'use server';

import { createClient } from "@/lib/supabase/server";

export async function saveDeck(deckId: string) {
  const supabase = createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return { ok: false, error: "Not authenticated" } as const;
  }

  const { error } = await supabase
    .from("user_decks")
    .upsert({ user_id: user.id, deck_id: deckId }, { onConflict: "user_id,deck_id" });

  if (error) {
    return { ok: false, error: error.message } as const;
  }

  return { ok: true } as const;
}
