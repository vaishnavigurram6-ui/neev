'use server';

// "Send 4 questions" — the one write this screen makes.
//
// A server action is a real public endpoint, so `loanId` arriving in the form is
// untrusted input: it is checked against the session's own loan before anything
// is posted. Without that check, any signed-in owner could stamp another
// borrower's questions as sent — the middleware only guards page navigations,
// not action invocations.
//
// The POST itself is idempotent on the backend (`routes/loans.py` only moves
// questions out of `draft`), so a double click reports the same count twice
// rather than sending anything twice.
//
// The state type lives in `state.ts`, not here: this module may only export
// async functions.

import { revalidatePath } from 'next/cache';
import { ApiError, apiPost } from '@/lib/api';
import { readSession } from '@/lib/session';
import type { SendQuestionsState } from './state';

const COPY = {
  notYours: 'These questions belong to a different loan than the one you are signed in for.',
  unreachable:
    'We could not reach the service just now, so nothing was sent. Your questions are still saved — try again in a moment.',
  refused: 'We could not send your questions just now. Nothing was sent — please try again.',
};

interface SendResponse {
  sent?: unknown;
}

export async function sendQuestionsAction(
  _previous: SendQuestionsState,
  formData: FormData
): Promise<SendQuestionsState> {
  const raw = formData.get('loanId');
  const loanId = typeof raw === 'string' ? raw : '';

  const session = await readSession();
  if (!session || session.role !== 'owner' || session.loanId !== loanId) {
    return { status: 'error', sent: null, message: COPY.notYours };
  }

  let sent: number | null = null;
  try {
    const body = await apiPost<SendResponse | undefined>(
      `/api/loans/${encodeURIComponent(loanId)}/questions/send`
    );
    sent = typeof body?.sent === 'number' ? body.sent : null;
  } catch (cause) {
    if (!(cause instanceof ApiError)) throw cause;
    // Status 0 is "the request never left this process" — nothing listening.
    // Anything else is a service that answered and refused.
    return {
      status: 'error',
      sent: null,
      message: cause.status === 0 ? COPY.unreachable : COPY.refused,
    };
  }

  // Outside the POST's try on purpose, and swallowed: the questions are already
  // sent by this point, so a cache failure must not report "nothing was sent"
  // and must not fail the action. The worst it can cost is a rail that shows
  // "Draft" until the next navigation.
  try {
    revalidatePath(`/owner/loans/${loanId}/boq`);
  } catch {
    // Nothing to recover: the send succeeded, only the cache hint was lost.
  }
  return { status: 'sent', sent, message: null };
}
