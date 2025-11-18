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

  console.log("[api/save-deck] Auth user:", { 
    userId: user?.id, 
    userEmail: user?.email,
    userError: userErr?.message,
    deckId,
    sourceType: options?.sourceType,
  });

  if (userErr) {
    console.error("[saveDeck] Failed to fetch user", userErr);
    return { ok: false, error: userErr.message };
  }

  if (!user) {
    console.warn("[saveDeck] Attempted save without authenticated user", {
      deckId,
      sourceType: options?.sourceType,
    });
    return { ok: false, error: "Not authenticated" };
  }

  // Upsert deck metadata FIRST (required for foreign key constraint)
  // CRITICAL: Use exact title from frontend - no fallbacks, no deckId, no "PDF Deck"
  // The route handler already validated that title exists, so we can trust it here
  const title = options?.title?.trim() || "";
  
  if (!title) {
    // This should never happen since route handler validates, but double-check
    console.error("[saveDeck] Title is empty after trim", {
      deckId,
      providedTitle: options?.title,
      sourceType: options?.sourceType,
    });
    return { ok: false, error: "Title is required. Cannot save deck without a valid title." };
  }
  
  console.log("[saveDeck] Upserting deck with title:", { 
    deckId,
    title,
    sourceType: options?.sourceType,
    sourceLabel: options?.sourceLabel,
  });
  
  const { data: decksData, error: deckError } = await supabase
    .from("decks")
    .upsert(
      {
        deck_id: deckId,
        title: title,  // exact title from frontend
        source_type: options?.sourceType ?? null,
        source_label: options?.sourceLabel ?? null,
      },
      { onConflict: "deck_id" },
    )
    .select("*")
    .single();

  console.log("[api/save-deck] decks upsert:", { 
    decksData, 
    decksError: deckError,
    deckId,
    title,
    sourceType: options?.sourceType,
    sourceLabel: options?.sourceLabel,
  });

  if (deckError) {
    console.error("[saveDeck] Failed to upsert deck metadata", { deckId, error: deckError });
    return { ok: false, error: deckError.message };
  }

  // Insert/update user_decks relationship (after decks row exists)
  // CRITICAL: Always upsert user_decks for both PDF and YouTube
  const { data: userDecksData, error: userDeckError } = await supabase
    .from("user_decks")
    .upsert(
      { 
        user_id: user.id, 
        deck_id: deckId,
        role: 'owner',
      },
      { onConflict: "user_id,deck_id" },
    )
    .select();

  console.log("[api/save-deck] user_decks upsert:", {
    userDecksData,
    userDecksError: userDeckError,
    userId: user.id,
    deckId,
    sourceType: options?.sourceType,
  });

  if (userDeckError) {
    console.error("[saveDeck] Supabase upsert failed", { deckId, error: userDeckError });
    return { ok: false, error: userDeckError.message };
  }

  return { ok: true };
}
