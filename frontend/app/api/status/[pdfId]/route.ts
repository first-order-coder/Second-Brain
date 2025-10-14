import { NextRequest, NextResponse } from "next/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL?.trim();

function isAbsolute(u?: string | null) {
  if (!u) return false;
  try { new URL(u); return true; } catch { return false; }
}

export async function GET(
  req: NextRequest,
  { params }: { params: { pdfId: string } }
) {
  if (!isAbsolute(API_BASE)) {
    return NextResponse.json(
      { detail: "NEXT_PUBLIC_API_URL is not set to an absolute URL." },
      { status: 500 }
    );
  }

  try {
    const r = await fetch(`${API_BASE}/status/${params.pdfId}`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    let data: any;
    try { data = await r.json(); } catch { data = { detail: "Backend returned non-JSON." }; }

    return NextResponse.json(data, { status: r.status });
  } catch (e: any) {
    return NextResponse.json(
      { detail: `Proxy could not reach ${API_BASE}/status/${params.pdfId}.` },
      { status: 502 }
    );
  }
}
