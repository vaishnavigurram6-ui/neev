// Panel.tsx — the owner screens' section card: a heading, an optional aside on
// the right of that heading, a body, and an optional footer note under a rule.
// It is layout over the kit's `Card`, not a new surface: no colour, no radius
// and no border of its own. Every scaffolded screen uses it, which is what keeps
// the five of them looking like one screen family.
import Card from '@/components/ui/Card';
import type { Skin } from '@/lib/tone';

export default function Panel({
  title,
  aside,
  footer,
  skin = 'owner',
  children,
}: {
  title: string;
  aside?: React.ReactNode;
  footer?: React.ReactNode;
  skin?: Skin;
  children: React.ReactNode;
}) {
  return (
    <Card skin={skin} className="p-[22px]">
      <div className="flex items-baseline justify-between gap-4">
        <h2 className="text-[14.5px] font-bold text-ink">{title}</h2>
        {aside && <div className="flex-none text-[12px] text-faint">{aside}</div>}
      </div>
      <div className="mt-[14px]">{children}</div>
      {footer && (
        <div className="mt-[14px] border-t border-line pt-[12px] text-[12px] leading-[1.55] text-faint">
          {footer}
        </div>
      )}
    </Card>
  );
}
