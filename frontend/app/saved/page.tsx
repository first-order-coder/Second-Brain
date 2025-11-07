import Link from "next/link";
import { createClient } from "@/lib/supabase/server";

export default async function SavedDecksPage() {
  const supabase = createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        Please <Link href="/auth" className="underline">sign in</Link> to view your decks.
      </div>
    );
  }

  const { data, error } = await supabase
    .from("user_decks")
    .select("deck_id, created_at")
    .order("created_at", { ascending: false });

  if (error) {
    return (
      <div className="mx-auto max-w-3xl p-6 text-red-600">
        {error.message}
      </div>
    );
  }

  if (!data?.length) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        No decks saved yet. Generate one from a PDF or YouTube link.
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl p-6">
      <h1 className="mb-4 text-xl font-semibold">My Decks</h1>
      <ul className="space-y-2">
        {data.map((deck) => (
          <li
            key={deck.deck_id}
            className="flex items-center justify-between rounded-md border px-4 py-2"
          >
            <div className="flex flex-col text-sm">
              <span>{deck.deck_id}</span>
              <span className="text-xs text-muted-foreground">
                Saved {new Date(deck.created_at).toLocaleString()}
              </span>
            </div>
            <Link href={`/flashcards/${deck.deck_id}`} className="text-blue-600 underline">
              Open
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
