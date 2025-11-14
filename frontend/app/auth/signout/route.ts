import { NextRequest, NextResponse } from "next/server";
import { createServerClient } from "@supabase/ssr";

// Ensure we are using the Node runtime (Supabase SSR expects this)
export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  // We will *always* send the user back to home, even on error
  const redirectUrl = new URL("/", req.url);
  const res = NextResponse.redirect(redirectUrl);

  try {
    const supabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      {
        cookies: {
          get(name: string) {
            return req.cookies.get(name)?.value;
          },
          set(name: string, value: string, options: any) {
            res.cookies.set(name, value, options);
          },
          remove(name: string, options: any) {
            res.cookies.set(name, "", { ...options, maxAge: 0 });
          },
        },
      }
    );

    await supabase.auth.signOut();
  } catch (error) {
    // IMPORTANT: do not rethrow, just log, so we don't get a 500 page
    console.error("[auth/signout] Error during sign out:", error);
  }

  return res;
}
