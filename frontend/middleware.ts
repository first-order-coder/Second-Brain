import { NextResponse, type NextRequest } from 'next/server';
import { updateSession } from '@/lib/supabase/middleware';

const PROTECTED_PATHS = ['/saved', '/profile'];

export async function middleware(request: NextRequest) {
  const url = request.nextUrl.clone();

  if (PROTECTED_PATHS.some((path) => url.pathname.startsWith(path))) {
    const hasSession =
      request.cookies.has('sb-access-token') ||
      request.cookies.has('sb-refresh-token');

    if (!hasSession) {
      url.pathname = '/auth';
      return NextResponse.redirect(url);
    }
  }

  return await updateSession(request);
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
};
