import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import SavedDecksList, {
  type SavedDeckRecord,
} from "@/components/decks/SavedDecksList";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default async function ProfilePage() {
  const supabase = createClient();
  const {
    data: { user },
    error: userError,
  } = await supabase.auth.getUser();

  if (userError) {
    console.error("[profile] Failed to load user", userError);
  }

  if (!user) {
    return (
      <div className="p-6">
        Please{" "}
        <Link className="underline" href="/auth">
          sign in
        </Link>
        .
      </div>
    );
  }

  // Get user_decks first, then fetch deck titles separately (manual join)
  // This is more reliable than nested select which has type issues
  const { data: userDecksData, error: userDecksError } = await supabase
    .from("user_decks")
    .select("deck_id, created_at")
    .order("created_at", { ascending: false })
    .limit(10);

  let data: SavedDeckRecord[] | null = null;
  let error = userDecksError;

  if (userDecksError) {
    console.error("[profile] Failed to fetch user_decks", userDecksError);
  } else if (userDecksData && userDecksData.length > 0) {
    // Fetch deck titles separately
    const deckIds = userDecksData.map(ud => ud.deck_id);
    const { data: decksData, error: decksError } = await supabase
      .from("decks")
      .select("deck_id, title")
      .in("deck_id", deckIds);

    if (decksError) {
      console.error("[profile] Failed to fetch decks", decksError);
      error = decksError;
    } else {
      // Merge the data
      const decksMap = new Map((decksData || []).map(d => [d.deck_id, d.title]));
      data = userDecksData.map(ud => ({
        deck_id: ud.deck_id,
        created_at: ud.created_at,
        decks: decksMap.has(ud.deck_id) ? { title: decksMap.get(ud.deck_id) } : null
      }));
      error = null;
    }
  } else {
    data = [];
  }

  // Debug: log what we actually got
  console.log("[profile] Raw data from Supabase:", JSON.stringify(data, null, 2));
  if (error) {
    console.error("[profile] Final error after fallback:", error);
  }

  const decks = (data as SavedDeckRecord[] | null) ?? [];

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6">
      <div>
        <h1 className="text-xl font-semibold">Your Profile</h1>
        <div className="mt-2 rounded-md border p-4 text-sm">
          <div>
            <span className="text-muted-foreground">User ID:</span> {user.id}
          </div>
          <div>
            <span className="text-muted-foreground">Email:</span> {user.email}
          </div>
          <div>
            <span className="text-muted-foreground">Created:</span>{" "}
            {user.created_at}
          </div>
        </div>
      </div>

      <SavedDecksList
        decks={decks}
        limit={10}
        showTitle
        errorMessage={error?.message ?? null}
      />

      <div className="flex items-center justify-between">
        <Link href="/saved" className="text-sm underline">
          View all saved decks
        </Link>
        <form action="/auth/signout" method="post">
          <button className="rounded-md border px-3 py-1.5 text-sm">
            Sign out
          </button>
        </form>
      </div>
    </div>
  );
}

