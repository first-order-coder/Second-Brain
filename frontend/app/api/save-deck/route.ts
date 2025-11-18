import { NextRequest, NextResponse } from "next/server";
import { saveDeck } from "@/app/actions/save-deck";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();

    const deckId = body.deckId as string | undefined;
    const title = body.title as string | undefined;
    const sourceType = (body.sourceType as string | undefined) ?? null;
    const sourceLabel = (body.sourceLabel as string | undefined) ?? null;

    console.log("[api/save-deck] Received body:", {
      deckId,
      title,
      sourceType,
      sourceLabel,
    });

    // IMPORTANT: no fallback here - reject if missing
    if (!deckId || !title) {
      return NextResponse.json(
        { ok: false, error: "deckId and title are required" },
        { status: 400 }
      );
    }

    const result = await saveDeck(deckId, { title, sourceType, sourceLabel });
    
    if (!result.ok) {
      const status = result.error === "Not authenticated" ? 401 : 500;
      console.warn("[api/save-deck] Save failed", { deckId, error: result.error, sourceType });
      return NextResponse.json(result, { status });
    }

    console.log("[api/save-deck] Save succeeded", { 
      deckId, 
      title, 
      sourceType,
      sourceLabel,
    });
    
    return NextResponse.json({ ok: true, deckId, title }, { status: 200 });
  } catch (error) {
    console.error("[api/save-deck] Unexpected error", error);
    return NextResponse.json(
      { ok: false, error: error instanceof Error ? error.message : "unknown" },
      { status: 500 },
    );
  }
}
