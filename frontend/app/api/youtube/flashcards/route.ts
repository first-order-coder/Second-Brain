import { NextRequest, NextResponse } from "next/server";
import { getApiBase } from '@/lib/getApiBase';

export async function POST(req: NextRequest) {
  let API_BASE: string;
  try {
    API_BASE = getApiBase();
  } catch (error) {
    return NextResponse.json(
      { detail: error instanceof Error ? error.message : "NEXT_PUBLIC_API_BASE_URL is not set." },
      { status: 500 }
    );
  }
  try {
    const body = await req.json();
    const r = await fetch(`${API_BASE}/youtube/flashcards`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    let data: any = null;
    try { data = await r.json(); } catch { data = { detail: "Backend returned non-JSON response." }; }
    return NextResponse.json(data, { status: r.status });
  } catch (e: any) {
    return NextResponse.json(
      { detail: `Proxy could not reach ${API_BASE}/youtube/flashcards. Check NEXT_PUBLIC_API_URL, container networking, and that FastAPI listens on 0.0.0.0:8000.` },
      { status: 502 }
    );
  }
}

// Save deck proxy
export async function PUT(req: NextRequest) {
  let API_BASE: string;
  try {
    API_BASE = getApiBase();
  } catch (error) {
    return NextResponse.json(
      { detail: error instanceof Error ? error.message : "NEXT_PUBLIC_API_BASE_URL is not set." },
      { status: 500 }
    );
  }
  const body = await req.json();
  const r = await fetch(`${API_BASE}/youtube/save`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const text = await r.text();
  try {
    const json = JSON.parse(text);
    return NextResponse.json(json, { status: r.status, headers: { 'x-proxy-api-base': API_BASE } });
  } catch {
    return new NextResponse(text, { status: r.status, headers: { 'content-type': 'text/plain', 'x-proxy-api-base': API_BASE } });
  }
}
