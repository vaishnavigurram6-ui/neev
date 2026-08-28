// Every figure this screen shows, derived from `GET /api/loans/{id}/boq/latest`.
// Nothing here is transcribed from the mockup: the mockup's numbers live in the
// fixture behind the endpoint, and this module only decides which formatter from
// `lib/format.ts` applies and how the mockup's composite strings are assembled.
//
// Kept next to the page rather than in `lib/`: the kit and `lib/` are frozen for
// Phase 2, and `formatStatValue` / `formatDay` are wanted by Sanction Check and
// Portfolio too. Both are flagged for promotion into `lib/format.ts`.

import { formatINR, formatINRCompact, formatPct, formatQty, formatRatio } from '@/lib/format';
import type { Tone } from '@/lib/tone';
import type { BoqReviewView, FlagGroupView, FlagRowView, StatCardView } from '@/lib/types';

/** "2026-08-12" -> "12 Aug 2026". UTC-pinned so the server and the client agree
 *  on the day; `components/owner/preview.ts` formats dates the same way, and the
 *  two should collapse into one exported formatter once `lib/` reopens. */
const DAY = new Intl.DateTimeFormat('en-IN', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  timeZone: 'UTC',
});

export function formatDay(iso: string): string {
  return DAY.format(new Date(`${iso}T00:00:00Z`));
}

/** A stat card's value, formatted according to the `value_kind` the API sent.
 *
 *  `countNoun` is the card's unit of counting, which the API does not carry: the
 *  BoQ cards count items ("9 items", the mockup's own wording). A value that
 *  arrives as a string when its kind says otherwise is rendered as-is rather
 *  than coerced to NaN — `StatCardView.value` is `float | str` on the wire, and
 *  the em dash for an unknown figure travels that way. */
export function formatStatValue(card: StatCardView, countNoun: string): string {
  const { value, value_kind: kind } = card;
  if (kind === 'text') return String(value);
  if (typeof value !== 'number') return String(value);
  switch (kind) {
    case 'money':
      return formatINR(value);
    case 'money_compact':
      return formatINRCompact(value);
    case 'pct':
      return formatPct(value);
    case 'ratio':
      return formatRatio(value);
    case 'count':
      return `${formatQty(value)} ${countNoun}`;
  }
}

/** The mono figures beside a flagged line: "6.5 cum × ₹9,800 = ₹63,700" for a
 *  priced line, "expected ≈ 295 sqm ≈ ₹74,000" for scope that is absent.
 *
 *  Which of the two a row gets is not a guess: a missing-scope flag has no
 *  priced line behind it, so the mapper leaves qty/rate/amount null and fills
 *  `expected_*` instead. `null` when the flag carries neither — a vague-spec
 *  flag on an unpriced line would, and inventing a figure for it would be worse
 *  than showing none. */
export function rowFigures(row: FlagRowView, expectedPrefix: string): string | null {
  if (row.qty !== null && row.unit && row.rate !== null && row.amount !== null) {
    return `${formatQty(row.qty)} ${row.unit} × ${formatINR(row.rate)} = ${formatINR(row.amount)}`;
  }
  if (row.amount !== null) return formatINR(row.amount);

  const expected: string[] = [expectedPrefix];
  if (row.expected_qty !== null) {
    const unit = row.expected_unit ? ` ${row.expected_unit}` : '';
    expected.push(`≈ ${formatQty(row.expected_qty)}${unit}`);
  }
  if (row.expected_amount !== null) expected.push(`≈ ${formatINR(row.expected_amount)}`);
  return expected.length > 1 ? expected.join(' ') : null;
}

/** The severity the API itself assigned to the payment split.
 *
 *  The "DUE BEFORE SLAB" stat card already carries a tone, judged in
 *  `mappers/boq.py` against its own threshold. Reading that tone — rather than
 *  re-judging the same percentage here against the 25% the mockup's copy calls
 *  standard — is what stops the rail's pill, bar and before-slab figure from
 *  contradicting the card sitting directly above them, which they would for any
 *  split between the two thresholds.
 *
 *  The card is found by what it holds, not by its position: it is the only one
 *  whose kind is `pct` and whose value is the before-slab split. `standardPct`
 *  is the fallback rule for a view model that carries no such card. */
export function paymentTone(view: BoqReviewView, standardPct: number): Tone {
  const card = view.cards.find(
    (candidate) => candidate.value_kind === 'pct' && candidate.value === view.pct_before_slab
  );
  return card?.tone ?? (view.pct_before_slab > standardPct ? 'warn' : 'success');
}

export function countRows(groups: FlagGroupView[]): number {
  return groups.reduce((total, group) => total + group.items.length, 0);
}

/** The quoted total, reconstructed.
 *
 *  API GAP: `BoqReviewView` carries `pct_before_slab` and `amount_before_slab`
 *  but not `boq_total`, even though the mapper has `revision.boq_total` in hand.
 *  The payment card's "after · ₹17,60,000" label and the GST notice's rupee
 *  figure are both fractions of that total, so it is inverted out of the two
 *  fields that are exposed — `amount_before_slab` IS `boq_total × pct_before_slab`
 *  in `mappers/boq.py`, so this is that identity read backwards, not an estimate.
 *
 *  `null` unless both halves of the identity are positive: a 0% split says
 *  Read straight from the view model's `boq_total`. This used to be inverted
 *  out of amount_before_slab / pct_before_slab, which divided by zero on a
 *  schedule with nothing due before the slab; the field was added to the API
 *  on 2026-08-28 so the derivation could go. A non-positive total returns
 *  null and every caller omits its figure rather than printing "up to ₹0". */
export function quotedTotal(view: BoqReviewView): number | null {
  return Number.isFinite(view.boq_total) && view.boq_total > 0 ? view.boq_total : null;
}

/** What is due after the slab is cast — the balance of the quoted total. */
export function amountAfterSlab(view: BoqReviewView): number | null {
  const total = quotedTotal(view);
  return total === null ? null : total - view.amount_before_slab;
}

/** The upper bound of the unbudgeted GST the notice warns about.
 *
 *  The rate pair is the mockup's copy ("At 12–18%"), held next to the sentence
 *  in COPY so the two cannot drift; only the total comes from the API. The
 *  fixture does price a GST provision — `cost_estimate.sections` has one — but
 *  it reaches the frontend on the Sanction Check view, not this one, so the
 *  alternative would be a second endpoint call for a rail footnote. */
export function gstUpperBound(view: BoqReviewView, upperRate: number): number | null {
  const total = quotedTotal(view);
  return total === null ? null : total * upperRate;
}
