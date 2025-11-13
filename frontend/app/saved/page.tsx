import { redirect } from "next/navigation";
import SavedDecksList, {
  type SavedDeckRecord,
} from "@/components/decks/SavedDecksList";
import { createClient } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

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

  const { data, error } = await supabase
    .from("user_decks")
    .select("deck_id, created_at")
    .order("created_at", { ascending: false });

  if (error) {
    console.error("[saved] Failed to fetch user decks", error);
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

