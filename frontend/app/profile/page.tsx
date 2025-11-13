import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import SavedDecksList, {
  type SavedDeckRecord,
} from "@/components/decks/SavedDecksList";

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

  const { data, error } = await supabase
    .from("user_decks")
    .select("deck_id, created_at")
    .order("created_at", { ascending: false })
    .limit(10);

  if (error) {
    console.error("[profile] Failed to fetch user decks", error);
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

