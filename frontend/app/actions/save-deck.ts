"use server";

import { createClient } from "@/lib/supabase/server";

type SaveDeckResult =
  | { ok: true }
  | { ok: false; error: string };

type SaveDeckOptions = {
  title?: string | null;
  sourceType?: string | null;
  sourceLabel?: string | null;
};

export async function saveDeck(
  deckId: string,
  options?: SaveDeckOptions,
): Promise<SaveDeckResult> {
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

  // Upsert deck metadata FIRST (required for foreign key constraint)
  // IMPORTANT: Only update title if a valid title is provided. Don't overwrite existing good titles with deckId.
  // Check if deck already exists to preserve existing title if new title is null/empty
  const { data: existingDeck } = await supabase
    .from("decks")
    .select("title")
    .eq("deck_id", deckId)
    .single();

  // Use provided title if valid, otherwise preserve existing title, otherwise fallback to deckId
  let title: string;
  if (options?.title && options.title.trim() !== "") {
    // Valid title provided - use it
    title = options.title.trim();
  } else if (existingDeck?.title && existingDeck.title.trim() !== "" && existingDeck.title !== deckId) {
    // No title provided but existing good title exists - preserve it
    title = existingDeck.title;
  } else {
    // No title and no existing title - use deckId as last resort (shouldn't happen with our fixes)
    title = deckId;
  }
  
  console.log("[saveDeck] Title decision:", { 
    provided: options?.title, 
    existing: existingDeck?.title, 
    final: title,
    deckId 
  });
  
  const { error: deckError } = await supabase
    .from("decks")
    .upsert(
      {
        deck_id: deckId,
        title: title,
        source_type: options?.sourceType ?? null,
        source_label: options?.sourceLabel ?? null,
      },
      { onConflict: "deck_id" },
    );

  if (deckError) {
    console.error("[saveDeck] Failed to upsert deck metadata", { deckId, error: deckError });
    return { ok: false, error: deckError.message };
  }

  // Insert/update user_decks relationship (after decks row exists)
  const { error: userDeckError } = await supabase
    .from("user_decks")
    .upsert(
      { user_id: user.id, deck_id: deckId },
      { onConflict: "user_id,deck_id" },
    );

  if (userDeckError) {
    console.error("[saveDeck] Supabase upsert failed", { deckId, error: userDeckError });
    return { ok: false, error: userDeckError.message };
  }

  return { ok: true };
}
