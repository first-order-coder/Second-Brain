import Link from "next/link";
import HeaderAuthControls from "@/components/app/HeaderAuthControls";
import { createClient } from "@/lib/supabase/server";
import { ThemeToggle } from "@/components/theme/ThemeToggle";

export default async function Header() {
  const supabase = createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  return (
    <header className="w-full border-b bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
        <Link href="/" className="text-lg font-semibold">
          Second Brain
        </Link>

        <div className="flex items-center gap-3">
          <ThemeToggle />
          {!user ? (
            <HeaderAuthControls />
          ) : (
            <div className="flex items-center gap-3">
              <Link href="/saved" className="text-sm underline">
                My Decks
              </Link>
              <Link href="/profile" className="text-sm underline">
                Profile
              </Link>
              <form action="/auth/signout" method="post">
                <button className="rounded-md border px-3 py-1.5 text-sm">
                  Sign out
                </button>
              </form>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
