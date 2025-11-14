import Link from "next/link";
import HeaderAuthControls from "@/components/app/HeaderAuthControls";
import { createClient } from "@/lib/supabase/server";
import { ThemeToggle } from "@/components/theme/ThemeToggle";
import UserMenu from "@/components/app/UserMenu";

export default async function Header() {
  let user = null;
  let email = null;
  let name = null;
  let imageUrl = null;

  try {
    const supabase = createClient();
    const {
      data: { user: authUser },
    } = await supabase.auth.getUser();
    user = authUser;
    email = user?.email ?? null;
    const metadata = (user?.user_metadata ?? {}) as Record<string, unknown>;
    name =
      typeof metadata.name === "string"
        ? metadata.name
        : typeof metadata.full_name === "string"
          ? metadata.full_name
          : null;
    imageUrl =
      (typeof metadata.avatar_url === "string"
        ? metadata.avatar_url
        : typeof metadata.picture === "string"
          ? metadata.picture
          : null) ?? null;
  } catch (error) {
    // If auth check fails (e.g., after signout), treat as logged out
    console.error("[Header] Failed to get user:", error);
    user = null;
  }

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
            <UserMenu email={email} name={name} imageUrl={imageUrl} />
          )}
        </div>
      </div>
    </header>
  );
}
