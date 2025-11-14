import { NextRequest, NextResponse } from "next/server";
import { createServerClient } from "@supabase/ssr";

// Make sure this is a Node route, not edge
export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  const redirectUrl = new URL("/", req.url);
  // Use 303 See Other for POST->GET redirect (prevents client-side issues)
  const res = NextResponse.redirect(redirectUrl, { status: 303 });

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
    // Do NOT throw – just log, so we never surface a 500 page
    console.error("[auth/signout] Error during sign out:", error);
  }

  return res;
}
