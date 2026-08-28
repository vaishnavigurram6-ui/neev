// Server-side fetch against the FastAPI backend. No screen calls fetch directly.
//
// `server-only` is a build-time fence: NEEV_API_BASE is not NEXT_PUBLIC_, so an
// accidental client import would inline the fallback and have the viewer's own
// browser call 127.0.0.1:8000. Better a build error than a silent one.
import 'server-only';

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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const method = init?.method ?? 'GET';

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { 'content-type': 'application/json', ...(init?.headers ?? {}) },
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

export function apiPost<T>(path: string, body?: unknown): Promise<T> {
  // `body !== undefined`, not a truthiness test: `false`, `0` and `""` are all
  // valid JSON documents, and dropping them while still sending
  // `content-type: application/json` makes FastAPI answer 422.
  return request<T>(path, {
    method: 'POST',
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}
