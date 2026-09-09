// Same-origin passthrough for a reported milestone: the stage, the photos, and
// the note that goes with them.
//
// A route handler and not a server action, for the same reason as the BoQ
// upload next door: Next caps a server action's body at 1 MB by default and
// this body is three site photographs. A route handler has no such cap and
// streams the body straight through, so the limit that applies is the
// backend's — 10 MB per file, one to six files — which is where it belongs.
//
// AND IT WRITES. A reported milestone flips the tranche to needs-human-review
// and puts photographs into the loan file, so the session check below is not
// belt-and-braces: `proxy.ts` does not match `/api/*`, which makes this the
// only gate in front of it on this side.
import { isLoanId } from '@/components/owner/loan-facts';
import { API_BASE, sessionCookieHeader } from '@/lib/api';
import { readSession } from '@/lib/session';

export const dynamic = 'force-dynamic';

// Matched to the BoQ relay: three downscaled photographs on a domestic Indian
// uplink, with room for a slow one.
const UPLOAD_TIMEOUT_MS = 180_000;

export async function POST(
  request: Request,
  { params }: { params: Promise<{ loanId: string }> }
): Promise<Response> {
  const { loanId } = await params;
  if (!isLoanId(loanId)) {
    return Response.json({ detail: 'Not a loan id.' }, { status: 400 });
  }

  const session = await readSession();
  if (session === null) {
    return Response.json({ detail: 'Sign in to report a milestone.' }, { status: 401 });
  }
  // Reporting progress is the borrower's act. A lender reads the book; it does
  // not file evidence on somebody's behalf.
  if (session.role !== 'owner') {
    return Response.json(
      { detail: 'Only the borrower can report a milestone.' },
      { status: 403 }
    );
  }
  if (session.loanId !== loanId) {
    return Response.json(
      { detail: `This session is signed in for loan ${session.loanId}.` },
      { status: 403 }
    );
  }

  const contentType = request.headers.get('content-type');
  if (contentType === null || !contentType.startsWith('multipart/form-data')) {
    return Response.json({ detail: 'Expected a multipart upload.' }, { status: 415 });
  }

  try {
    const cookie = await sessionCookieHeader();
    const upstream = await fetch(`${API_BASE}/api/loans/${loanId}/milestones`, {
      method: 'POST',
      // The multipart boundary lives in the content-type header, so it travels
      // with the body it describes.
      headers: { 'content-type': contentType, ...(cookie ? { cookie } : {}) },
      body: request.body,
      // Required by the fetch spec whenever the body is a stream.
      duplex: 'half',
      cache: 'no-store',
      signal: AbortSignal.timeout(UPLOAD_TIMEOUT_MS),
    } as RequestInit & { duplex: 'half' });

    const body = await upstream.text();
    return new Response(body, {
      status: upstream.status,
      headers: { 'content-type': upstream.headers.get('content-type') ?? 'application/json' },
    });
  } catch {
    return Response.json(
      { detail: 'We could not reach the service that records your progress.' },
      { status: 502 }
    );
  }
}
