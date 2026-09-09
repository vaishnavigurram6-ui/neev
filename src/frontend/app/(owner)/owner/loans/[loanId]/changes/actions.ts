'use server';

// The owner's two writes on this screen: answering a change order, and logging
// one the contractor asked for off the record.
//
// Server actions rather than client fetches, for the same reasons as the bank's
// decision action: the session cookie is httpOnly so only the server can
// forward it, and NEEV_API_BASE is deliberately not a NEXT_PUBLIC_ variable, so
// the backend is not reachable from a browser at all.
//
// `loanId` and the change order's id arrive as bound arguments, not form
// fields. Next encrypts bound arguments, so the contract being answered cannot
// be swapped by editing the DOM. Both are re-validated anyway, because the
// request path is built from them.
import { revalidatePath } from 'next/cache';
import { ApiError, apiPost } from '@/lib/api';
import { isReplyAction, parseRupees, type ReplyState } from './state';

const RECORDED: Record<string, string> = {
  accept: 'Accepted. It is now part of your contract total.',
  decline: 'Declined. Your signed line stands.',
  counter: 'Counter sent. The order stays open until your contractor answers.',
};

const FAILED = 'That reply was not recorded. Try again.';
const UNCONFIRMED =
  'The service did not answer in time, so this reply is unconfirmed. Reload the page before replying again.';
const SIGN_IN = 'Your session has expired. Sign in again and your reply will go through.';
const SETTLED = 'This change order has already been answered. Reload to see where it stands.';
const GONE = 'That change order is no longer on this loan.';
const NEEDS_FIGURE = 'Enter the amount you will agree to, in whole rupees.';

/** A loan id is an opaque short token in this build ("1001"). */
const LOAN_ID = /^[A-Za-z0-9_-]{1,16}$/;

function failure(message: string): ReplyState {
  return { status: 'error', message, recorded: null };
}

export async function replyAction(
  loanId: string,
  changeOrderId: number,
  _previous: ReplyState,
  formData: FormData
): Promise<ReplyState> {
  const action = formData.get('action');
  if (!isReplyAction(action)) return failure(FAILED);
  if (!LOAN_ID.test(loanId) || !Number.isInteger(changeOrderId) || changeOrderId < 1) {
    return failure(FAILED);
  }

  const body: { action: string; counter_amount?: number; note?: string } = { action };
  if (action === 'counter') {
    const typed = formData.get('counter_amount');
    const amount = parseRupees(typeof typed === 'string' ? typed : '');
    if (amount === null) return failure(NEEDS_FIGURE);
    body.counter_amount = amount;
  }
  const note = formData.get('note');
  if (typeof note === 'string' && note.trim()) body.note = note.trim().slice(0, 2000);

  try {
    await apiPost<unknown>(
      `/api/loans/${encodeURIComponent(loanId)}/change-orders/${changeOrderId}/reply`,
      body
    );
  } catch (cause) {
    if (!(cause instanceof ApiError)) throw cause;
    if (cause.status === 401 || cause.status === 403) return failure(SIGN_IN);
    if (cause.status === 404) return failure(GONE);
    if (cause.status === 409) return failure(SETTLED);
    if (cause.status === 422) return failure(NEEDS_FIGURE);
    // Status 0 is "the request never came back". Telling the owner nothing was
    // recorded when an acceptance may already be on their contract is the one
    // wrong answer here.
    if (cause.status === 0) return failure(UNCONFIRMED);
    return failure(FAILED);
  }

  // The running total in the rail is now wrong on this page's cached render.
  revalidatePath(`/owner/loans/${loanId}/changes`);
  return { status: 'ok', message: RECORDED[action], recorded: action };
}

export async function logAction(
  loanId: string,
  _previous: ReplyState,
  formData: FormData
): Promise<ReplyState> {
  if (!LOAN_ID.test(loanId)) return failure(FAILED);

  const text = (name: string): string => {
    const value = formData.get(name);
    return typeof value === 'string' ? value.trim() : '';
  };

  const title = text('title');
  const proposed_desc = text('proposed_desc');
  const proposed = parseRupees(text('proposed_amount'));
  // A change to nothing is a change too: an extra window has no signed line, so
  // a blank signed amount means zero rather than an error.
  const signedTyped = text('signed_amount');
  const signed = signedTyped === '' ? 0 : parseRupees(signedTyped);

  if (!title) return failure('Give the change a short name.');
  if (!proposed_desc) return failure('Say what your contractor is now proposing.');
  if (proposed === null || signed === null) return failure('Enter both amounts in whole rupees.');

  try {
    await apiPost<unknown>(`/api/loans/${encodeURIComponent(loanId)}/change-orders`, {
      title: title.slice(0, 200),
      signed_desc: text('signed_desc') || 'Not in the signed BoQ',
      signed_amount: signed,
      proposed_desc: proposed_desc.slice(0, 2000),
      proposed_amount: proposed,
    });
  } catch (cause) {
    if (!(cause instanceof ApiError)) throw cause;
    if (cause.status === 401 || cause.status === 403) return failure(SIGN_IN);
    if (cause.status === 0) return failure(UNCONFIRMED);
    return failure('That change was not logged. Try again.');
  }

  revalidatePath(`/owner/loans/${loanId}/changes`);
  return {
    status: 'ok',
    message: 'Logged. It is on the list below, marked as not yet checked against local rates.',
    recorded: null,
  };
}
