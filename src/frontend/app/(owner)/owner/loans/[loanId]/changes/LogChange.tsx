'use client';

// Logging a change the contractor asked for verbally, in a modal.
//
// A native <dialog> opened with showModal(): the browser gives the focus trap,
// the Escape key, the backdrop and the inert background for free, and every one
// of those is something a div-with-a-fixed-position gets wrong. The form inside
// is the same server action as before.
//
// It closes on success and the list behind it updates itself: `logAction` calls
// `revalidatePath`, so Next re-renders the page's server component and the new
// row, the new running total and the sanction line all arrive together. Nothing
// here re-adds them client-side, which is what would let the modal and the page
// disagree.
import { useActionState, useEffect, useRef } from 'react';
import Button from '@/components/ui/Button';
import { logAction } from './actions';
import { IDLE, type ReplyState } from './state';

const FIELD =
  'w-full rounded-[10px] border border-input-border bg-card px-[12px] py-[9px] text-[13px] text-ink placeholder:text-faint';
const LABEL = 'flex flex-col gap-[4px] text-[11px] font-semibold text-sub';

export default function LogChange({
  loanId,
  copy,
}: {
  loanId: string;
  copy: { cta: string; title: string; lead: string };
}) {
  const [state, formAction, pending] = useActionState<ReplyState, FormData>(
    logAction.bind(null, loanId),
    IDLE
  );
  const dialog = useRef<HTMLDialogElement>(null);
  const form = useRef<HTMLFormElement>(null);

  // Close on success, and leave the fields empty for the next one. Kept in an
  // effect rather than in the submit handler because the action's result is
  // what says it worked.
  useEffect(() => {
    if (state.status === 'ok') {
      form.current?.reset();
      dialog.current?.close();
    }
  }, [state]);

  return (
    <>
      <Button variant="primary" onClick={() => dialog.current?.showModal()}>
        {copy.cta}
      </Button>

      <dialog
        ref={dialog}
        aria-labelledby="log-change-title"
        className="w-[min(560px,92vw)] rounded-card border border-line bg-card p-0 text-ink backdrop:bg-scrim"
      >
        <div className="p-[22px]">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 id="log-change-title" className="text-[16px] font-bold text-ink">
                {copy.title}
              </h2>
              <p className="mt-[4px] text-[12.5px] leading-[1.55] text-sub">{copy.lead}</p>
            </div>
            {/* A form-less close, so Escape and this button do the same thing. */}
            <button
              type="button"
              onClick={() => dialog.current?.close()}
              aria-label="Close"
              className="rounded-pill px-2 py-1 text-[16px] leading-none text-faint hover:bg-chip hover:text-ink"
            >
              ✕
            </button>
          </div>

          <form ref={form} action={formAction} className="mt-[14px] flex flex-col gap-[10px]">
            <label className={LABEL}>
              What is the change?
              <input
                name="title"
                autoFocus
                className={FIELD}
                placeholder="Extra window in the stair landing"
              />
            </label>
            <div className="grid grid-cols-2 gap-[10px]">
              <label className={LABEL}>
                The line in your signed BoQ
                <input name="signed_desc" className={FIELD} placeholder="Not in the signed drawing" />
              </label>
              <label className={LABEL}>
                Signed amount (₹, blank if none)
                <input
                  name="signed_amount"
                  inputMode="numeric"
                  className={`tnum ${FIELD}`}
                  placeholder="0"
                />
              </label>
              <label className={LABEL}>
                What is now proposed
                <input
                  name="proposed_desc"
                  className={FIELD}
                  placeholder="1 no. UPVC window, 3 x 4 ft"
                />
              </label>
              <label className={LABEL}>
                Proposed amount (₹)
                <input
                  name="proposed_amount"
                  inputMode="numeric"
                  className={`tnum ${FIELD}`}
                  placeholder="14500"
                />
              </label>
            </div>

            <div className="mt-[4px] flex items-center justify-end gap-3">
              <p
                id="log-change-status"
                aria-live="polite"
                className={`mr-auto text-[11.5px] leading-[1.5] ${
                  state.status === 'error' ? 'text-danger' : 'text-faint'
                }`}
              >
                {pending ? 'Logging…' : (state.message ?? '')}
              </p>
              <Button type="button" onClick={() => dialog.current?.close()}>
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                disabled={pending}
                aria-describedby="log-change-status"
              >
                {pending ? 'Logging…' : 'Log this change'}
              </Button>
            </div>
          </form>
        </div>
      </dialog>
    </>
  );
}
