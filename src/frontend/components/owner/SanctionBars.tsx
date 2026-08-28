// SanctionBars.tsx — the three comparison bars on Sanction Check: the
// contractor's quote, the realistic cost at local rates, and the sanction.
//
// Every width is `pct_of_max` from the API. The mockup's 91% / 100% / 80% are
// what 32,00,000 / 35,00,000 / 28,00,000 come to against the largest bar, and
// the mapper already did that division — nothing here may spell a percentage.
//
// The mockup also draws the reference bar (the largest) darker than the other
// neutral one. That is emphasis, not status, so it is derived from the widths
// rather than smuggled in as a second colour vocabulary.
import Figure from '@/components/ui/Figure';
import { formatINR, formatPct } from '@/lib/format';
import type { Tone } from '@/lib/tone';
import type { SanctionBarView } from '@/lib/types';

// `toneClasses` carries a pill pair, a text colour and a tint — no solid fill,
// because nothing else in the kit is a block of tone-coloured area. A bar is
// that one thing, so the solid classes live here instead of becoming a fourth
// role on every tone. Still the one `tone` vocabulary: no colour prop, no hex.
const FILL: Record<Tone, string> = {
  danger: 'bg-danger',
  warn: 'bg-warn',
  success: 'bg-success',
  neutral: 'bg-faint',
};

export default function SanctionBars({ bars }: { bars: SanctionBarView[] }) {
  const widest = bars.reduce((max, bar) => Math.max(max, share(bar)), 0);

  return (
    <ul className="flex flex-col gap-[18px]">
      {bars.map((bar) => {
        const pct = share(bar);
        // The widest bar is the one everything else is read against, so it gets
        // ink. A bar carrying a status keeps its status colour either way.
        const fill = bar.tone === 'neutral' && pct >= widest ? 'bg-ink' : FILL[bar.tone];
        return (
          <li key={bar.label}>
            <div className="flex items-baseline justify-between gap-4">
              <span className="text-[13px] font-semibold text-sub">{bar.label}</span>
              <Figure value={formatINR(bar.value)} tone={bar.tone} />
            </div>
            {/* Decorative geometry. The figure above is the value, so the bar is
                hidden from assistive tech rather than mimed with a progressbar
                role: nothing here is readable by length alone. */}
            <div
              aria-hidden="true"
              className="mt-2 h-[22px] overflow-hidden rounded-[8px] bg-chip"
            >
              <div className={`h-full rounded-[8px] ${fill}`} style={{ width: formatPct(pct) }} />
            </div>
            <p className="mt-[5px] text-[12px] leading-[1.5] text-faint">{bar.sub}</p>
          </li>
        );
      })}
    </ul>
  );
}

/** `pct_of_max` clamped into 0–1.
 *
 *  It is backend data, so it is untrusted: a value above 1 would draw a bar
 *  wider than its own track, a negative one would produce `width: -10%` — which
 *  CSS drops, silently rendering a full-width bar — and a NaN would reach
 *  `formatPct` as "—", an invalid width. Clamping keeps the geometry honest. */
function share(bar: SanctionBarView): number {
  if (!Number.isFinite(bar.pct_of_max)) return 0;
  return Math.min(Math.max(bar.pct_of_max, 0), 1);
}
