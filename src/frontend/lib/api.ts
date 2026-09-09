// Server-side fetch against the FastAPI backend. No screen calls fetch directly.
//
// `server-only` is a build-time fence: NEEV_API_BASE is not NEXT_PUBLIC_, so an
// accidental client import would inline the fallback and have the viewer's own
// browser call 127.0.0.1:8000. Better a build error than a silent one.
import 'server-only';
import { cookies } from 'next/headers';

export const API_BASE = process.env.NEEV_API_BASE ?? 'http://127.0.0.1:8000';

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    /** The backend's response body, when there was one. FastAPI's `detail` is
     *  often the only thing that can say why a request was rejected. */
    readonly detail?: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

// fetch has no default timeout. A process that accepts the connection and
// never answers wedges every screen that calls it — this actually happened in
// development, when an unrelated local service was listening on the API port.
// Any request that has not answered by then fails as an unreachable backend,
// which the screens already render as an error state with a retry.
const REQUEST_TIMEOUT_MS = 8000;

/** The `cookie` header that carries this visitor's session to the backend, or
 *  undefined when there is no session.
 *
 *  ALWAYS read the session through `cookies()`, NEVER by forwarding the raw
 *  `cookie` header off an incoming request. Next percent-encodes cookie values
 *  when it writes them, so the header a browser sends holds
 *  `neev_session=owner%3A1001%3AUmF2aSBLdW1hcg%3A...` while the backend signs
 *  and parses `owner:1001:UmF2aSBLdW1hcg:...`. `cookies()` decodes on read; a
 *  forwarded raw header does not, and `_parse_cookie` then finds no colons at
 *  all and reads it as *no session* — which surfaced as the BoQ upload failing
 *  with "No session. Sign in at POST /api/auth/session." for a signed-in owner.
 *  Pinned by tests/session-forwarding.test.mjs. */
export async function sessionCookieHeader(): Promise<string | undefined> {
  const cookie = (await cookies()).get('neev_session');
  return cookie ? `neev_session=${cookie.value}` : undefined;
}

async function request<T>(path: string, init?: RequestInit, onResponse?: (response: Response) => Promise<void>): Promise<T> {
  const method = init?.method ?? 'GET';
  const cookie = await sessionCookieHeader();
  const headers = new Headers(init?.headers);
  headers.set('content-type', 'application/json');
  if (cookie) headers.set('cookie', cookie);

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers,
      // Loan data is private and changes on every decision; never cache it.
      cache: 'no-store',
      signal: init?.signal ?? AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });
  } catch (cause) {
    // A refused connection or DNS failure rejects with TypeError, not ApiError —
    // and that is the most common failure in local development. Status 0 means
    // "the request never reached the backend".
    throw new ApiError(
      `${method} ${path} could not reach the backend at ${API_BASE}`,
      0,
      cause instanceof Error ? cause.message : undefined
    );
  }

  const text = await response.text();

  if (!response.ok) {
    throw new ApiError(`${method} ${path} failed: ${response.status}`, response.status, text);
  }
  if (onResponse) await onResponse(response);

  // A 204, or any successful empty body, is a valid response — not a parse
  // failure. `undefined as T` keeps `apiPost<void>` honest.
  if (text.length === 0) return undefined as T;

  try {
    return JSON.parse(text) as T;
  } catch {
    throw new ApiError(`${method} ${path} returned a body that is not JSON`, response.status, text);
  }
}

export function apiGet<T>(path: string): Promise<T> {
  return request<T>(path);
}

/** Only the backend issues sessions. No offline or client-authored fallback. */
export function apiLogin<T>(body: unknown): Promise<T> {
  return request<T>('/api/auth/session', { method: 'POST', body: JSON.stringify(body) }, async (response) => {
    const value = response.headers.get('set-cookie')?.match(/(?:^|,\s*)neev_session=([^;]+)/)?.[1];
    if (!value) throw new ApiError('Backend did not issue a session', 502);
    (await cookies()).set('neev_session', value, {
      httpOnly: true, sameSite: 'lax', path: '/', maxAge: 43200,
      secure: process.env.NODE_ENV === 'production',
    });
  });
}

/** Sign-up, which also issues a session -- so it copies the cookie exactly the
 *  way apiLogin does. Same reason: the backend's Set-Cookie cannot reach the
 *  browser from a server-to-server fetch, so the server action re-issues it. */
export function apiSignup<T>(body: unknown): Promise<T> {
  return request<T>('/api/auth/signup', { method: 'POST', body: JSON.stringify(body) }, async (response) => {
    const value = response.headers.get('set-cookie')?.match(/(?:^|,\s*)neev_session=([^;]+)/)?.[1];
    if (!value) throw new ApiError('Backend did not issue a session', 502);
    (await cookies()).set('neev_session', value, {
      httpOnly: true, sameSite: 'lax', path: '/', maxAge: 43200,
      secure: process.env.NODE_ENV === 'production',
    });
  });
}

/** All reads and writes forward the caller's session; headers may carry idempotency keys. */
export function apiPost<T>(
  path: string,
  body?: unknown,
  headers?: Record<string, string>
): Promise<T> {
  // `body !== undefined`, not a truthiness test: `false`, `0` and `""` are all
  // valid JSON documents, and dropping them while still sending
  // `content-type: application/json` makes FastAPI answer 422.
  return request<T>(path, {
    method: 'POST',
    body: body !== undefined ? JSON.stringify(body) : undefined,
    headers,
  });
}
