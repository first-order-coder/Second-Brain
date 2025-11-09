"use server";

import { createClient } from "@/lib/supabase/server";

type SaveDeckResult =
  | { ok: true }
  | { ok: false; error: string };

export async function saveDeck(deckId: string): Promise<SaveDeckResult> {
  const supabase = createClient();
  const {
    data: { user },
    error: userErr,
  } = await supabase.auth.getUser();

  if (userErr) {
    console.error("[saveDeck] Failed to fetch user", userErr);
    return { ok: false, error: userErr.message };
  }

  if (!user) {
    console.warn("[saveDeck] Attempted save without authenticated user", {
      deckId,
    });
    return { ok: false, error: "Not authenticated" };
  }

  const { error } = await supabase
    .from("user_decks")
    .upsert(
      { user_id: user.id, deck_id: deckId },
      { onConflict: "user_id,deck_id" },
    );

  if (error) {
    console.error("[saveDeck] Supabase upsert failed", { deckId, error });
    return { ok: false, error: error.message };
  }

  return { ok: true };
}
