import { redirect } from "next/navigation";
import SavedDecksList, {
  type SavedDeckRecord,
} from "@/components/decks/SavedDecksList";
import { createClient } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default async function SavedDecksPage() {
  const supabase = createClient();
  const {
    data: { user },
    error: userError,
  } = await supabase.auth.getUser();

  if (userError) {
    console.error("[saved] Failed to load user", userError);
  }

  if (!user) {
    redirect("/auth");
  }

  // Get user_decks first, then fetch deck titles separately (manual join)
  // This is more reliable than nested select which has type issues
  const { data: userDecksData, error: userDecksError } = await supabase
    .from("user_decks")
    .select("deck_id, created_at")
    .order("created_at", { ascending: false });

  let data: SavedDeckRecord[] | null = null;
  let error = userDecksError;

  if (userDecksError) {
    console.error("[saved] Failed to fetch user_decks", userDecksError);
  } else if (userDecksData && userDecksData.length > 0) {
    // Fetch deck titles separately
    const deckIds = userDecksData.map(ud => ud.deck_id);
    const { data: decksData, error: decksError } = await supabase
      .from("decks")
      .select("deck_id, title")
      .in("deck_id", deckIds);

    if (decksError) {
      console.error("[saved] Failed to fetch decks", decksError);
      error = decksError;
    } else {
      // Merge the data
      const decksMap = new Map((decksData || []).map(d => [d.deck_id, d.title]));
      console.log("[saved] Decks map:", Array.from(decksMap.entries()));
      console.log("[saved] User decks count:", userDecksData.length);
      data = userDecksData.map(ud => {
        const title = decksMap.get(ud.deck_id);
        console.log(`[saved] Deck ${ud.deck_id}: title = ${title}`);
        return {
          deck_id: ud.deck_id,
          created_at: ud.created_at,
          decks: title ? { title } : null
        };
      });
      error = null;
    }
  } else {
    data = [];
  }

  // Debug: log what we actually got
  console.log("[saved] Raw data from Supabase:", JSON.stringify(data, null, 2));
  console.log("[saved] First deck sample:", data?.[0]);
  if (error) {
    console.error("[saved] Final error after fallback:", error);
  }

  const decks = (data as SavedDeckRecord[] | null) ?? [];

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-6">
      {decks.length === 0 && !error && (
        <p className="text-sm text-muted-foreground">
          You have no saved decks yet. Generate a deck and open it once to see it here.
        </p>
      )}
      <SavedDecksList
        decks={decks}
        showTitle
        errorMessage={error?.message ?? null}
      />
    </div>
  );
}

