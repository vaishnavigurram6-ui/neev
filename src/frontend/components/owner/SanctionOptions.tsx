// SanctionOptions.tsx — the "three ways forward" cards in the Sanction Check
// rail. Informational, not actionable: the mockup gives them a hover border and
// nothing else, so they stay list items rather than becoming fake buttons.
//
// `saves_label` is a copy field, not a figure — one of the three reads "closes
// the rest". It is rendered as it arrives, mono, exactly as the mockup has it.
import Card from '@/components/ui/Card';
import Figure from '@/components/ui/Figure';
import type { SanctionOptionView } from '@/lib/types';

export default function SanctionOptions({ options }: { options: SanctionOptionView[] }) {
  // A list with no items is not an empty list on screen, it is a stray <ul>.
  if (options.length === 0) return null;

  return (
    <ul className="flex flex-col gap-4">
      {options.map((option) => (
        <li key={option.title}>
          <Card className="p-[18px] transition-colors hover:border-ink">
            <div className="flex items-baseline justify-between gap-3">
              <h3 className="text-[13.5px] font-bold text-ink">{option.title}</h3>
              <Figure value={option.saves_label} tone="success" size="sm" />
            </div>
            <p className="mt-[5px] text-[12.5px] leading-[1.55] text-sub">{option.desc}</p>
          </Card>
        </li>
      ))}
    </ul>
  );
}
