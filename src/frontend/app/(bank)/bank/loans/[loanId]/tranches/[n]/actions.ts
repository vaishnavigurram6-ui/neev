'use server';

// The one write in the bank console: an officer's decision on a tranche.
//
// It runs as a server action rather than a client fetch for two reasons. The
// session cookie is httpOnly, so only the server can forward it — and
// `POST /api/loans/{id}/tranches/{n}/decision` refuses an anonymous caller (401)
// and a borrower's session (403), by design: a decision goes into the loan file
// under somebody's name. And the backend is reachable only from the server;
// `NEEV_API_BASE` is deliberately not a NEXT_PUBLIC_ variable.
//
// `loanId` and `tranche` arrive as bound arguments, not form fields: Next
// encrypts bound action arguments, so the loan whose file is being written cannot
// be swapped by editing the DOM. They are re-validated anyway, because the path
// is built from them.
import { revalidatePath } from 'next/cache';
import { cookies } from 'next/headers';
import { ApiError, apiPost } from '@/lib/api';
import { SESSION_COOKIE } from '@/lib/session';
import { isDecisionAction, type DecisionState } from './state';

const RECORDED: Record<string, string> = {
  RELEASE: 'Release recorded. The full evidence trail went to the loan file.',
  HOLD: 'Hold recorded, with the re-scope request. The full evidence trail went to the loan file.',
  ESCALATE:
    'Escalation recorded. The full evidence trail went to the loan file for the physical inspection.',
};

const FAILED = 'The decision was not recorded — nothing was written to the loan file. Try again.';
// Status 0 is "the request never came back": either it never left this process or
// it passed lib/api.ts's 8s deadline. Neither says what the backend did with it,
// and telling an officer nothing was written when a HOLD may already be in the
// loan file is the one wrong answer here.
const UNCONFIRMED =
  'The backend did not answer in time, so this decision is unconfirmed. Reload the tranche before deciding again.';
const NOT_A_LENDER =
  'Only a lender can decide a tranche. Sign in again as a credit officer and retry.';
const GONE = 'This tranche is no longer on the book. Open the hotlist and pick it up from there.';
const BAD_REQUEST = 'That decision was not one of the three on this card. Nothing was recorded.';

/** A loan id is an opaque short token in this build ("1001"). Anything else is a
 *  tampered action, not a loan. */
const LOAN_ID = /^[A-Za-z0-9_-]{1,16}$/;

export async function decideAction(
  loanId: string,
  tranche: number,
  _previous: DecisionState,
  formData: FormData
): Promise<DecisionState> {
  const action = formData.get('action');
  if (!isDecisionAction(action)) {
    return { status: 'error', message: BAD_REQUEST, recorded: null };
  }
  if (!LOAN_ID.test(loanId) || !Number.isInteger(tranche) || tranche < 1) {
    return { status: 'error', message: FAILED, recorded: null };
  }

  const session = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!session) {
    return { status: 'error', message: NOT_A_LENDER, recorded: null };
  }

  const path = `/api/loans/${encodeURIComponent(loanId)}/tranches/${tranche}/decision`;

  try {
    await apiPost<unknown>(path, { action }, { cookie: `${SESSION_COOKIE}=${session}` });
  } catch (cause) {
    if (!(cause instanceof ApiError)) throw cause;
    if (cause.status === 401 || cause.status === 403) {
      return { status: 'error', message: NOT_A_LENDER, recorded: null };
    }
    if (cause.status === 404) {
      return { status: 'error', message: GONE, recorded: null };
    }
    if (cause.status === 422) {
      return { status: 'error', message: BAD_REQUEST, recorded: null };
    }
    if (cause.status === 0) {
      return { status: 'error', message: UNCONFIRMED, recorded: null };
    }
    return { status: 'error', message: FAILED, recorded: null };
  }

  // The decision is idempotent per tranche and does not move the tranche's
  // status, so the view itself does not change — but the exposure figures it
  // quotes are now frozen in the loan file, and the officer may reload to read
  // them, so the cached render is dropped rather than left behind.
  revalidatePath(`/bank/loans/${loanId}/tranches/${tranche}`);

  return { status: 'ok', message: RECORDED[action], recorded: action };
}
