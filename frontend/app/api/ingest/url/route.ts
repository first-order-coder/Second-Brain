import { NextRequest, NextResponse } from 'next/server'

export const runtime = 'nodejs'

function apiBase() {
  return process.env.NEXT_PUBLIC_API_URL?.trim() || 'http://localhost:8000'
}

async function forwardJSON(path: string, init: RequestInit) {
  const base = apiBase()
  const ctl = new AbortController()
  const t = setTimeout(() => ctl.abort(), 12000)
  try {
    const res = await fetch(`${base}${path}`, { ...init, signal: ctl.signal })
    const ct = res.headers.get('content-type') || ''
    const body = ct.includes('application/json') ? await res.json() : await res.text()
    return new NextResponse(typeof body === 'string' ? body : JSON.stringify(body), {
      status: res.status,
      headers: { 'content-type': ct || 'application/json', 'x-proxy-api-base': base }
    })
  } catch (e: any) {
    return NextResponse.json(
      { error: 'fetch failed', detail: `Failed to connect to backend API at ${base}. ${e?.message || ''}` },
      { status: 502, headers: { 'x-proxy-api-base': base } }
    )
  } finally {
    clearTimeout(t)
  }
}

export async function OPTIONS() { 
  return NextResponse.json({}, { status: 200 }) 
}

export async function POST(req: NextRequest) {
  const body = await req.text()
  return forwardJSON('/ingest/url', { 
    method: 'POST', 
    headers: { 'content-type': 'application/json' }, 
    body 
  })
}
