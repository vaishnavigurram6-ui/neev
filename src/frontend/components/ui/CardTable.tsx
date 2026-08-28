// CardTable.tsx — the BoQ, portfolio, scorecard and math grids are all this
// component. It renders a real <table> — CSS for layout, table semantics for
// meaning — so row and column relationships survive for a screen reader. It
// scrolls inside its own overflow-x container so the page body never scrolls
// horizontally below 1280px.
import Link from 'next/link';
import Card from './Card';
import { toneClasses, type Skin, type Tone } from '@/lib/tone';

export interface Column<T> {
  key: string;
  header: string;
  align?: 'left' | 'right';
  width?: string;
  render: (row: T) => React.ReactNode;
}

export default function CardTable<T>({
  columns,
  rows,
  caption,
  skin = 'owner',
  rowHref,
  rowTone,
  groupBy,
  emptyMessage = 'Nothing to show yet.',
}: {
  columns: Column<T>[];
  rows: T[];
  /** Announced to screen readers; visually hidden. Always describe the data. */
  caption: string;
  skin?: Skin;
  rowHref?: (row: T) => string;
  rowTone?: (row: T) => Tone | null;
  groupBy?: (row: T) => string;
  emptyMessage?: string;
}) {
  const grouped = groupBy
    ? rows.reduce<Map<string, T[]>>((acc, row) => {
        const key = groupBy(row);
        const bucket = acc.get(key);
        if (bucket) bucket.push(row);
        else acc.set(key, [row]);
        return acc;
      }, new Map())
    : new Map<string, T[]>([['', rows]]);

  return (
    <Card skin={skin} className="overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] border-collapse text-left">
          <caption className="sr-only">{caption}</caption>
          <thead>
            <tr className="border-b border-line">
              {columns.map((column) => (
                <th
                  key={column.key}
                  scope="col"
                  style={column.width ? { width: column.width } : undefined}
                  className={`px-[15px] py-[11px] text-[10.5px] font-semibold uppercase tracking-[0.06em] text-faint ${
                    column.align === 'right' ? 'text-right' : 'text-left'
                  }`}
                >
                  {column.header}
                </th>
              ))}
            </tr>
          </thead>
          {[...grouped.entries()].map(([group, groupRows]) => (
            <tbody key={group || 'all'}>
              {group && (
                <tr>
                  <th
                    scope="colgroup"
                    colSpan={columns.length}
                    className="bg-hover px-[15px] py-[8px] text-[10.5px] font-semibold uppercase tracking-[0.06em] text-sub"
                  >
                    {group}
                  </th>
                </tr>
              )}
              {groupRows.map((row, index) => {
                const tone = rowTone?.(row) ?? null;
                const tint = tone ? toneClasses(tone, skin).bg : '';
                const href = rowHref?.(row);
                return (
                  <tr
                    key={index}
                    className={`border-b border-rowline last:border-0 hover:bg-hover ${tint}`}
                  >
                    {columns.map((column, columnIndex) => (
                      <td
                        key={column.key}
                        className={`px-[15px] py-[12px] align-top text-[13px] ${
                          column.align === 'right' ? 'text-right' : 'text-left'
                        }`}
                      >
                        {href && columnIndex === 0 ? (
                          <Link href={href} className="hover:text-action">
                            {column.render(row)}
                          </Link>
                        ) : (
                          column.render(row)
                        )}
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          ))}
        </table>
      </div>
      {rows.length === 0 && (
        <p className="px-[15px] py-8 text-center text-[13px] text-sub">{emptyMessage}</p>
      )}
    </Card>
  );
}
