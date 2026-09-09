'use server';

// Login runs through one server action, so validation happens where it cannot
// be skipped and the session cookie is set by the server that issues it.
//
// Two boundaries meet here:
//
//   * `POST /api/auth/session` — a demo username and the shared demo password —
//     called through lib/api.ts like every other endpoint. The backend's own
//     Set-Cookie header cannot reach the browser from a server-to-server fetch,
//     so apiLogin copies its signed cookie unchanged.
//   * An unreachable, slow or rejecting backend is a failed login. There is no
//     locally fabricated session fallback.
//
// The account decides the destination, not the form: the backend answers with
// the role and the loan the username holds, and this only chooses which of that
// role's screens to open.

import { redirect } from 'next/navigation';
import { ApiError, apiLogin } from '@/lib/api';
import { type Role } from '@/lib/session';
import type { LoginState } from './state';

/** lib/api.ts sets no timeout, and `fetch` has none by default. That is fine
 *  for a service that answers or refuses, but a local port can just as easily
 *  be held by something that accepts the connection and never replies — in
 *  which case the form would spin for as long as the visitor is willing to
 *  watch. Racing the call turns that into a reported failure. */
const API_TIMEOUT_MS = 8000;
const TIMED_OUT = Symbol('timed-out');

function withTimeout<T>(work: Promise<T>): Promise<T | typeof TIMED_OUT> {
  return Promise.race([
    work,
    new Promise<typeof TIMED_OUT>((resolve) => setTimeout(() => resolve(TIMED_OUT), API_TIMEOUT_MS)),
  ]);
}

interface AuthSessionResponse {
  role?: unknown;
  loan_id?: unknown;
  name?: unknown;
}

function field(formData: FormData, name: string): string {
  const value = formData.get(name);
  return typeof value === 'string' ? value.trim() : '';
}

/** Where to land after a successful login.
 *
 *  `next` is attacker-controlled (the middleware puts it in the URL, but anyone
 *  can), so it is only honoured when it is a path on this origin *and* inside
 *  the signed-in role's own tree. Otherwise the role's home wins. Without the
 *  second check an owner following a stale `?next=/bank/portfolio` would be
 *  redirected straight back to /login by the middleware — a loop that looks
 *  like a broken login rather than a rejected link.
 *
 *  Not exported: a `'use server'` module may only export async functions, and
 *  exporting this one would publish it as a callable endpoint. */
function destinationFor(role: Role, loanId: string, next: string): string {
  const fallback = role === 'owner' ? `/owner/loans/${loanId}/boq` : '/bank/portfolio';

  // Must be a same-origin absolute path. `//evil.example` and `/\evil.example`
  // are both protocol-relative URLs in a browser, not paths.
  if (!/^\/(?![\\/])/.test(next)) return fallback;

  const prefix = role === 'owner' ? '/owner' : '/bank';
  if (next !== prefix && !next.startsWith(`${prefix}/`)) return fallback;

  // Owner sessions are scoped to a single loan by the middleware.
  const wantsLoan = /^\/owner\/loans\/([^/?#]+)/.exec(next)?.[1];
  if (wantsLoan !== undefined && wantsLoan !== loanId) return fallback;

  return next;
}

export async function loginAction(_previous: LoginState, formData: FormData): Promise<LoginState> {
  const username = field(formData, 'username');
  const password = field(formData, 'password');
  const next = field(formData, 'next');

  if (!username) {
    return { username, error: { field: 'username', message: 'Enter a username.' } };
  }
  if (!password) {
    return { username, error: { field: 'password', message: 'Enter the password.' } };
  }

  // One message for a wrong username and a wrong password, matching the
  // backend: a login that distinguishes them tells anyone who asks which
  // accounts exist.
  const rejected: LoginState = {
    username,
    error: {
      field: 'form',
      message: 'That username and password do not match a demo account.',
    },
  };
  const unreachable: LoginState = {
    username,
    error: {
      field: 'form',
      message: 'We could not sign you in just now. Please try again in a moment.',
    },
  };

  let role: Role = 'owner';
  let loanId = '';
  try {
    const body = await withTimeout(
      apiLogin<AuthSessionResponse | undefined>({ username, password })
    );
    // No answer inside the window is not permission to sign someone in.
    if (body === TIMED_OUT) return unreachable;
    if (body?.role === 'owner' || body?.role === 'bank') role = body.role;
    if (typeof body?.loan_id === 'string' && body.loan_id) loanId = body.loan_id;
  } catch (cause) {
    if (!(cause instanceof ApiError)) throw cause;
    // 401 is a rejected credential and says so; anything else is the service.
    return cause.status === 401 ? rejected : unreachable;
  }

  if (!loanId) return unreachable;

  // Throws NEXT_REDIRECT; it must stay outside the try above.
  redirect(destinationFor(role, loanId, next));
}
