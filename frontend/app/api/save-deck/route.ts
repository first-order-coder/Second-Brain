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

    const result = await saveDeck(deckId);
    const status = result.ok ? 200 : result.error === "Not authenticated" ? 401 : 500;
    if (!result.ok) {
      console.warn("[api/save-deck] Save failed", { deckId, error: result.error });
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
