'use client';

// The three replies an owner can give one change order.
//
// One <form>, three submit buttons carrying their own intent, and the counter's
// figure in the same form as the button that sends it — so a keyboard Enter in
// the amount field sends the counter rather than accepting the proposal.
import { useActionState } from 'react';
import Button from '@/components/ui/Button';
import { formatINR } from '@/lib/format';
import { replyAction } from './actions';
import { IDLE, type ReplyState } from './state';

export default function ReplyCard({
  loanId,
  changeOrderId,
  proposedAmount,
  signedAmount,
  labels,
}: {
  loanId: string;
  changeOrderId: number;
  proposedAmount: number;
  signedAmount: number;
  labels: { counter: string; accept: string; decline: string; counterLabel: string };
}) {
  const [state, formAction, pending] = useActionState<ReplyState, FormData>(
    replyAction.bind(null, loanId, changeOrderId),
    IDLE
  );

  const amountId = `counter-${changeOrderId}`;
  const statusId = `reply-status-${changeOrderId}`;

  return (
    <form action={formAction} className="mt-[14px]">
      <div className="flex flex-wrap items-end gap-2">
        <div className="flex flex-col gap-[4px]">
          <label htmlFor={amountId} className="text-[11px] font-semibold text-sub">
            {labels.counterLabel}
          </label>
          <input
            id={amountId}
            name="counter_amount"
            type="text"
            inputMode="numeric"
            autoComplete="off"
            placeholder={formatINR(signedAmount)}
            aria-describedby={statusId}
            className="tnum w-[150px] rounded-[10px] border border-input-border bg-card px-[12px] py-[9px] text-[13px] text-ink placeholder:text-faint"
          />
        </div>
        <Button
          type="submit"
          name="action"
          value="counter"
          disabled={pending}
          aria-describedby={statusId}
        >
          {labels.counter}
        </Button>
        <Button
          type="submit"
          name="action"
          value="accept"
          variant="primary"
          disabled={pending}
          aria-describedby={statusId}
        >
          {labels.accept}
          {proposedAmount > 0 ? ` · ${formatINR(proposedAmount)}` : ''}
        </Button>
        <Button
          type="submit"
          name="action"
          value="decline"
          disabled={pending}
          aria-describedby={statusId}
        >
          {labels.decline}
        </Button>
      </div>

      {/* Announced, not merely shown: the reply is the whole point of the card. */}
      <p
        id={statusId}
        aria-live="polite"
        className={`mt-[8px] text-[11.5px] leading-[1.5] ${
          state.status === 'error' ? 'text-danger' : 'text-faint'
        }`}
      >
        {pending ? 'Sending your reply…' : (state.message ?? '')}
      </p>
    </form>
  );
}
