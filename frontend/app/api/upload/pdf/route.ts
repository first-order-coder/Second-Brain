import { NextRequest, NextResponse } from "next/server";

// Force Node runtime for multipart streaming
export const runtime = "nodejs";

import { getApiBase, isAbsoluteUrl } from '@/lib/getApiBase';

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
  
  if (!isAbsoluteUrl(API_BASE)) {
    return NextResponse.json(
      { detail: "NEXT_PUBLIC_API_BASE_URL is not set to an absolute URL (e.g., http://localhost:8000 or https://your-backend.onrender.com)." },
      { status: 500 }
    );
  }

  // Read incoming multipart form from the browser
  const incoming = await req.formData();

  // Rebuild a fresh FormData to avoid ReadableStream edge cases
  const fd = new FormData();
  const entries = Array.from(incoming.entries());
  for (const [key, value] of entries) {
    // Check if it's a file by looking for the stream method
    if (value && typeof value === 'object' && 'stream' in value && 'name' in value) {
      fd.append(key, value as any, (value as any).name);
    } else {
      fd.append(key, value as string);
    }
  }

  // Forward to FastAPI (DO NOT set Content-Type; fetch will add boundary)
  const r = await fetch(`${API_BASE}/upload-pdf`, {
    method: "POST",
    body: fd,
  });

  // Return backend's JSON + status as-is
  let data: any = null;
  try { data = await r.json(); } catch { data = { detail: "Backend returned non-JSON." }; }
  return NextResponse.json(data, { status: r.status });
}
