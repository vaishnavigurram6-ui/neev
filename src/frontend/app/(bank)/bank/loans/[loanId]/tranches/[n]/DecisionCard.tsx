'use client';

// The decision card. The prototype's three options are styled <div>s with a
// pointer cursor; here they are three submit buttons in one real <form>, so the
// card is keyboard-operable and every press goes through the server action that
// forwards the officer's session.
//
// All three stay enabled after a decision: the endpoint is idempotent per
// tranche, so an officer who changes their mind replaces the entry rather than
// appending an argument with itself — and a card that locked itself after the
// first press would hide that.
import { useActionState } from 'react';
import { toneClasses, type Tone } from '@/lib/tone';
import { decideAction } from './actions';
import { INITIAL_DECISION_STATE, type DecisionAction } from './state';

const COPY = {
  title: 'Decision',
  release: 'Release',
  hold: 'Hold — request re-scope',
  escalate: 'Escalate to physical inspection',
  recommended: 'recommended',
  working: 'Recording…',
  trail:
    'Every decision carries the full evidence trail — photos, benchmark lookups and the exposure math above — into the loan file.',
  recordedMark: 'recorded',
};

export default function DecisionCard({
  loanId,
  tranche,
  /** Already through formatINR() — this component formats nothing. */
  requestAmount,
  recommended,
  recommendedTone,
}: {
  loanId: string;
  tranche: number;
  requestAmount: string;
  /** Which of the three the pipeline recommends, or null when it recommends none
   *  of them. Never guessed here: it is derived from the API's recommendation. */
  recommended: DecisionAction | null;
  recommendedTone: Tone;
}) {
  const [state, formAction, pending] = useActionState(
    decideAction.bind(null, loanId, tranche),
    INITIAL_DECISION_STATE
  );

  const options: { action: DecisionAction; label: string }[] = [
    { action: 'RELEASE', label: `${COPY.release} ${requestAmount}` },
    { action: 'HOLD', label: COPY.hold },
    { action: 'ESCALATE', label: COPY.escalate },
  ];

  const emphasis = toneClasses(recommendedTone, 'bank');

  return (
    <form action={formAction} className="rounded-bank bg-bank-bar px-[22px] py-[20px]">
      <h2 className="text-[13.5px] font-bold text-bank-surface">{COPY.title}</h2>

      <div className="mt-3 flex flex-col gap-2">
        {options.map((option) => {
          const isRecommended = option.action === recommended;
          const isRecorded = state.recorded === option.action;
          return (
            <button
              key={option.action}
              type="submit"
              name="action"
              value={option.action}
              disabled={pending}
              aria-describedby="decision-trail"
              className={`flex items-center justify-between gap-3 rounded-bank px-[14px] py-[11px] text-left text-[13px] font-semibold transition-colors disabled:cursor-progress disabled:opacity-60 ${
                isRecommended
                  ? `${emphasis.pill} font-bold`
                  : 'border border-bank-inactive/40 text-bank-inactive hover:text-bank-surface'
              }`}
            >
              <span>{option.label}</span>
              {isRecommended && <span className="text-[11.5px]">{COPY.recommended}</span>}
              {isRecorded && !isRecommended && (
                <span className="text-[11.5px]">{COPY.recordedMark}</span>
              )}
            </button>
          );
        })}
      </div>

      {/* Announced, not merely shown: the outcome of a write is the one thing an
          officer must not have to notice. */}
      <p
        aria-live="polite"
        className={`mt-3 min-h-[16px] text-[11.5px] leading-[1.6] ${
          state.status === 'error' ? 'font-semibold text-bank-surface' : 'text-bank-inactive'
        }`}
      >
        {pending ? COPY.working : state.message}
      </p>

      <p id="decision-trail" className="mt-2 text-[11.5px] leading-[1.6] text-bank-inactive">
        {COPY.trail}
      </p>
    </form>
  );
}
