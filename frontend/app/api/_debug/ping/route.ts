import { NextResponse } from 'next/server'

export const runtime = 'nodejs'

function apiBase() { 
  return process.env.NEXT_PUBLIC_API_URL?.trim() || 'http://localhost:8000' 
}

export async function GET() {
  if ((process.env.ENABLE_DEBUG_ENDPOINTS || 'false').toLowerCase() !== 'true') {
    return NextResponse.json({ ok: false, error: 'disabled' }, { status: 404 })
  }
  const base = apiBase()
  try {
    const r = await fetch(`${base}/`, { cache: 'no-store' })
    const j = await r.json().catch(() => ({}))
    return NextResponse.json(
      { ok: true, base, backend: j }, 
      { headers: { 'x-proxy-api-base': base } }
    )
  } catch (e: any) {
    return NextResponse.json(
      { ok: false, base, error: e?.message || 'fetch failed' }, 
      { status: 502, headers: { 'x-proxy-api-base': base } }
    )
  }
}
