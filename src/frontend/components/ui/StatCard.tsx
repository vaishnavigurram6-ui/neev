// StatCard.tsx — four of these head BoQ Review and Portfolio. Label is uppercase
// with letter-spacing; value is mono at 23px; sub is one line of context.
import Card from './Card';
import Figure from './Figure';
import type { Skin, Tone } from '@/lib/tone';

export default function StatCard({
  label,
  value,
  sub,
  tone = 'neutral',
  skin = 'owner',
}: {
  label: string;
  value: string;
  sub: string;
  tone?: Tone;
  skin?: Skin;
}) {
  return (
    <Card skin={skin} className="px-[17px] py-[15px]">
      <div className="text-[10.5px] font-semibold uppercase tracking-[0.08em] text-faint">
        {label}
      </div>
      <div className="mt-[9px]">
        <Figure value={value} tone={tone} skin={skin} size="lg" />
      </div>
      <div className="mt-[6px] text-[12px] leading-[1.45] text-sub">{sub}</div>
    </Card>
  );
}
