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
import { SESSION_COOKIE, readSession, type Role } from './session';

const SESSION_MAX_AGE_SECONDS = 60 * 60 * 8;
/** The only loan the fixtures cover, and where an owner session lands. */
const GOLDEN_LOAN_ID = '1001';

function homeFor(role: Role, loanId: string): string {
  return role === 'owner' ? `/owner/loans/${loanId}/boq` : '/bank/portfolio';
}

/** Swap sides of the table, keeping the same loan in view. */
export async function switchRoleAction(formData: FormData): Promise<void> {
  const requested: Role = formData.get('to') === 'bank' ? 'bank' : 'owner';
  const current = await readSession();
  // A bank session carries a loan id only so the cookie's three fields stay
  // aligned; no bank route reads it. Falling back to the golden case keeps the
  // switch working even from a session that never had one.
  const loanId = current?.loanId || GOLDEN_LOAN_ID;

  const store = await cookies();
  // Empty name: lib/session.ts fills in the role's own display name, so
  // switching never carries the owner's name onto the officer's chip.
  store.set(SESSION_COOKIE, `${requested}:${loanId}:`, {
    httpOnly: true,
    sameSite: 'lax',
    path: '/',
    maxAge: SESSION_MAX_AGE_SECONDS,
    secure: process.env.NODE_ENV === 'production',
  });

  redirect(homeFor(requested, loanId));
}

export async function logOutAction(): Promise<void> {
  (await cookies()).delete(SESSION_COOKIE);
  redirect('/');
}
