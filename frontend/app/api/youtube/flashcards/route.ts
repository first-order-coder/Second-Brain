import { NextRequest, NextResponse } from "next/server";
const API_BASE = process.env.NEXT_PUBLIC_API_URL;

export async function POST(req: NextRequest) {
  if (!API_BASE) {
    return NextResponse.json(
      { detail: "NEXT_PUBLIC_API_URL is not set. Set it to your FastAPI base (e.g., http://localhost:8000 in local dev or http://backend:8000 in Docker Compose)." },
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
  if (!API_BASE) {
    return NextResponse.json(
      { detail: "NEXT_PUBLIC_API_URL is not set. Set it to your FastAPI base (e.g., http://localhost:8000 in local dev or http://backend:8000 in Docker Compose)." },
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
