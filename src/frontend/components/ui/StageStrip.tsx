// StageStrip.tsx — the 5-stage checklist (Tranche Decision) and the journey
// strip (Onboarding, Login) are the same shape.
//
// The three states must differ visually, not only in the sr-only text: a `✓` on
// a stage that has not yet passed tells a sighted officer "verified" while the
// screen reader says "in progress", and on this screen that is the difference
// between a cleared disbursal check and an open one.
import { toneClasses, type Skin } from '@/lib/tone';

export interface Stage {
  name: string;
  sub: string;
  state: 'done' | 'current' | 'todo';
}

const GLYPH: Record<Stage['state'], string> = {
  done: '✓',
  current: '●',
  todo: '·',
};

const ANNOUNCE: Record<Stage['state'], string> = {
  done: 'Complete.',
  current: 'In progress.',
  todo: 'Not started.',
};

export default function StageStrip({ stages, skin = 'owner' }: { stages: Stage[]; skin?: Skin }) {
  const radius = skin === 'bank' ? 'rounded-bank' : 'rounded-card';
  const done = toneClasses('success', skin);
  const current = toneClasses('warn', skin);
  const currentBorder = skin === 'bank' ? 'border-bank-warn' : 'border-warn';

  return (
    <ol className="flex gap-[10px]">
      {stages.map((stage) => {
        const tone = stage.state === 'done' ? done : stage.state === 'current' ? current : null;
        return (
          <li
            key={stage.name}
            aria-current={stage.state === 'current' ? 'step' : undefined}
            className={`flex-1 border px-3 py-[10px] ${radius} ${
              stage.state === 'current'
                ? `${currentBorder} ${current.bg}`
                : stage.state === 'done'
                  ? `border-line ${done.bg}`
                  : 'border-line bg-card'
            }`}
          >
            <div className="flex items-center gap-2">
              <span
                className={`flex h-[18px] w-[18px] items-center justify-center rounded-full text-[11px] font-bold ${
                  tone ? `${tone.bg} ${tone.text}` : 'bg-chip text-faint'
                }`}
                aria-hidden="true"
              >
                {GLYPH[stage.state]}
              </span>
              <span
                className={`text-[12.5px] font-semibold ${
                  stage.state === 'todo' ? 'text-faint' : 'text-ink'
                }`}
              >
                {stage.name}
              </span>
            </div>
            <div className="mt-[4px] text-[11px] text-sub">{stage.sub}</div>
            <span className="sr-only">{ANNOUNCE[stage.state]}</span>
          </li>
        );
      })}
    </ol>
  );
}
