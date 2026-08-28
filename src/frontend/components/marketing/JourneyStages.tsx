// The four-stage journey strip, shared by Landing and Login.
//
// Deliberately NOT the kit's <StageStrip>: that component models progress
// (done / current / todo) and renders a tick or a dot per stage. These four
// stages describe what Neev does across a build — none of them is "complete" for
// a visitor who has not signed in — so a progress vocabulary would be a lie.
//
// An <ol> because the stages are ordered: 0 before signing through 3 on every
// change. The numerals are mono, per the handoff's rule that every number is.
//
// EXTENDED (plan Task 15): a third `cards` treatment and an optional `stages`
// override. `Neev 0 Owner Onboarding.dc.html` draws the same four stages under
// "HOW NEEV STAYS WITH YOU" as a four-card grid with its own, longer copy. That
// is one strip with three layouts, not two components — forking it would leave
// the product with two lists of the same four stages that could drift apart.
import Card from '@/components/ui/Card';
import { JOURNEY_STAGES, type JourneyStage } from './journey';

export default function JourneyStages({
  layout,
  label,
  stages = JOURNEY_STAGES,
  className = '',
}: {
  /** `rows` is the Login left-panel treatment, `grid` the Landing band, `cards`
   *  the Onboarding block. */
  layout: 'rows' | 'grid' | 'cards';
  /** Invisible group name. The prototypes give the strip no visible heading. */
  label: string;
  /** Defaults to the Login prototype's wording. Onboarding passes its own, which
   *  is the same four stages said at greater length. */
  stages?: JourneyStage[];
  className?: string;
}) {
  if (layout === 'cards') {
    return (
      <ol aria-label={label} className={`grid grid-cols-4 gap-3 ${className}`}>
        {stages.map((stage) => (
          <li key={stage.n}>
            <Card className="h-full p-[18px]">
              <div className="tnum text-[11px] text-faint">{`STAGE ${stage.n}`}</div>
              <div className="mt-2 text-[13.5px] font-bold text-ink">{stage.name}</div>
              <div className="mt-[5px] text-[12px] leading-[1.55] text-sub">{stage.desc}</div>
            </Card>
          </li>
        ))}
      </ol>
    );
  }

  if (layout === 'rows') {
    return (
      <ol aria-label={label} className={`flex flex-col ${className}`}>
        {stages.map((stage) => (
          <li
            key={stage.n}
            className="flex items-baseline gap-[14px] border-b border-line py-[11px]"
          >
            <span className="tnum w-4 flex-none text-[11px] text-action">{stage.n}</span>
            <span className="w-[130px] flex-none text-[13px] font-semibold text-ink">
              {stage.name}
            </span>
            <span className="text-[12px] leading-[1.5] text-faint">{stage.desc}</span>
          </li>
        ))}
      </ol>
    );
  }

  return (
    <ol aria-label={label} className={`grid grid-cols-4 gap-8 ${className}`}>
      {stages.map((stage) => (
        <li key={stage.n} className="flex items-baseline gap-3">
          <span className="tnum flex-none text-[11px] font-semibold text-action">{stage.n}</span>
          <div>
            <div className="text-[13.5px] font-bold text-ink">{stage.name}</div>
            <div className="mt-[3px] text-[12.5px] leading-[1.55] text-sub">{stage.desc}</div>
          </div>
        </li>
      ))}
    </ol>
  );
}
