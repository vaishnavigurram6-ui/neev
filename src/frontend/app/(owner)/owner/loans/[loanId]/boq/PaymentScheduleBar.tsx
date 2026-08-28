// The payment-schedule bar from the rail of `Neev 1 BoQ Review.dc.html`.
//
// The prototype hardcodes six segments and three shades of terracotta. Here the
// segments are the stages the API returns — five for the golden case — and their
// widths are their own `pct`. Nothing about the bar is written into the markup.
//
// The bar is `aria-hidden`, with the same information following it as a real
// list for screen readers: a row of coloured strips conveys nothing when read
// aloud, and the stage names and percentages are the actual content.
//
// Colour: `lib/tone.ts` exposes a pill pair, a text colour and a tint, but no
// solid fill, and a 10px bar drawn in `--danger-tint` is invisible. The classes
// below are theme-token utilities (never hex) held as complete literal strings
// so Tailwind's scanner sees them. `ToneClasses` wants a `solid` member —
// Sanction Check's comparison bars need the same thing.
import { formatPct } from '@/lib/format';
import type { Tone } from '@/lib/tone';
import type { PaymentStageView } from '@/lib/types';

const FILL: Record<Tone, string[]> = {
  danger: ['bg-danger', 'bg-danger/70', 'bg-danger/45', 'bg-danger/30'],
  warn: ['bg-warn', 'bg-warn/70', 'bg-warn/45', 'bg-warn/30'],
  success: ['bg-success', 'bg-success/70', 'bg-success/45', 'bg-success/30'],
  neutral: ['bg-ink', 'bg-ink/70', 'bg-ink/45', 'bg-ink/30'],
};

const REST = 'bg-input-border';

export default function PaymentScheduleBar({
  stages,
  tone,
  copy,
}: {
  stages: PaymentStageView[];
  /** The severity of this schedule, judged once by the page and used by every
   *  part of the card, so the bar and the pill never disagree. */
  tone: Tone;
  copy: { listLabel: string; beforeSlab: string; afterSlab: string };
}) {
  if (stages.length === 0) return null;

  const shades = FILL[tone];
  let beforeSlabSeen = 0;

  return (
    <>
      <div className="mt-[16px] flex h-[10px] gap-[2px] overflow-hidden rounded-full" aria-hidden="true">
        {stages.map((stage, index) => {
          const fill = stage.before_slab
            ? shades[Math.min(beforeSlabSeen++, shades.length - 1)]
            : REST;
          return (
            <span
              key={`${stage.label}-${index}`}
              // Flex basis rather than width so the 2px gaps come out of the
              // segments instead of overflowing the track.
              style={{ flexBasis: `${stage.pct * 100}%` }}
              className={`min-w-0 shrink ${fill}`}
            />
          );
        })}
      </div>

      <ul className="sr-only">
        <li>{copy.listLabel}</li>
        {stages.map((stage, index) => (
          <li key={`${stage.label}-${index}`}>
            {`${stage.label}: ${formatPct(stage.pct)} — ${
              stage.before_slab ? copy.beforeSlab : copy.afterSlab
            }`}
          </li>
        ))}
      </ul>
    </>
  );
}
