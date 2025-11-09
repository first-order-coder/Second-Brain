import { redirect } from "next/navigation";
import SavedDecksList from "@/components/decks/SavedDecksList";
import { createClient } from "@/lib/supabase/server";

export default async function SavedDecksPage() {
  const supabase = createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/auth");
  }

  return (
    <div className="mx-auto max-w-3xl p-6">
      <SavedDecksList showTitle />
    </div>
  );
}

