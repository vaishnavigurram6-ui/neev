'use client';

// Logging a change the contractor asked for verbally.
//
// Behind a <details> because it is the rarer path: the common case is answering
// what the contractor has already put in writing. Open it and it is a plain
// form — no wizard, no modal — because the owner is usually standing on site
// with one hand free.
import { useActionState } from 'react';
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import { logAction } from './actions';
import { IDLE, type ReplyState } from './state';

const FIELD =
  'w-full rounded-[10px] border border-input-border bg-card px-[12px] py-[9px] text-[13px] text-ink placeholder:text-faint';

export default function LogChange({ loanId, copy }: { loanId: string; copy: { cta: string; title: string; lead: string } }) {
  const [state, formAction, pending] = useActionState<ReplyState, FormData>(
    logAction.bind(null, loanId),
    IDLE
  );

  return (
    <details className="group">
      <summary className="cursor-pointer list-none text-[13px] font-semibold text-action underline decoration-from-font underline-offset-2">
        {copy.cta}
      </summary>
      <Card className="mt-[10px] p-[18px]">
        <h3 className="text-[14px] font-bold text-ink">{copy.title}</h3>
        <p className="mt-[4px] text-[12px] leading-[1.55] text-sub">{copy.lead}</p>
        <form action={formAction} className="mt-[12px] flex flex-col gap-[10px]">
          <label className="flex flex-col gap-[4px] text-[11px] font-semibold text-sub">
            What is the change?
            <input name="title" className={FIELD} placeholder="Extra window in the stair landing" />
          </label>
          <div className="grid grid-cols-2 gap-[10px]">
            <label className="flex flex-col gap-[4px] text-[11px] font-semibold text-sub">
              The line in your signed BoQ
              <input name="signed_desc" className={FIELD} placeholder="Not in the signed drawing" />
            </label>
            <label className="flex flex-col gap-[4px] text-[11px] font-semibold text-sub">
              Signed amount (₹, blank if none)
              <input name="signed_amount" inputMode="numeric" className={`tnum ${FIELD}`} placeholder="0" />
            </label>
            <label className="flex flex-col gap-[4px] text-[11px] font-semibold text-sub">
              What is now proposed
              <input name="proposed_desc" className={FIELD} placeholder="1 no. UPVC window, 3 x 4 ft" />
            </label>
            <label className="flex flex-col gap-[4px] text-[11px] font-semibold text-sub">
              Proposed amount (₹)
              <input name="proposed_amount" inputMode="numeric" className={`tnum ${FIELD}`} placeholder="14500" />
            </label>
          </div>
          <div className="flex items-center gap-3">
            <Button type="submit" variant="primary" disabled={pending}>
              {pending ? 'Logging…' : 'Log this change'}
            </Button>
            <p
              aria-live="polite"
              className={`text-[11.5px] leading-[1.5] ${
                state.status === 'error' ? 'text-danger' : 'text-faint'
              }`}
            >
              {state.message ?? ''}
            </p>
          </div>
        </form>
      </Card>
    </details>
  );
}
