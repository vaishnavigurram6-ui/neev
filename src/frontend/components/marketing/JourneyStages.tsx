// The four-stage journey strip, shared by Landing and Login.
//
// Deliberately NOT the kit's <StageStrip>: that component models progress
// (done / current / todo) and renders a tick or a dot per stage. These four
// stages describe what Neev does across a build — none of them is "complete" for
// a visitor who has not signed in — so a progress vocabulary would be a lie.
//
// An <ol> because the stages are ordered: 0 before signing through 3 on every
// change. The numerals are mono, per the handoff's rule that every number is.
import { JOURNEY_STAGES } from './journey';

export default function JourneyStages({
  layout,
  label,
  className = '',
}: {
  /** `rows` is the Login left-panel treatment; `grid` is the Landing band. */
  layout: 'rows' | 'grid';
  /** Invisible group name. The prototypes give the strip no visible heading. */
  label: string;
  className?: string;
}) {
  if (layout === 'rows') {
    return (
      <ol aria-label={label} className={`flex flex-col ${className}`}>
        {JOURNEY_STAGES.map((stage) => (
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
      {JOURNEY_STAGES.map((stage) => (
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
