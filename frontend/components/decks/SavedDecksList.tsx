import Link from "next/link";

export type SavedDeckRecord = {
  deck_id: string;
  created_at: string;
  decks?: { title: string | null } | null;
};

type SavedDecksListProps = {
  decks: SavedDeckRecord[];
  limit?: number;
  showTitle?: boolean;
  errorMessage?: string | null;
};

export default function SavedDecksList({
  decks,
  limit,
  showTitle = true,
  errorMessage = null,
}: SavedDecksListProps) {
  if (errorMessage) {
    return (
      <div className="rounded-md border p-4 text-sm text-red-600">
        Error: {errorMessage}
      </div>
    );
  }

  const visibleDecks =
    typeof limit === "number" ? decks.slice(0, Math.max(0, limit)) : decks;

  if (!visibleDecks || visibleDecks.length === 0) {
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
        {visibleDecks.map((deck) => {
          const deckId = String(deck.deck_id);
          // Debug: log the deck structure
          console.log("[SavedDecksList] Deck structure:", { deckId, decks: deck.decks, title: deck.decks?.title });
          
          // Handle different possible data structures from Supabase
          // Supabase might return decks as an array or object
          let title: string | null = null;
          if (Array.isArray(deck.decks) && deck.decks.length > 0) {
            title = deck.decks[0]?.title ?? null;
          } else if (deck.decks && typeof deck.decks === 'object' && 'title' in deck.decks) {
            title = (deck.decks as { title: string | null }).title;
          }
          
          const displayTitle = title ?? deckId;
          
          // Fix timezone - ensure we're using local timezone
          const savedDate = new Date(deck.created_at);
          const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
          const savedAtString = savedDate.toLocaleString(undefined, {
            timeZone: timezone,
            year: "numeric",
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
          });
          
          return (
            <li
              key={deckId}
              className="flex items-center justify-between rounded-md border px-4 py-2"
            >
              <div className="flex flex-col">
                <span className="text-sm font-medium">{displayTitle}</span>
                <span className="text-xs text-muted-foreground">
                  Saved {savedAtString}
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

