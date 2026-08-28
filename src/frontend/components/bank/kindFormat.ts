// One place that turns a view model's `{value, value_kind}` pair into display
// text, so no screen decides for itself how a figure is written.
//
// The backend deliberately sends numbers plus a kind (`views.py`: "value_kind
// tells the frontend which formatter to apply, which is what keeps formatINR()
// the single formatter"). This is that dispatch table, and it is the only reason
// a screen never has to branch on a field name.
//
// It lives under components/bank/ because that is the tree Task 18 owns; it is
// not bank-specific, and belongs in lib/format.ts the moment that file is
// unfrozen.
import { formatINR, formatINRCompact, formatPct, formatQty, formatRatio } from '@/lib/format';
import type { ValueKind } from '@/lib/types';

/** A figure the API sent as a number renders through its kind's formatter; one
 *  it sent as a string is already the em dash the mappers use for "not known",
 *  and is passed through untouched rather than coerced to NaN. */
export function formatByKind(value: number | string, kind: ValueKind): string {
  if (typeof value === 'string') return value;
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
      return formatQty(value);
    case 'text':
    default:
      // A `text` kind carrying a number is a backend bug, not a money figure:
      // group it and do not invent a currency symbol for it. `default` covers
      // the same ground for a kind this hand-transcribed union does not know
      // yet — an empty cell where a rupee figure belongs is the worse failure.
      return formatQty(value);
  }
}
