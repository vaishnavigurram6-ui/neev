'use server';

// Session actions behind the profile chip.
//
// The chip was a styled <div> — the prototype gives it `cursor: pointer` and
// nothing behind it, so it looked clickable and was not. It is the obvious place
// for the two things a signed-in person actually wants, and switching sides is
// the one a demo needs constantly: without it, moving between the owner's view
// and the bank console means going back to /login and re-entering a number.
//
// Both actions go through the same cookie the login flow writes, so the boundary
// stays real: proxy.ts still enforces role and per-loan access on every request,
// and nothing here can grant something login could not.

import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import { SESSION_COOKIE, type Role } from './session';

/** Swap sides of the table, keeping the same loan in view. */
export async function switchRoleAction(formData: FormData): Promise<void> {
  const requested: Role = formData.get('to') === 'bank' ? 'bank' : 'owner';
  (await cookies()).delete(SESSION_COOKIE);
  redirect(`/login?role=${requested}`);
}

export async function logOutAction(): Promise<void> {
  (await cookies()).delete(SESSION_COOKIE);
  redirect('/');
}
