'use server';

// Login runs through one server action, so validation happens where it cannot be
// skipped and the session cookie is set by the server that issues it.
//
// Two boundaries meet here:
//
//   * `POST /api/auth/session` (spec §5.2 — "role + phone, sets cookie") is the
//     real contract, called through lib/api.ts like every other endpoint. The
//     backend's own Set-Cookie header cannot reach the browser from a
//     server-to-server fetch, so this action writes `neev_session` itself in the
//     format lib/session.ts parses: "role:loanId:name".
//   * When the endpoint is not there — nothing listening (ApiError status 0), or
//     a backend without the auth route yet (404) — the action falls back to a
//     local session so the screens stay reachable. A backend that answers and
//     *refuses*, or does not answer in time, is a different thing entirely and
//     surfaces as an inline error: that is a real rejection, not an absence.
//
// There is no "send the OTP" endpoint and no OTP to send — real SMS is explicitly
// out of scope (spec §9) — so step one only validates the number. Any six digits
// are accepted in step two; nothing here is a secret, and nothing pretends to be.

import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import { ApiError, apiPost } from '@/lib/api';
import { SESSION_COOKIE, type Role } from '@/lib/session';
import type { LoginState } from './state';

/** The golden demo case, and the only owner loan the fixtures know. Used when the
 *  backend does not name one. */
const GOLDEN_LOAN_ID = '1001';
const SESSION_MAX_AGE_SECONDS = 60 * 60 * 8;

/** Indian mobile numbers are ten digits and start 6-9. */
const MOBILE = /^[6-9]\d{9}$/;

/** lib/api.ts sets no timeout, and `fetch` has none by default. That is fine for
 *  a service that answers or refuses, but 127.0.0.1:8000 in development is just as
 *  likely to be occupied by something that accepts the connection and never
 *  replies — in which case the login form would spin for as long as the visitor
 *  is willing to watch it. Racing the call turns that into a reported failure.
 *  Generous enough to survive a cold start, since it reports rather than retries.
 *  The abandoned fetch is not cancellable from here (apiPost takes no signal),
 *  but nothing is waiting on it. */
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
  return typeof value === 'string' ? value : '';
}

/** Accepts what people actually type: "+91 98490 12345", "098490-12345",
 *  "9849012345". Returns the bare ten digits, or whatever is left if it is not a
 *  recognisable number — the caller reports that, rather than guessing. */
function normalizePhone(raw: string): string {
  const digits = raw.replace(/\D+/g, '');
  if (digits.length === 12 && digits.startsWith('91')) return digits.slice(2);
  if (digits.length === 11 && digits.startsWith('0')) return digits.slice(1);
  return digits;
}

function roleFrom(value: string): Role {
  return value === 'bank' ? 'bank' : 'owner';
}

/** Where to land after a successful login.
 *
 *  `next` is attacker-controlled (the middleware puts it in the URL, but anyone
 *  can), so it is only honoured when it is a path on this origin *and* inside the
 *  signed-in role's own tree. Otherwise the role's home wins. Without the second
 *  check an owner following a stale `?next=/bank/portfolio` would be redirected
 *  straight back to /login by the middleware — a loop that looks like a broken
 *  login rather than a rejected link.
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

export async function loginAction(previous: LoginState, formData: FormData): Promise<LoginState> {
  const role = roleFrom(field(formData, 'role'));
  const next = field(formData, 'next');
  const intent = field(formData, 'intent');

  // Enter-key submits carry the first submit button's name/value, so `intent` is
  // normally present; deriving it from the previous step keeps a no-JS or
  // hand-built POST honest rather than crashing.
  const action =
    intent === 'verify' || intent === 'change-number'
      ? intent
      : intent === 'send-code'
        ? intent
        : previous.step === 'code'
          ? 'verify'
          : 'send-code';

  if (action === 'change-number') {
    return { step: 'phone', role, phone: previous.phone, error: null };
  }

  const typed = field(formData, 'phone');
  const phone = normalizePhone(typed || previous.phone);

  if (action === 'send-code') {
    if (!phone) {
      return {
        step: 'phone',
        role,
        phone: '',
        error: { field: 'phone', message: 'Enter your mobile number.' },
      };
    }
    if (!MOBILE.test(phone)) {
      return {
        step: 'phone',
        role,
        phone,
        error: {
          field: 'phone',
          message: 'That is not a 10-digit mobile number. Indian numbers start with 6, 7, 8 or 9.',
        },
      };
    }
    return { step: 'code', role, phone, error: null };
  }

  // action === 'verify'
  if (!MOBILE.test(phone)) {
    return {
      step: 'phone',
      role,
      phone,
      error: { field: 'phone', message: 'Enter your mobile number.' },
    };
  }

  const code = field(formData, 'code').replace(/\D+/g, '');
  if (code.length !== 6) {
    return {
      step: 'code',
      role,
      phone,
      error: { field: 'code', message: 'Enter the 6-digit code, all six digits.' },
    };
  }

  let loanId = GOLDEN_LOAN_ID;
  // Empty is deliberate: lib/session.ts fills in the role's display name, so an
  // offline login invents no borrower.
  let name = '';
  // The role the *backend* grants, once it is able to. The submitted role is only
  // a request: a phone number belongs to one side of the table, and the service
  // that knows which is the one that should say. Until it does, the toggle wins,
  // which is the mocked half of "mocked session, real boundary" (spec §2).
  let granted = role;

  const failed: LoginState = {
    step: 'code',
    role,
    phone,
    error: {
      field: 'form',
      message: 'We could not sign you in just now. Please try again in a moment.',
    },
  };

  try {
    const body = await withTimeout(
      apiPost<AuthSessionResponse | undefined>('/api/auth/session', { role, phone })
    );
    // No answer inside the window is not permission to sign someone in: a slow
    // backend may be a healthy backend about to refuse this number. Only a
    // request that never left the process (status 0, below) is treated as absent.
    if (body === TIMED_OUT) return failed;
    if (typeof body?.loan_id === 'string' && body.loan_id) loanId = body.loan_id;
    if (typeof body?.name === 'string') name = body.name;
    if (body?.role === 'owner' || body?.role === 'bank') granted = body.role;
  } catch (cause) {
    if (!(cause instanceof ApiError)) throw cause;

    // status 0 — nothing is listening, so there is nothing to disagree with.
    // 404 — something is listening but the auth route does not exist yet: it
    // lands in plan Task 12, which is being built in parallel with this screen.
    // Both fall through to a local session so the screens stay reachable; both
    // are development states, and neither can happen once Task 12 has merged.
    const endpointAbsent = cause.status === 0 || cause.status === 404;
    if (!endpointAbsent) return failed;
    console.warn(
      `[login] POST /api/auth/session unavailable (status ${cause.status}) — issuing a local ${role} session. Once the backend's auth route exists this branch should never run.`
    );
  }

  const store = await cookies();
  // The name is percent-encoded because the cookie is colon-separated and
  // lib/session.ts decodes it; a name containing ":" must not shift the fields.
  store.set(SESSION_COOKIE, `${granted}:${loanId}:${encodeURIComponent(name)}`, {
    httpOnly: true,
    sameSite: 'lax',
    path: '/',
    maxAge: SESSION_MAX_AGE_SECONDS,
    secure: process.env.NODE_ENV === 'production',
  });

  // Throws NEXT_REDIRECT; it must stay outside the try above.
  redirect(destinationFor(granted, loanId, next));
}
