import { NextRequest, NextResponse } from "next/server";
import { getApiBase, isAbsoluteUrl } from '@/lib/getApiBase';

export async function GET(
  req: NextRequest,
  { params }: { params: { sourceId: string } }
) {
  let API_BASE: string;
  try {
    API_BASE = getApiBase();
  } catch (error) {
    return NextResponse.json(
      { detail: error instanceof Error ? error.message : "NEXT_PUBLIC_API_BASE_URL is not set." },
      { status: 500 }
    );
  }
  
  if (!isAbsoluteUrl(API_BASE)) {
    return NextResponse.json(
      { detail: "NEXT_PUBLIC_API_BASE_URL is not set to an absolute URL." },
      { status: 500 }
    );
  }

  try {
    const r = await fetch(`${API_BASE}/summaries/${params.sourceId}`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    let data: any;
    try { data = await r.json(); } catch { data = { detail: "Backend returned non-JSON." }; }

    return NextResponse.json(data, { status: r.status });
  } catch (e: any) {
    return NextResponse.json(
      { detail: `Proxy could not reach ${API_BASE}/summaries/${params.sourceId}.` },
      { status: 502 }
    );
  }
}
