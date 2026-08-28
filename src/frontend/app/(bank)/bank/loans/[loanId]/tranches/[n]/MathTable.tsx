// "The math, in one line each" — a real <table>, not the prototype's grid of
// styled <div>s. Three columns is a data grid: an officer reading it aloud, or
// with a screen reader, has to be able to hear which figure belongs to which
// line, and the label is the row's header, not another cell.
//
// Not `CardTable`: that component is built for the wide grids (min-w 720px, a
// linked first column, groups) and this table sits in the narrow left column of a
// 1fr/380px shell, where 720px would force it to scroll sideways inside its own
// card at 1280px. Same kit surface (`Card`, `Figure`), different shape.
import { formatByKind } from '@/components/bank/kindFormat';
import Figure from '@/components/ui/Figure';
import type { MathRowView } from '@/lib/types';

export default function MathTable({ rows, caption }: { rows: MathRowView[]; caption: string }) {
  return (
    <table className="w-full border-collapse text-left">
      <caption className="sr-only">{caption}</caption>
      <thead>
        <tr className="border-b border-line">
          <th
            scope="col"
            className="pb-[8px] text-[10.5px] font-semibold uppercase tracking-[0.06em] text-faint"
          >
            Line
          </th>
          <th
            scope="col"
            className="pb-[8px] text-[10.5px] font-semibold uppercase tracking-[0.06em] text-faint"
          >
            How it is worked out
          </th>
          <th
            scope="col"
            className="pb-[8px] text-right text-[10.5px] font-semibold uppercase tracking-[0.06em] text-faint"
          >
            Result
          </th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.label} className="border-b border-rowline last:border-0">
            <th
              scope="row"
              className="w-[190px] py-[12px] pr-3 align-baseline text-[13px] font-semibold text-ink"
            >
              {row.label}
            </th>
            {/* The calculation is the backend's own string, rendered as sent:
                it is the audit line, and re-typesetting it here would put a
                second author on the arithmetic. */}
            <td className="tnum py-[12px] pr-3 align-baseline text-[12px] leading-[1.5] text-sub">
              {row.calc}
            </td>
            <td className="py-[12px] text-right align-baseline">
              <Figure
                value={formatByKind(row.result, row.result_kind)}
                tone={row.tone}
                skin="bank"
              />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
