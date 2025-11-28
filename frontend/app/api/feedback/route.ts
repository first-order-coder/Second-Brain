import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

/**
 * POST /api/feedback
 *
 * Lightweight endpoint to store user feedback in Supabase `public.feedback`.
 * Uses the Supabase anon key (via the shared server client) and relies on
 * RLS policy: "Anyone can insert feedback".
 */
export async function POST(req: NextRequest) {
  try {
    let body: any;
    try {
      body = await req.json();
    } catch {
      return NextResponse.json(
        { error: "Invalid JSON body." },
        { status: 400 }
      );
    }

    const rawMessage = typeof body.message === "string" ? body.message : "";
    const message = rawMessage.trim();
    const rawEmail = typeof body.email === "string" ? body.email : undefined;
    const email = rawEmail?.trim() || null;
    const pageUrl =
      typeof body.pageUrl === "string" && body.pageUrl.length > 0
        ? body.pageUrl
        : null;

    if (!message || message.length < 5) {
      return NextResponse.json(
        { error: "Feedback message must be at least 5 characters long." },
        { status: 400 }
      );
    }

    const supabase = createClient();

    const { error } = await supabase.from("feedback").insert({
      message,
      email,
      page_url: pageUrl,
    });

    if (error) {
      console.error("[api/feedback] Supabase insert error:", error);
      return NextResponse.json(
        { error: "Failed to store feedback. Please try again later." },
        { status: 500 }
      );
    }

    return NextResponse.json({ ok: true }, { status: 200 });
  } catch (err) {
    console.error("[api/feedback] Unexpected error:", err);
    return NextResponse.json(
      { error: "Unexpected error while submitting feedback." },
      { status: 500 }
    );
  }
}


