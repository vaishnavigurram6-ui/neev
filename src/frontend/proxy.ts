// Role enforcement at the edge. Owner routes reject bank sessions and vice
// versa. The mock session still exercises this boundary so real auth is a
// drop-in.
import { NextResponse, type NextRequest } from 'next/server';

const SESSION_COOKIE = 'neev_session';

export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const needsOwner = pathname.startsWith('/owner');
  const needsBank = pathname.startsWith('/bank');
  if (!needsOwner && !needsBank) return NextResponse.next();

  const raw = request.cookies.get(SESSION_COOKIE)?.value;
  const [role, sessionLoanId] = raw?.split(':') ?? [];

  const wrongRole = (needsOwner && role !== 'owner') || (needsBank && role !== 'bank');

  // Role alone is not authorization. Without this, an owner signed in for loan
  // 1001 could read /owner/loans/1002/boq — the role prefix matches and the
  // layout only re-checks the role. A bank officer legitimately reads any loan
  // in the book, so the check is owner-side only.
  const loanInPath = /^\/owner\/loans\/([^/]+)/.exec(pathname)?.[1];
  const wrongLoan = needsOwner && loanInPath !== undefined && loanInPath !== sessionLoanId;

  if (!raw || wrongRole || wrongLoan) {
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
