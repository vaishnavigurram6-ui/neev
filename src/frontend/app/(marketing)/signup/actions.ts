'use server';

// Sign-up runs through one server action, so validation happens where it cannot
// be skipped and the session cookie is set by the server that issues it.
//
// The backend is the authority on every rule here -- username shape, password
// length, whether a name is taken. This re-states the cheap ones so the visitor
// gets an answer on the field rather than a form-level message, and re-states
// nothing the backend does not also enforce: a check only on this side is not a
// check.
//
// A new account is a borrower with a new loan, and the response says which. The
// role is never in the request: staff access to the whole book is not
// self-served, and a `role` field would be a privilege the caller got to claim.

import { redirect } from 'next/navigation';
import { ApiError, apiSignup } from '@/lib/api';
import type { SignupField, SignupState, SignupValues } from './state';

const API_TIMEOUT_MS = 12000;
const TIMED_OUT = Symbol('timed-out');

function withTimeout<T>(work: Promise<T>): Promise<T | typeof TIMED_OUT> {
  return Promise.race([
    work,
    new Promise<typeof TIMED_OUT>((resolve) => setTimeout(() => resolve(TIMED_OUT), API_TIMEOUT_MS)),
  ]);
}

interface SignupResponse {
  role?: unknown;
  loan_id?: unknown;
}

function field(formData: FormData, name: string): string {
  const value = formData.get(name);
  return typeof value === 'string' ? value.trim() : '';
}

/** Digits only, so "32,00,000" and "₹32,00,000" are accepted as typed. Indian
 *  digit grouping is what a borrower will write, and rejecting it as
 *  non-numeric would be the form's fault, not theirs. */
function rupees(raw: string): number | null {
  const digits = raw.replace(/[^0-9]/g, '');
  if (!digits) return null;
  const value = Number(digits);
  return Number.isSafeInteger(value) && value > 0 ? value : null;
}

const USERNAME_RE = /^[a-z0-9][a-z0-9._-]{2,39}$/;

export async function signupAction(
  _previous: SignupState,
  formData: FormData
): Promise<SignupState> {
  const values: SignupValues = {
    name: field(formData, 'name'),
    username: field(formData, 'username').toLowerCase(),
    locality: field(formData, 'locality'),
    sanctioned: field(formData, 'sanctioned'),
    built_up_sqft: field(formData, 'built_up_sqft'),
  };
  const password = field(formData, 'password');

  const reject = (f: SignupField, message: string): SignupState => ({
    values,
    error: { field: f, message },
  });

  if (values.name.length < 2) return reject('name', 'Enter your full name.');
  if (!USERNAME_RE.test(values.username)) {
    return reject(
      'username',
      'Use 3 or more lowercase letters, numbers, dots, dashes or underscores.'
    );
  }
  if (password.length < 8) return reject('password', 'Use at least 8 characters.');
  if (values.locality.length < 2) return reject('locality', 'Where is the plot?');

  const sanctioned = rupees(values.sanctioned);
  if (sanctioned === null) return reject('sanctioned', 'Enter the sanctioned amount.');

  // Optional, so only a value that was typed and is unusable is an error.
  let builtUp: number | null = null;
  if (values.built_up_sqft) {
    builtUp = rupees(values.built_up_sqft);
    if (builtUp === null) return reject('built_up_sqft', 'Enter the area in square feet.');
  }

  let loanId = '';
  try {
    const body = await withTimeout(
      apiSignup<SignupResponse | undefined>({
        name: values.name,
        username: values.username,
        password,
        locality: values.locality,
        sanctioned,
        built_up_sqft: builtUp,
      })
    );
    // No answer inside the window is not permission to sign someone in.
    if (body === TIMED_OUT) {
      return reject('form', 'We could not create your account just now. Please try again.');
    }
    if (typeof body?.loan_id === 'string' && body.loan_id) loanId = body.loan_id;
  } catch (cause) {
    if (!(cause instanceof ApiError)) throw cause;
    // 409 is a taken or reserved username and belongs on that field; 422 is a
    // rule this action did not re-state, so show what the backend said.
    if (cause.status === 409) return reject('username', 'That username is taken. Try another.');
    if (cause.status === 422) return reject('form', cause.message);
    return reject('form', 'We could not create your account just now. Please try again.');
  }

  if (!loanId) {
    return reject('form', 'We could not create your account just now. Please try again.');
  }

  // Straight to their own contract screen, which is honestly empty until they
  // upload a BoQ. Throws NEXT_REDIRECT; it must stay outside the try above.
  redirect(`/owner/loans/${loanId}/boq`);
}
