import Link from "next/link";

export type SavedDeckRecord = {
  deck_id: string;
  created_at: string;
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

