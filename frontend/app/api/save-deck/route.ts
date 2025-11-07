import { NextResponse } from "next/server";
import { saveDeck } from "@/app/actions/save-deck";

export async function POST(req: Request) {
  const { searchParams } = new URL(req.url);
  const deckId = searchParams.get("deckId");

  if (!deckId) {
    return NextResponse.json({ ok: false, error: "Missing deckId" }, { status: 400 });
  }

  const result = await saveDeck(deckId);
  return NextResponse.json(result, { status: result.ok ? 200 : 401 });
}
