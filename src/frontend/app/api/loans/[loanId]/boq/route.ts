// Same-origin passthrough for the BoQ upload.
//
// WHY THIS IS NOT A SERVER ACTION. The wizard's natural shape is
// `useActionState` + a server action, as `(marketing)/login` uses. It cannot be:
// Next caps a server action's request body at 1 MB by default, and this body is
// the owner's BoQ — a scanned PDF, an Excel workbook, or, as the dropzone
// promises in so many words, "just photos of the pages". Raising the cap is a
// change to `next.config.ts`, which every other screen shares. A route handler
// has no such cap and streams the body straight through, so the limit that
// applies is the backend's, which is where it belongs.
//
// Like the SSE relay next door this is a relay and not an endpoint: the
// multipart body is forwarded untouched and the backend's JSON answer is
// returned verbatim, status included.
//
// AND, UNLIKE IT, THIS ONE WRITES. A finished run persists a new `BoqRevision`,
// so an open POST here would let anyone spawn analysis jobs against any loan in
// the book and add revisions to it. `proxy.ts` does not match `/api/*`, and the
// backend allows anonymous requests on the stated grounds that the frontend's
// middleware gates them — so the session check below is not belt-and-braces, it
// is the only gate on the path.
import { isLoanId } from '@/components/owner/loan-facts';
import { API_BASE } from '@/lib/api';
import { readSession } from '@/lib/session';

export const dynamic = 'force-dynamic';

// Generous enough for a multi-megabyte scan on a domestic uplink: paired with the
// wizard's 20 MB ceiling this is about 0.9 Mbps sustained, and `AbortSignal`
// covers the request body as well as the answer. Short enough that a wedged
// backend does not hold the wizard open indefinitely.
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
    return Response.json({ detail: 'Sign in to upload a BoQ.' }, { status: 401 });
  }
  // A lender legitimately works across the book; an owner has exactly one loan.
  // The same asymmetry as `get_authorized_loan` on the backend.
  if (session.role === 'owner' && session.loanId !== loanId) {
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
    const cookie = request.headers.get('cookie');
    const upstream = await fetch(`${API_BASE}/api/loans/${loanId}/boq`, {
      method: 'POST',
      // The multipart boundary lives in the incoming content-type header, so it
      // has to be forwarded with the body it describes.
      headers: {
        'content-type': contentType,
        ...(cookie ? { cookie } : {}),
      },
      body: request.body,
      // Required by the fetch spec whenever the body is a stream rather than a
      // buffer; without it undici rejects the request outright.
      duplex: 'half',
      cache: 'no-store',
      signal: AbortSignal.timeout(UPLOAD_TIMEOUT_MS),
    } as RequestInit & { duplex: 'half' });

    // Inside the try: the timeout covers the response phase too, and an upstream
    // that dies after sending headers throws here. Outside, that would surface as
    // Next's HTML error page to a caller expecting JSON.
    const body = await upstream.text();
    return new Response(body, {
      status: upstream.status,
      headers: { 'content-type': upstream.headers.get('content-type') ?? 'application/json' },
    });
  } catch {
    return Response.json(
      { detail: 'We could not reach the service that reads your BoQ.' },
      { status: 502 }
    );
  }
}
