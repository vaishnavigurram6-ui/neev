// Same-origin passthrough for the analysis stream.
//
// WHY THIS EXISTS. `lib/api.ts` is `server-only` and NEEV_API_BASE is not a
// NEXT_PUBLIC_ variable, so the browser has no address for the backend and must
// not be given one — 127.0.0.1:8021 is the developer's machine, not the reader's.
// The Analyzing screen's `EventSource` therefore opens a URL on this origin and
// this handler relays the bytes. Two things fall out of that for free: the
// session cookie is sent by the browser without `withCredentials`, and there is
// no cross-origin preflight to configure on the FastAPI side.
//
// It is a relay, not an endpoint: no shaping, no buffering, no interpretation of
// the event union. The screen consumes exactly what `app/api/routes/jobs.py`
// publishes.
//
// Both this relay and the backend enforce session and owner/loan authorization;
// knowing a job id alone never grants access to another borrower's findings.
import { isLoanId } from '@/components/owner/loan-facts';
import { API_BASE, ApiError, apiGet, sessionCookieHeader } from '@/lib/api';
import { readSession } from '@/lib/session';

// Never prerendered, never cached: the response is an open socket.
export const dynamic = 'force-dynamic';

// Job ids are `uuid4().hex[:12]` (src/backend/app/services/jobs.py). Validated
// rather than escaped, because this value is interpolated into an upstream URL
// path: without it, a job id of `../loans/1002` would make the frontend a
// confused-deputy proxy for any backend route it can reach.
const JOB_ID = /^[0-9a-f]{6,64}$/;

const SSE_HEADERS = {
  'content-type': 'text/event-stream; charset=utf-8',
  // `no-transform` matters as much as `no-cache`: a proxy that gzips or rewrites
  // the body can hold events back until the buffer fills, which would make the
  // whole screen pointless.
  'cache-control': 'no-cache, no-store, no-transform',
  connection: 'keep-alive',
  'x-accel-buffering': 'no',
};

/** How long the client waits before reopening the stream, in ms. */
const RETRY_HINT_MS = 3000;

interface JobStatus {
  job_id: string;
  loan_id: string;
  status: string;
  error: string | null;
}

/** A 200 `text/event-stream` that says nothing and ends.
 *
 *  Answering a transient backend failure with 503 does NOT do what it looks like
 *  it does: per the HTML spec an EventSource *fails* the connection on any status
 *  other than 200 — readyState goes to CLOSED and it never reconnects. So a
 *  backend restart would show as a permanent "we lost the connection" on the very
 *  first blip. A 200 that closes immediately is an EOF, which IS reconnectable,
 *  and the `retry:` field sets the interval. The screen counts those cycles and
 *  gives up on its own terms after a few. */
function retryLater(reason: string): Response {
  // Leading ":" is an SSE comment — carried for a human reading the wire, never
  // delivered to `onmessage`, so the screen sees a connection that opened and
  // said nothing rather than a bogus event.
  return new Response(`: ${reason}\nretry: ${RETRY_HINT_MS}\n\n`, {
    status: 200,
    headers: SSE_HEADERS,
  });
}

export async function GET(
  request: Request,
  { params }: { params: Promise<{ jobId: string }> }
): Promise<Response> {
  const { jobId } = await params;
  if (!JOB_ID.test(jobId)) {
    return new Response('Not a job id.', { status: 400 });
  }

  const session = await readSession();
  if (session === null) {
    return new Response('No session.', { status: 401 });
  }

  // An owner may follow only their own loan's runs. Without this the 48-bit job
  // id would be the only thing standing between one borrower and another's
  // findings feed — and ids are handed out in a redirect URL, which is exactly
  // the sort of thing that gets pasted into a chat.
  if (session.role === 'owner') {
    if (!isLoanId(session.loanId)) {
      return new Response('Malformed session.', { status: 401 });
    }
    try {
      const job = await apiGet<JobStatus>(`/api/jobs/${jobId}`);
      if (job.loan_id !== session.loanId) {
        return new Response('That check belongs to a different loan.', { status: 403 });
      }
    } catch (cause) {
      if (!(cause instanceof ApiError)) throw cause;
      if (cause.status === 401 || cause.status === 403) {
        return new Response('Session cannot access this job.', { status: cause.status });
      }
      // 404 — the backend has never heard of this job, usually a page reloaded
      // after a restart. Let it through: the stream itself answers with a
      // terminal `done` pointing somewhere real, which is better than a bare 404
      // the screen would have to invent a destination for.
      if (cause.status !== 404) return retryLater('job status unavailable');
    }
  }

  let upstream: Response;
  try {
    // Read through `cookies()`, not off this request's own header — see
    // `sessionCookieHeader`. Forwarding the raw header sent the backend a
    // percent-encoded value it read as no session at all.
    const cookie = await sessionCookieHeader();
    upstream = await fetch(`${API_BASE}/api/jobs/${jobId}/events`, {
      headers: {
        accept: 'text/event-stream',
        ...(cookie ? { cookie } : {}),
      },
      cache: 'no-store',
      // The reader navigating away or closing the tab aborts this fetch, which
      // drops the upstream subscriber instead of leaving it following a job
      // nobody is watching.
      signal: request.signal,
    });
  } catch {
    return retryLater('backend unreachable');
  }

  if (!upstream.ok || upstream.body === null) {
    if (upstream.status === 401 || upstream.status === 403) {
      return new Response('Session cannot access this job.', { status: upstream.status });
    }
    return retryLater(`backend answered ${upstream.status}`);
  }

  return new Response(upstream.body, { status: 200, headers: SSE_HEADERS });
}
