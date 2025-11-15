import { NextResponse } from "next/server";
import { saveDeck } from "@/app/actions/save-deck";

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const deckId = typeof body?.deckId === "string" ? body.deckId : null;

    if (!deckId) {
      console.warn("[api/save-deck] Missing deckId in request body", body);
      return NextResponse.json(
        { ok: false, error: "Missing deckId" },
        { status: 400 },
      );
    }

    const title = typeof body?.title === "string" && body.title.trim() !== "" ? body.title.trim() : null;
    const sourceType = typeof body?.sourceType === "string" ? body.sourceType : null;
    const sourceLabel = typeof body?.sourceLabel === "string" ? body.sourceLabel : null;

    const options = {
      title,
      sourceType,
      sourceLabel,
    };

    // Log received data for debugging
    console.log("[api/save-deck] Received:", { 
      deckId, 
      title: options.title, 
      sourceType: options.sourceType, 
      sourceLabel: options.sourceLabel,
      rawBody: { title: body?.title, sourceType: body?.sourceType, sourceLabel: body?.sourceLabel }
    });

    const result = await saveDeck(deckId, options);
    const status = result.ok ? 200 : result.error === "Not authenticated" ? 401 : 500;
    if (!result.ok) {
      console.warn("[api/save-deck] Save failed", { deckId, error: result.error });
    } else {
      console.log("[api/save-deck] Save succeeded", { deckId, title: options.title });
    }
    return NextResponse.json(result, { status });
  } catch (error) {
    console.error("[api/save-deck] Unexpected error", error);
    return NextResponse.json(
      { ok: false, error: error instanceof Error ? error.message : "unknown" },
      { status: 500 },
    );
  }
}
