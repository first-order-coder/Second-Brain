import { NextRequest, NextResponse } from "next/server";
import { createServerClient } from "@supabase/ssr";

export async function POST(req: NextRequest) {
  const origin = req.nextUrl.origin;
  const redirectUrl =
    process.env.NEXT_PUBLIC_APP_URL ?? origin ?? "http://localhost:3000";
  const res = NextResponse.redirect(new URL("/", redirectUrl));

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        get(name: string) {
          return req.cookies.get(name)?.value;
        },
        set(name: string, value: string, options: any) {
          const cookieOptions = {
            path: "/",
            ...(options ?? {}),
          };
          res.cookies.set(name, value, cookieOptions);
        },
        remove(name: string, options: any) {
          const cookieOptions = {
            path: "/",
            ...(options ?? {}),
            maxAge: 0,
          };
          res.cookies.set(name, "", cookieOptions);
        },
      },
    }
  );

  await supabase.auth.signOut().catch((error) => {
    console.warn("[auth/signout] Supabase signOut failed", error);
  });

  return res;
}
