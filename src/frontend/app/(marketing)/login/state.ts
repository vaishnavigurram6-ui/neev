// The login form's state, shared by the client form and the server action.
//
// It lives in its own module because `actions.ts` carries the `'use server'`
// directive, and such a file may only export async functions — a plain
// `initialLoginState` helper there would be a build error.
import type { Role } from '@/lib/session';

/** Phone first, then the code. Two steps in one <form>, not two routes: the
 *  number typed in step one must survive step two without a round trip. */
export type LoginStep = 'phone' | 'code';

export interface LoginError {
  /** Which control the message belongs to. `form` is for failures that belong to
   *  neither field — an unreachable or unhappy backend. */
  field: 'phone' | 'code' | 'form';
  message: string;
}

export interface LoginState {
  step: LoginStep;
  role: Role;
  /** Normalised to ten digits, no spaces, no country code. */
  phone: string;
  error: LoginError | null;
}

export function initialLoginState(role: Role): LoginState {
  return { step: 'phone', role, phone: '', error: null };
}

/** "9849012345" -> "98490 12345", the grouping the design shows. Anything that
 *  is not a ten-digit number is returned untouched rather than mangled. */
export function formatPhone(phone: string): string {
  return /^\d{10}$/.test(phone) ? `${phone.slice(0, 5)} ${phone.slice(5)}` : phone;
}
