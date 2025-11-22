import { NextRequest, NextResponse } from "next/server";
import { getApiBase, isAbsoluteUrl } from '@/lib/getApiBase';

export async function GET(req: NextRequest) {
  let API_BASE: string;
  try {
    API_BASE = getApiBase();
  } catch (error) {
    return NextResponse.json(
      {
        detail: error instanceof Error ? error.message : "NEXT_PUBLIC_API_BASE_URL is not set.",
        got: null,
      },
      { status: 500 }
    );
  }
  
  if (!isAbsoluteUrl(API_BASE)) {
    return NextResponse.json(
      {
        detail: "NEXT_PUBLIC_API_BASE_URL is not set to an absolute URL. Set it to your FastAPI base, e.g., http://localhost:8000 (dev) or https://your-backend.onrender.com (prod).",
        got: API_BASE ?? null,
      },
      { status: 500 }
    );
  }

  const { searchParams } = new URL(req.url);
  const url = searchParams.get('url');

  if (!url) {
    return NextResponse.json(
      { detail: "Missing 'url' query parameter" },
      { status: 400 }
    );
  }

  try {
    const r = await fetch(`${API_BASE}/youtube/tracks?url=${encodeURIComponent(url)}`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    let data: any;
    try { data = await r.json(); } catch { data = { detail: "Backend returned non-JSON." }; }

    return NextResponse.json(data, { status: r.status });
  } catch (e: any) {
    return NextResponse.json(
      { detail: `Proxy could not reach ${API_BASE}/youtube/tracks. Check NEXT_PUBLIC_API_URL, container networking, and that FastAPI listens on 0.0.0.0:8000.` },
      { status: 502 }
    );
  }
}
