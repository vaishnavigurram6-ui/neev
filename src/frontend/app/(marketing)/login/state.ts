// The login form's state, shared by the client form and the server action.
//
// It lives in its own module because `actions.ts` carries the `'use server'`
// directive, and such a file may only export async functions — a plain
// `initialLoginState` helper there would be a build error.
//
// One step, two fields. It was two steps — a phone number, then a six-digit
// code that accepted any six digits — which could not be narrated honestly and
// mapped every owner onto the same loan however they signed in. Named accounts
// replaced it; see `app/api/accounts.py`.

export interface LoginError {
  /** Which control the message belongs to. `form` is for failures that belong
   *  to neither field — a rejected credential, or an unreachable backend. */
  field: 'username' | 'password' | 'form';
  message: string;
}

export interface LoginState {
  /** Kept across a failed attempt so the visitor does not retype it. The
   *  password is never echoed back. */
  username: string;
  error: LoginError | null;
}

export function initialLoginState(username = ''): LoginState {
  return { username, error: null };
}
