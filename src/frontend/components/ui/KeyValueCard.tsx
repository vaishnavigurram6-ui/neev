// KeyValueCard.tsx — the "math in one line each" pattern, used by Tranche
// Decision, Build Progress and the sanction rail.
import Card from './Card';
import type { Skin } from '@/lib/tone';

export default function KeyValueCard({
  title,
  rows,
  footer,
  skin = 'owner',
}: {
  title: string;
  rows: { label: string; value: React.ReactNode; sub?: string }[];
  footer?: React.ReactNode;
  skin?: Skin;
}) {
  return (
    <Card skin={skin} className="p-[17px]">
      <h2 className="text-[13.5px] font-bold text-ink">{title}</h2>
      <dl className="mt-3 flex flex-col gap-[10px]">
        {rows.map((row) => (
          <div key={row.label} className="flex items-baseline justify-between gap-3">
            <dt className="text-[12.5px] text-sub">
              {row.label}
              {row.sub && <span className="mt-[2px] block text-[11px] text-faint">{row.sub}</span>}
            </dt>
            <dd className="flex-none text-right">{row.value}</dd>
          </div>
        ))}
      </dl>
      {footer && <div className="mt-[14px] border-t border-line pt-[12px]">{footer}</div>}
    </Card>
  );
}
