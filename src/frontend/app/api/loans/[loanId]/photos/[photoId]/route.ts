// Same-origin passthrough for one site photograph.
//
// A relay and not an endpoint: the bytes come from the backend unchanged. It
// exists because the backend is not reachable from a browser at all
// (NEEV_API_BASE is deliberately not a NEXT_PUBLIC_ variable) and because the
// session cookie is httpOnly, so only the server can carry it upstream.
//
// The access decision is the backend's `AuthorizedLoan`: a lender reads any
// loan in the book, an owner only their own, and the photo is looked up inside
// that loan rather than by id. This side adds no rule of its own beyond
// refusing an obviously malformed path, so there is one place where the
// boundary lives.
import { isLoanId } from '@/components/owner/loan-facts';
import { API_BASE, sessionCookieHeader } from '@/lib/api';

export const dynamic = 'force-dynamic';

const TIMEOUT_MS = 15_000;

/** What the backend will serve. An unexpected type is passed through as a
 *  download rather than as something a browser will render. */
const IMAGE = /^image\/(jpeg|png|webp)$/;

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ loanId: string; photoId: string }> }
): Promise<Response> {
  const { loanId, photoId } = await params;
  if (!isLoanId(loanId) || !/^[1-9]\d{0,11}$/.test(photoId)) {
    return Response.json({ detail: 'Not a photograph.' }, { status: 400 });
  }

  const cookie = await sessionCookieHeader();
  if (!cookie) return Response.json({ detail: 'Sign in to view site photos.' }, { status: 401 });

  let upstream: Response;
  try {
    upstream = await fetch(`${API_BASE}/api/loans/${loanId}/photos/${photoId}`, {
      headers: { cookie },
      cache: 'no-store',
      signal: AbortSignal.timeout(TIMEOUT_MS),
    });
  } catch {
    return Response.json({ detail: 'Could not reach the photo store.' }, { status: 502 });
  }

  if (!upstream.ok) {
    // Forward the status so an <img> for a photo that is gone fails as a 404
    // rather than as a 200 carrying an error document.
    return new Response(null, { status: upstream.status });
  }

  const type = upstream.headers.get('content-type') ?? '';
  return new Response(upstream.body, {
    status: 200,
    headers: {
      'content-type': IMAGE.test(type) ? type : 'application/octet-stream',
      // Private: this is somebody's house being built, not a public asset.
      'cache-control': 'private, max-age=3600',
      'x-content-type-options': 'nosniff',
      ...(IMAGE.test(type) ? {} : { 'content-disposition': 'attachment' }),
    },
  });
}
