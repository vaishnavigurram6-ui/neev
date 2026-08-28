'use client';

// The header's "Send 4 questions" action. A real <form> around a real submit
// button, so it works the way the browser expects and the result is announced —
// the prototype's version is a <div> with a hover style and no destination.
import { useActionState } from 'react';
import Button from '@/components/ui/Button';
import { sendQuestionsAction } from './actions';
import { initialSendState } from './state';

export default function SendQuestionsForm({
  loanId,
  count,
  contractor,
  alreadySent,
  copy,
}: {
  loanId: string;
  count: number;
  contractor: string | null;
  /** True when every drafted question has already gone. The backend is
   *  idempotent, so the control stays live — it just stops claiming to be a
   *  first send. */
  alreadySent: boolean;
  copy: {
    send: string;
    sendAgain: string;
    sending: string;
    sentOne: string;
    sentMany: string;
    withContractor: string;
  };
}) {
  const [state, formAction, pending] = useActionState(sendQuestionsAction, initialSendState);

  const recipient = contractor ?? copy.withContractor;
  // The backend's count when it gave one; otherwise the number of questions this
  // screen just submitted. Never zero-with-a-tick: a send that reports nothing
  // sent is not a confirmation.
  const sent = state.sent ?? count;
  const confirmation =
    state.status === 'sent'
      ? `${sent === 1 ? copy.sentOne : copy.sentMany.replace('{n}', String(sent))} ${recipient}.`
      : null;

  return (
    <form action={formAction} className="flex flex-col items-end gap-[6px]">
      <input type="hidden" name="loanId" value={loanId} />
      <Button type="submit" variant="primary" disabled={pending || count === 0}>
        {pending
          ? copy.sending
          : alreadySent
            ? copy.sendAgain
            : copy.send.replace('{n}', String(count))}
      </Button>
      {/* Always in the tree so it is a live region before it has anything to
          say; `empty:hidden` keeps it out of the layout until it does. */}
      <p
        role="status"
        className={`max-w-[240px] text-right text-[11px] leading-[1.45] empty:hidden ${
          state.status === 'error' ? 'font-semibold text-danger' : 'text-faint'
        }`}
      >
        {state.status === 'error' ? state.message : confirmation}
      </p>
    </form>
  );
}
