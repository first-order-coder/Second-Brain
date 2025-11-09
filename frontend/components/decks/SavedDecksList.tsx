import Link from "next/link";
import { createClient } from "@/lib/supabase/server";

type SavedDecksListProps = {
  limit?: number;
  showTitle?: boolean;
};

export default async function SavedDecksList({
  limit,
  showTitle = true,
}: SavedDecksListProps) {
  const supabase = createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return (
      <div className="rounded-md border p-4 text-sm">
        Please{" "}
        <Link href="/auth" className="underline">
          sign in
        </Link>{" "}
        to view your saved decks.
      </div>
    );
  }

  let query = supabase
    .from("user_decks")
    .select("deck_id, created_at")
    .order("created_at", { ascending: false });

  if (typeof limit === "number") {
    query = query.limit(limit);
  }

  const { data, error } = await query;

  if (error) {
    return (
      <div className="rounded-md border p-4 text-sm text-red-600">
        Error: {error.message}
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="rounded-md border p-4 text-sm">
        No decks saved yet. Generate a deck and open it once.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {showTitle && <h2 className="text-lg font-semibold">My Decks</h2>}
      <ul className="space-y-2">
        {data.map((deck) => {
          const deckId = String(deck.deck_id);
          return (
            <li
              key={deckId}
              className="flex items-center justify-between rounded-md border px-4 py-2"
            >
              <div className="flex flex-col">
                <span className="text-sm font-medium">{deckId}</span>
                <span className="text-xs text-muted-foreground">
                  Saved {new Date(deck.created_at).toLocaleString()}
                </span>
              </div>
              <Link
                href={`/flashcards/${deckId}`}
                className="text-sm text-blue-600 underline"
              >
                Open
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}


