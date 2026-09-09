// The reply form's state, shared by the client card and the server action.
//
// Its own module because `actions.ts` carries `'use server'`, and such a file
// may only export async functions — a plain `initialReplyState` there would be
// a build error.

export type ReplyAction = 'accept' | 'decline' | 'counter';

export interface ReplyState {
  status: 'idle' | 'ok' | 'error';
  message: string | null;
  /** Which reply landed, so the card can show what the owner did without a
   *  round trip to re-read the row. */
  recorded: ReplyAction | null;
}

export const IDLE: ReplyState = { status: 'idle', message: null, recorded: null };

export function isReplyAction(value: unknown): value is ReplyAction {
  return value === 'accept' || value === 'decline' || value === 'counter';
}

/** "1,25,000" or "125000" -> 125000. Returns null for anything that is not a
 *  whole number of rupees, which the action reports rather than rounding: a
 *  counter is a figure the owner will be held to. */
export function parseRupees(raw: string): number | null {
  const digits = raw.replace(/[\s,₹]/g, '');
  if (!/^\d{1,12}$/.test(digits)) return null;
  return Number(digits);
}
