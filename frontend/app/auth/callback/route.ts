import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const next = url.searchParams.get("next");

  if (code) {
    const supabase = createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (error) {
      const message = encodeURIComponent(error.message);
      return NextResponse.redirect(`${url.origin}/auth?error=${message}`);
    }
  }

  const destination = next ? `${url.origin}${next}` : `${url.origin}/`;
  return NextResponse.redirect(destination);
}

