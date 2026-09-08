'use server';

// Login runs through one server action, so validation happens where it cannot be
// skipped and the session cookie is set by the server that issues it.
//
// Two boundaries meet here:
//
//   * `POST /api/auth/session` (spec §5.2 — "role + phone, sets cookie") is the
//     real contract, called through lib/api.ts like every other endpoint. The
//     backend's own Set-Cookie header cannot reach the browser from a
//     server-to-server fetch, so apiLogin copies its signed cookie unchanged.
//   * An unreachable, slow or rejecting backend is a failed login. There is no
//     locally fabricated session fallback.
//
// There is no "send the OTP" endpoint and no OTP to send — real SMS is explicitly
// out of scope (spec §9) — so step one only validates the number. Any six digits
// are accepted in step two. This is an explicitly enabled synthetic-data sandbox,
// not identity verification; the issued session cookie must still stay private.

import { redirect } from 'next/navigation';
import { ApiError, apiLogin } from '@/lib/api';
import { type Role } from '@/lib/session';
import type { LoginState } from './state';

/** The golden demo case, and the only owner loan the fixtures know. Used when the
 *  backend does not name one. */
const GOLDEN_LOAN_ID = '1001';

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
  // Identity comes from the backend response, never from a locally signed cookie.
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
      apiLogin<AuthSessionResponse | undefined>({ role, phone })
    );
    // No answer inside the window is not permission to sign someone in.
    if (body === TIMED_OUT) return failed;
    if (typeof body?.loan_id === 'string' && body.loan_id) loanId = body.loan_id;
    if (body?.role === 'owner' || body?.role === 'bank') granted = body.role;
  } catch (cause) {
    if (!(cause instanceof ApiError)) throw cause;

    // Network failures and rejected credentials both fail closed.
    return failed;
  }

  // Throws NEXT_REDIRECT; it must stay outside the try above.
  redirect(destinationFor(granted, loanId, next));
}
