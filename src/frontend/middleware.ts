// Role enforcement at the edge. Owner routes reject bank sessions and vice
// versa. The mock session still exercises this boundary so real auth is a
// drop-in.
import { NextResponse, type NextRequest } from 'next/server';

const SESSION_COOKIE = 'neev_session';

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const needsOwner = pathname.startsWith('/owner');
  const needsBank = pathname.startsWith('/bank');
  if (!needsOwner && !needsBank) return NextResponse.next();

  const raw = request.cookies.get(SESSION_COOKIE)?.value;
  const role = raw?.split(':')[0];

  const wrongRole = (needsOwner && role !== 'owner') || (needsBank && role !== 'bank');
  if (!raw || wrongRole) {
    const url = request.nextUrl.clone();
    url.pathname = '/login';
    url.search = `?next=${encodeURIComponent(pathname + search)}`;
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ['/owner/:path*', '/bank/:path*'],
};
